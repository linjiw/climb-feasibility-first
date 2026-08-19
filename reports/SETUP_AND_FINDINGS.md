# CLIMB — environment setup and Phase-0 findings

Date: 2026-08-15
Machine: RTX 5090 (sm_120, 32 GiB) · 20 cores · 93 GB RAM · driver 590.48.01 / CUDA 13.1
Plan under test: `/home/robotixx/newton/fable.md`

Everything below was measured on this machine. Numbers quoted without a source
were produced by the commands in §8.

---

## 1. Headline

Six things changed materially versus the plan as written.

1. **A silent data corruption was found and fixed.** All 7,901 pre-existing G1
   `.npz` motions are in Isaac Lab / PhysX breadth-first body order; mjlab needs
   MuJoCo depth-first. Both are 30 bodies × 29 joints, so the file loads, training
   runs, reward curves look plausible, and every tracking target is bound to the
   wrong link. Nothing in mjlab checks this. A validator and a rebuilt conversion
   pipeline now exist, and the pipeline is verified bit-equivalent to mjlab's own
   reference export.

2. **mjlab at its previous commit could not be installed at all** — not a stale
   venv, an unfetchable lock. Fixed by moving to v1.6.0 in a separate worktree.
   Side benefit: v1.6.0 uses mujoco-warp 3.11.0, which is exactly what Newton
   uses, so the cross-version confound in the sim2sim comparison disappears.

3. **Compute is 6–13× cheaper than the plan budgets.** Measured 0.45 s/iteration
   at 4096 envs → **3.8 GPU-hours per 30k-iteration run**, against the plan's
   assumed 24–48. The 45-run matrix is ~169 GPU-hours, not 1,080–2,160. This
   buys the statistical power the matrix currently lacks.

4. **A second silent corruption: the AMASS retargets mix six frame rates**
   (120/100/60/250/59/150), encoded per filename. mjlab's converter takes a
   single `--input-fps`, so converting that directory the obvious way retimes
   59% of the bank and every velocity derived from it. See section 4.

5. **A third: those same retargets store root height relative** (mean root
   z = -0.004 m vs +0.767 m for LAFAN1), burying the robot 0.75 m into the
   floor. Fixed by a rigid vertical realignment that needs no re-conversion.

6. **The plan's central hypothesis contradicts the researcher's own prior
   results**, which fable.md does not cite. See §7 — this is the one item that
   needs a decision rather than an action.

---

## 2. What is installed and verified

| Subsystem | Location | State | Evidence |
|---|---|---|---|
| Newton | `/home/robotixx/newton` + `.venv` (py3.12.13) | **ready** | `6142 tests, OK (skipped=167)`, exit 0, 36 min |
| Newton on 5090 | — | **ready** | `cuda:0 … sm_120, 31 GiB, mempool enabled`; `robot_g1 --viewer null` exit 0 |
| mjlab v1.6.0 | `/data/robotixx/climb/mjlab-1.6.0` (worktree) + `.venv` (py3.13.9) | **ready** | `import mjlab` OK; torch 2.9.0+cu128, capability (12,0), sm_120 matmul OK |
| mjlab tracking task | — | **ready** | `Mjlab-Tracking-Flat-Unitree-G1` registered; 10-iter train run exit 0 |
| Motion validator | `/data/robotixx/climb/tools/validate_motion_npz.py` | **ready** | A/B: mjlab reference PASS, local copy FAIL, same clip |
| Bank converter | `/data/robotixx/climb/tools/build_motion_bank.py` | **ready** | output bit-equivalent to mjlab reference (§4) |
| GMR shim | `/data/robotixx/climb/tools/gmr_npz_to_csv.py` | **ready** | joint order verified: 29 hinges identical |
| Throughput bench | `/data/robotixx/climb/tools/bench_throughput.sh` | **ready** | curve in §3 |
| Ground aligner | `/data/robotixx/climb/tools/ground_align_bank.py` | **ready** | idempotent; verified no-op on second pass |
| Difficulty featurizer | `/data/robotixx/climb/tools/featurize_motions.py` | **ready** | 28 covariates; atlas in §5 |
| LAFAN1 bank | `bank/lafan1` | **ready** | 40 clips, 2.45 h, 0.74 GiB, 0 failures |
| LAFAN1 (GMR) | `bank/lafan1_gmr` | **ready** | 77 clips, **4.60 h** — the full official release |
| AMASS bank | `bank/amass` | **ready** | 10,705 clips, 36.56 h, 11.0 GiB, 2 rejects |

The user's own `/home/robotixx/mjlab` checkout was **not modified** — no commits,
no branch switch, no dropped stash. The v1.6.0 line lives in a git worktree.

### Why mjlab was unfixable in place

`uv.lock` at the previous commit pinned `mujoco==3.6.0.dev881488083` from
`py.mujoco.org`. That build has been garbage-collected: the URL returns 404 and
the index no longer carries any 3.6.x. The installed `tyro 0.9.35` was a
symptom, not the cause — the venv simply predated the lock and, being an
editable install, the source tree advanced to 1.2.0 while its dependency set
stayed frozen at the 0.1.0 era. v1.6.0 resolves entirely from pypi.org.

---

## 3. Measured throughput (Phase-0 exit criterion)

`Mjlab-Tracking-Flat-Unitree-G1`, single clip, quiet GPU, steady-state mean over
the back half of 30 iterations. `num_steps_per_env=24`.

| num_envs | s/iter | steps/s | peak VRAM | 30k-iter run |
|---:|---:|---:|---:|---:|
| 1,024 | 0.349 | 70,358 | 4.6 GiB | 2.9 h |
| 2,048 | 0.381 | 128,906 | 4.9 GiB | 3.2 h |
| 4,096 | 0.451 | 218,114 | 5.6 GiB | **3.8 h** |
| 8,192 | 0.617 | 318,497 | 7.0 GiB | 5.1 h |
| 16,384 | 1.008 | 390,095 | 9.4 GiB | 8.4 h |

Baseline occupancy 3,491 MiB (desktop + a pre-existing Isaac Lab job), so
mjlab's own peak at 16k envs is ~6.2 GiB. **VRAM is not the constraint** on a
32 GiB card — throughput saturation is (4k→8k buys 1.46×, 8k→16k only 1.22×).
4,096 envs is the efficiency sweet spot; 8,192 if wall-clock per run matters more
than total GPU-hours.

### What this does to the experiment matrix

At 4,096 envs and 3.8 h/run:

| Design | Runs | GPU-h | Days @100% | Days @50% |
|---|---:|---:|---:|---:|
| Plan as written (3 bank × 5 sampler × 3 seeds) | 45 | 169 | 7.0 | 14.1 |
| **5 seeds** (3 × 5 × 5) | 75 | 282 | 11.7 | 23.5 |
| 5 seeds + 30% ablations | ~98 | 367 | 15.3 | 30.6 |

Phase 2's window (Oct 1 – Nov 15) is 46 days. **The 5-seed design fits with
headroom even at 50% duty cycle.** This matters because 3 seeds cannot produce a
significant result: the minimum achievable one-sided sign-flip p at n=3 is 0.125,
and the prior program's own guardrail requires ≥5 seeds. The plan should be
re-specified at 5 seeds — the compute objection to doing so does not survive
measurement.

**Caveats.** Single-clip measurement. A multi-clip bank adds motion tensors to
VRAM (~12 MiB per 2-minute clip at 50 Hz; 800 short AMASS clips ≈ 0.8 GiB, still
comfortable) and may change reset/collection behaviour. Whether 30k iterations is
the right convergence budget for a *multi-clip* policy is untested — calibrate
before freezing the matrix.

---

## 4. Three silent corruptions in the motion bank

`MotionLoader` (`tracking/mdp/commands.py`) indexes `body_pos_w` with indices
from the compiled MuJoCo model and validates nothing:

```python
data = np.load(motion_file)
self._body_pos_w = torch.tensor(data["body_pos_w"], ...)
self.body_pos_w  = self._body_pos_w[:, self._body_indexes]
```

mjlab's `g1.xml` compiles to depth-first order — the whole left leg occupies
indices 1–6, the right leg 7–12, feet at **6** and **12**. Every pre-existing
`.npz` is breadth-first: mirrored L/R pairs level by level, feet at 18/19.

The discriminator is the pelvis-frame lateral offset of **three proximal bodies**
(1, 2, 7). Their origins sit at fixed or hinge-invariant transforms from the
pelvis, so their pelvis-frame y does not move no matter what the robot does.
Measured across all 40 LAFAN1 clips — including falls, fights and jumps — the
spread is *exactly zero*:

| | y[1] | y[2] | y[7] |
|---|---|---|---|
| depth-first | +0.0645 | **+0.1165** | −0.0645 |
| breadth-first | +0.0645 | **−0.0645** | +0.1238 |

`sign(y[2])` alone separates them; `y[7]` confirms.

Two weaker heuristics were tried and rejected:

* *"the two lowest bodies are the feet"* — misfires on kneeling/sitting/ground
  motions (a sitting clip reported feet at `[14, 18]`).
* *whole-limb mean y, plus profile correlation against the neutral pose* — this
  wrongly rejected 7 of the first 549 AMASS conversions, all of them legitimate:
  calibration T-poses, `Lie_Down`, and martial-arts kicks, i.e. exactly the clips
  whose legs cross the midline. The correlation check is retained only as a loose
  gross-mismatch net (threshold 0.5), not as the gate.

The lesson generalises: a validator for a motion bank must be invariant to pose,
because the hard clips — the ones a curriculum most wants — are precisely the
ones that break pose-dependent heuristics.

### Proof the pipeline is correct

mjlab publishes a reference export of `lafan1_dance1_subject1`. Converting the
same source CSV with the new pipeline and diffing against it:

| key | max abs diff |
|---|---|
| `joint_pos`, `joint_vel` | **0.0** (exact) |
| `body_pos_w` | 4.8e-07 |
| `body_quat_w` | 2.4e-07 |
| `body_lin_vel_w` | 3.6e-06 |
| `body_ang_vel_w` | 5.7e-06 |

Float32 round-off. The pipeline reproduces mjlab's own numerics.

### Bank status

Final bank: **10,822 clips, 43.6 h** of validated G1 motion in 13.1 GiB.

| bank | clips | duration | median clip | on disk |
|---|--:|--:|--:|--:|
| `lafan1` | 40 | 2.45 h | 241 s | 0.74 GiB |
| `lafan1_gmr` | 77 | 4.60 h | 238 s | 1.38 GiB |
| `amass` | 10,705 | 36.56 h | 7.3 s | 11.00 GiB |

Only 2 of 10,707 AMASS inputs were rejected, both genuinely single-frame CSVs.

Note the shape difference: AMASS clips have a **median of 7.3 s** against LAFAN1's
238 s. An 800-clip AMASS bank is roughly 1.6 h of motion, while 77 LAFAN1 clips
are 4.6 h. Bank size in *clips* and bank size in *hours* are not interchangeable,
and the experiment matrix is specified in clips — worth pinning down which one
the scaling axis is meant to be before the matrix is frozen.

* **40 LAFAN1 clips** converted and validated (2.45 h, 0.74 GiB, 0 failures).
* **77 GMR LAFAN1 clips** — the shim is a quaternion reorder only
  (`wxyz`→`xyzw`); the 29 hinges are in identical order, verified against both
  compiled models. These unlock 14 families absent from the 40-clip set:
  `ground1/2`, `obstacles1–6`, `push1`, `pushAndFall1`, `pushAndStumble1`,
  `aiming1/2`, `multipleActions1` — precisely the low-posture / multi-contact /
  recovery motions §3.2 wants for the hard set and the gentle hardware demos.
* **77 GMR clips validated 77/77, totalling 4.60 h** — the full official LAFAN1
  duration §3.2 assumes, versus 2.45 h from the other retarget.
* **10,705 AMASS clips** converted in 73.7 min, then ground-aligned.

⚠ The 40-clip and 77-clip LAFAN1 sets are **different retargetings of the same
source motions** and overlap on 40 names. They are kept in separate directories.
Do not merge them into one bank — that would put two retargeting pipelines
inside a single experimental condition. §5 quantifies how far apart they are.

### A second silent corruption: the AMASS retargets do not share a frame rate

`mjlab.scripts.csv_to_npz` takes a single `--input-fps`, and the obvious reading
of `train_converted_complete/` is that it is 120 fps throughout. It is not. The
rate is encoded per file in the name, and the directory mixes six of them:

| suffix | clips | effect if read as 120 fps |
|---|--:|---|
| `_120_` | 4,403 | correct |
| `_100_` | 4,165 | **20% too fast** |
| `_60_` | 642 | **2x too fast** |
| `_250_` | 56 | **~2x too slow** |
| `_59_`, `_150_` | 22 | wrong |
| GRAB (no suffix) | ~1,400 | unknown; treated as 120 |

Converting the whole directory at one rate silently retimes **59% of the bank**.
Nothing errors: the clip simply plays at the wrong speed, and since velocity and
acceleration are finite-differenced during conversion, every kinematic and
dynamic feature — and every tracking target the policy sees — is wrong by that
factor. It is the timing analogue of the body-order bug: shapes stay valid, so
nothing catches it.

`build_motion_bank.py --infer-fps` now reads the rate per clip from the filename
and records it in the manifest as `input_fps` / `input_fps_from_name`, falling
back to `--input-fps` (and reporting how often) for names that carry no rate.
Verified on a 250 fps clip: 7,471 input frames now yield 29.9 s of output
(7471/250) instead of the 62 s a 120 fps reading would have produced.

The first build was stopped and audited rather than trusted: of 4,261 clips
already written, 3,597 came from genuine 120 fps sources and were kept; the 664
mis-timed ones (604 at 60 fps, 30 at 250 fps, 30 GRAB) were deleted and requeued.

### A third: the AMASS retargets store root height *relative*

Root z in `train_converted_complete/*.csv` averages **-0.004 m**. In the LAFAN1
CSVs, which use the identical column layout, it averages **+0.767 m**. The AMASS
files record height relative to the standing pose; the LAFAN1 files record it
absolutely.

Converted as-is, the G1 is buried to the pelvis. On a "Stand" clip the shins sit
0.51 m below the floor plane and the deepest geom 0.79 m below it. The
body-order validator passes these files, correctly -- the ordering is fine, only
the height is wrong -- which is precisely why a separate check was needed.

The fix is self-calibrating and does not require re-conversion. A root height
change is a rigid vertical translation, so it can be applied to a finished npz:
every body moves by the same amount and joint angles, orientations and all
velocities are untouched. `ground_align_bank.py` shifts each clip by the 1st
percentile of its lower foot's clearance, so a clip with genuine flight phases
is aligned on its touchdowns rather than its apex. Measured offsets:

| bank | median offset | reading |
|---|--:|---|
| LAFAN1 | -0.012 m | already grounded |
| AMASS | **-0.752 m** | buried by the missing standing pelvis height |

The AMASS median of -0.752 m is the standing pelvis height, which is the
signature of exactly this bug rather than of scattered retargeting noise.

**LAFAN1 is deliberately left unaligned.** Its 12 mm penetration is present in
mjlab's own published reference export too, and that bank is currently
bit-equivalent to it. Trading a verified match against upstream for 12 mm is a
bad deal; the AMASS bank has no such reference and needs the shift.

---

## 5. First difficulty-atlas result (RQ1)

`tools/featurize_motions.py` computes the offline half of the atlas — the
per-clip covariates H1 rests on — over all 40 LAFAN1 clips. Means by family,
sorted by flight fraction:

| family | n | flight | ground | dbl sup | CoM spd p95 | GRF max (bw) | μ p95 | L peak |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| sprint1 | 2 | 0.089 | 0.000 | 0.597 | 3.77 | 2.64 | 0.69 | 6.71 |
| jumps1 | 3 | 0.087 | 0.064 | 0.399 | 1.43 | 2.82 | 0.59 | 6.07 |
| run2 | 2 | 0.070 | 0.000 | 0.302 | 2.83 | 2.87 | 0.71 | 6.28 |
| run1 | 2 | 0.060 | 0.000 | 0.258 | 2.65 | 1.94 | 0.62 | 5.26 |
| walk3 | 5 | 0.054 | 0.043 | 0.611 | 1.02 | 1.60 | 0.20 | 3.30 |
| fallAndGetUp2 | 2 | 0.044 | 0.504 | 0.568 | 1.63 | 2.45 | 0.31 | 6.60 |
| fight1 | 3 | 0.042 | 0.003 | 0.451 | 1.71 | 2.37 | 0.78 | 8.04 |
| fightAndSports1 | 2 | 0.039 | 0.002 | 0.590 | 1.48 | 2.60 | 0.70 | 8.45 |
| dance2 | 5 | 0.039 | 0.002 | 0.536 | 0.87 | 3.18 | 0.50 | 5.99 |
| fallAndGetUp1 | 3 | 0.033 | 0.387 | 0.496 | 1.97 | 2.44 | 0.43 | 7.01 |
| dance1 | 3 | 0.016 | 0.000 | 0.510 | 0.98 | 2.09 | 0.43 | 8.54 |
| fallAndGetUp3 | 1 | 0.015 | 0.163 | 0.596 | 1.14 | 1.81 | 0.41 | 6.25 |
| walk2 | 3 | 0.008 | 0.015 | 0.605 | 1.31 | 1.84 | 0.26 | 4.37 |
| walk1 | 3 | 0.001 | 0.000 | 0.646 | 1.29 | 1.63 | 0.27 | 3.36 |
| walk4 | 1 | 0.000 | 0.000 | 0.805 | 0.64 | 1.44 | 0.15 | 2.11 |

**The families dissociate, which is what H1 predicts.** `sprint1` leads flight
fraction and CoM speed (3.77 m/s) yet sits mid-pack on friction demand and
angular momentum; `dance1` has the *lowest* CoM speed of any non-walk family and
the *highest* angular momentum (8.54); `fight1` tops friction demand at μ≈0.78;
`dance2` tops peak GRF at 3.2 bodyweights. Double support falls monotonically
from 0.81 (walk4) to 0.26 (run1), which is the gait physics working. Ranking by kinematic magnitude gives a materially
different ordering than ranking by dynamic feasibility — so there is real signal
for the RQ1 regression to find, rather than one latent "intensity" axis.

`fallAndGetUp` carries a signature no other family has. It is the only group
with substantial non-foot ground contact — 0.504, 0.387 and 0.163 against ~0.00
for everything but `jumps1` (0.064) and `walk3` (0.043) — while sitting mid-range
on every kinematic axis. That is the multi-contact regime the plan wants, and no
kinematic feature identifies it.

### Retarget quality is now a measured covariate

The same machinery ranks the two retargets:

| retarget | median foot clearance | median max penetration | non-foot ground |
|---|--:|--:|--:|
| whole_body_tracking | **+3.3 mm** | 23.5 mm | 0.000 |
| GMR | +20.9 mm | 96.3 mm | 0.011 |

The whole_body_tracking retarget is roughly 4x better grounded on both measures.
That argues for a concrete bank policy: prefer the wbt clips for the 15 families
it covers, and take GMR only for the 14 families it uniquely provides —
recording `foot_clearance_p50` as a covariate so the quality difference can be
regressed out rather than silently confounding a bank-size effect.

### Measurement problems found and fixed while building this

All were caught by checking family ordering against physics rather than
assuming it.

**Joint-torque utilisation was invalid and has been removed.** Retargeted mocap
does not place the feet consistently on the terrain, so most frames report
`ncon = 0`, MuJoCo's constraint solve contributes nothing, and inverse dynamics
dumps the full 327 N bodyweight into the root residual. One standing frame
produced 354 N*m at a 139 N*m motor. Replaced with quantities well defined
without a consistent contact state -- required friction coefficient, vertical
GRF in bodyweights, CoP margin -- computed with contacts explicitly disabled so
the free-joint block of `qfrc_inverse` *is* the required ground wrench.

**Contact is now measured, not inferred.** Three successive height heuristics
each failed on a different family:

1. *"the two lowest bodies are the feet"* -- misfires on kneeling and sitting
   (a sitting clip reported feet at indices `[14, 18]`).
2. *`min` foot height as the ground reference* -- one penetrating frame destroys
   it. GMR dips to -6 mm on `fight1`, which made 95% of that clip read as flight.
3. *low percentile of the lowest body of any kind* -- meaningless while lying
   down, and it pushed `walk2` to 0.36 flight.

The terrain is a plane at exactly z = 0 and an exact `mj_geomDistance` query
costs ~0.1 s for a 13k-frame clip, so every frame is now queried directly
against real collision geometry. No ground estimation remains.

**The two retargets are not interchangeable, and the atlas proves it.** With
exact contact, cross-retarget rank agreement over the 15 shared families is:

| feature | Spearman rho |
|---|--:|
| non-foot ground contact | **+0.964** |
| required friction mu | **+0.918** |
| flight fraction | **+0.150** |

The flight disagreement is a property of the data, not the tool. Median
lower-foot clearance is **+3.3 mm** for the whole_body_tracking retarget and
**+20.9 mm** for GMR -- *GMR floats the robot about 2 cm off the floor*, so its
feet rarely enter the 2 cm contact band and every contact-derived feature is
inflated. `walk4` reads 91% airborne under GMR and 0% under wbt.

This is now exposed as the `foot_clearance_p1 / p50 / penetration_max`
covariates, which is exactly the "retargeting residual magnitude" feature
Section 3.3 asks for. **GMR clips need a per-clip z-offset correction before
they are used as tracking references** -- a policy trained on them would learn
to hover. That correction is deliberately not applied automatically; it alters
the reference the policy tracks, so it should be an explicit decision.

Remaining caveat: the support polygon is approximated by the two ankle-roll body
positions, ignoring the ~0.2 x 0.1 m foot area, so CoP margins run pessimistic
by roughly half a foot length. Fine as a relative ordering, not an absolute
stability criterion.

### Over the full 10,705-clip bank: what H1 actually gets

Spearman rho of every feature against `com_speed_p95`, the obvious kinematic
"intensity" proxy a naive difficulty ordering would use:

| feature | family | rho |
|---|---|--:|
| `required_mu_p95` | dyn | +0.706 |
| `vert_force_bw_max` | dyn | +0.640 |
| `contact_switch_rate` | dyn | +0.577 |
| `flight_phase_frac` | dyn | +0.503 |
| `joint_vel_p95` | kin | +0.480 |
| `support_margin_mean` | dyn | -0.446 |
| `jerk_p95` | kin | +0.398 |
| `com_height_range` | kin | +0.375 |
| `angmom_peak` | kin | +0.363 |
| `cop_margin_mean` | dyn | -0.255 |
| **`nonfoot_ground_frac`** | **dyn** | **-0.104** |

No feature exceeds rho = 0.71, so none is redundant with speed. The result that
matters for H1 is the last row: **the multi-contact axis is essentially
orthogonal to kinematic intensity**. A curriculum ordered by "how fast and big
is this motion" does not merely under-weight low-posture and multi-contact
clips, it carries almost no information about them. That is a concrete,
pre-training argument for the featurisation in section 3.3 over clip length or
CoM speed, and it is measured on 10,705 clips rather than asserted.

### 20% of the bank is physically untrackable

Geometric validity is not physical validity. These clips have correct body
order, correct timing and correct grounding, and still demand things no
controller can deliver -- kinematic retargeting carries no dynamics constraint,
so it will happily produce a motion needing friction coefficient 13 or 43
bodyweights of ground reaction. Left in, they occupy the hard tail of the
difficulty atlas for entirely the wrong reason.

| screen | rejected | share |
|---|--:|--:|
| hovers >5 cm on the median frame | 1,138 | 10.6% |
| joint speed beyond G1 actuators (>30 rad/s) | 1,001 | 9.4% |
| demands friction coefficient > 1.0 | 300 | 2.8% |
| peak ground reaction > 5 bodyweights | 122 | 1.1% |
| sinks >10 cm into the floor | 16 | 0.1% |
| shorter than 1 s | 31 | 0.3% |
| **any screen** | **2,185** | **20.4%** |

**8,520 clips / 26.89 h survive.** `tools/screen_bank.py` emits that list plus
difficulty-stratified tiers for the bank-size axis, stratified on a
rank-averaged composite of the *dynamic* features rather than clip length.

| tier | clips | hours |
|---|--:|--:|
| 50 | 50 | 0.17 |
| 200 | 200 | 0.61 |
| 800 | 800 | 2.54 |

Which surfaces a design question the plan should settle: **the 800-clip cell
holds 2.54 h of motion, while the 77-clip LAFAN1 bank holds 4.60 h.** The
bank-size axis as specified scales clip count 16x and hours 15x, but its top end
is still less total motion than Tier A. If the intended manipulation is
*diversity*, that is fine and should be said; if it is *scale*, the axis does
not deliver it.

## 6. First training result: the headroom gate, and a partial answer to H1

Everything above is instrumentation. This section is the first actual
experiment, and it changes what the plan should do next.

### The multi-clip capability now exists

`climb/` is an mjlab extension (the §7 deliverable) adding the axis CLIMB
needs. `MotionBank` concatenates clips and keeps a per-clip offset table, so
`time_steps` becomes a global index and all ~20 of mjlab's accessors work
unchanged; only the clip axis is new, since mjlab already samples the start
frame *within* a clip. Two arms are registered:

| task | sampler | verified |
|---|---|---|
| `Climb-Tracking-Flat-Unitree-G1` | uniform clip, uniform frame | top-1 weight 0.0200 = 1/50, entropy 1.000 |
| `…-G1-Adaptive` | clip ~ failure EMA + eps/N | entropy 1.000 -> 0.933, top-1 0.020 -> 0.112 |

Uniform means uniform over *clips*, not frames. The bank spans 3.7 s to 264 s,
so frame-uniform would weight by duration and quietly make the control arm a
length-weighted curriculum -- confounding the comparison it exists to anchor.

Baseline run: 4000 iterations, 4096 envs, 50-clip bank, ~57 min. Mean reward
1.2 -> 22.4, mean episode length 60 -> 409 steps. That is real multi-clip
tracking, not a single-clip specialist.

### The headroom gate: bank construction decides whether the matrix is interpretable

Evaluating that one frozen policy across three banks, 16 episodes per clip:

| bank | mean survival | frontier (gate >=0.20) | mastered (gate >=0.30) | verdict |
|---|--:|--:|--:|---|
| `tier_50` difficulty-stratified | 0.915 | 0.060 | 0.880 | **FAIL** — nothing left to learn |
| `tier_hard50` hardest decile | 0.603 | **0.480** | 0.380 | **PASS** |
| `tier_mixed100` union | 0.746 | **0.230** | 0.640 | **PASS** |

Two banks clear the SIM-D1 gate that four prior candidates failed. The gate is
not a formality: on `tier_50` the policy masters 88% of clips after 4000
iterations — 13% of a full run — so an adaptive sampler there has essentially
nothing to prioritise between, and any sampler comparison run on it would
return an uninterpretable null. That is the same shape as the prior program's
SIM-M3 result.

**Bank construction, not sampler design, is what buys headroom.** Stratifying
evenly across the difficulty composite produced a bank that is too easy;
taking the hardest decile produced one with a real frontier. This is a
concrete, measured prescription the plan currently lacks.

### H1: partially supported, and the half that fails is the interesting half

Regressing measured difficulty on the offline atlas over `tier_mixed100`
(n=100, 5-fold cross-validated, ridge=1.0):

| feature set | k | CV R^2 | CV rho |
|---|--:|--:|--:|
| clip length alone | 1 | -0.039 | -0.144 |
| kinematic magnitude | 5 | **+0.263** | **+0.744** |
| dynamic feasibility | 6 | +0.212 | +0.706 |
| kinematic + dynamic | 11 | +0.265 | +0.699 |

H1 has two clauses and they come apart:

* *"better than clip length alone"* — **strongly supported.** Clip length is
  worse than predicting the mean (rho = -0.14); the physics atlas reaches
  rho ~ 0.74 out of fold. The featurisation earns its place.
* *"dynamic-feasibility beats kinematic magnitude"* — **not supported here.**
  Kinematic is marginally ahead, and combining the two adds essentially nothing
  (+0.265 vs +0.263), which says they are largely redundant on this bank rather
  than complementary.

One thing makes the negative half *stronger* rather than weaker: the bank was
constructed by ranking clips on a composite built **entirely from the dynamic
features**. That selection widens the dynamic features' range in this sample,
which if anything should favour them in the regression -- and kinematic still
came out marginally ahead. The result is not an artefact of a bank that happened
to vary kinematically.

Caveats, stated plainly: one seed, one policy, one bank, 4000 of 30,000
iterations, n=100. This is a direction, not a result. But it is the direction
the paper should be pressure-testing, and it is cheap to test properly now that
the machinery exists.

### Three measurement errors caught along the way

Each produced confident, plausible, wrong numbers:

1. **Scrambled per-clip assignment.** `clip_of_env = arange(n) % n_clips`
   interleaves clips across envs, but `reshape(n_clips, k)` groups *consecutive*
   envs — so each "clip" row averaged k different clips. Aggregate means stayed
   correct, which is why it survived a first look; per-clip difficulty was
   noise. Caught because the hard and easy halves of a mixed bank came out with
   identical mean difficulty (0.364 vs 0.371) after having measured 0.380 vs
   0.886 when evaluated separately.
2. **Difficulty measured at the wrong unit.** Starting every episode at frame 0
   makes the 16 episodes of a clip near-identical, so survival collapses to 0 or
   1 and the frontier band empties. Sampling start points *within* the clip —
   matching how training and any curriculum actually sample — moved
   `tier_hard50` from frontier 0.100 (fail) to 0.480 (pass). The measure has to
   match the sampling unit.
3. **A 6%-support predictor detonating the regression.**
   `nonfoot_ground_frac` is nonzero in 6 of 100 clips; folds whose training
   split held few of them gave held-out clips enormous z-scores, taking the
   dynamic set from R^2 +0.21 to **-142** while its own rank correlation was
   -0.04. Now excluded by a documented minimum-support rule applied before any
   set is scored.

## 7. Where the plan and the prior evidence disagree

This is the item that needs a decision, not a command.

fable.md H2 claims "≥2–3× compute reduction" from grounded adaptive sampling. The
prior SONIC track-B program on this machine tested essentially that mechanism and
recorded three non-supporting results:

* **SIM-M3** — adaptive vs uniform, mean Δ MPJPE-G **+0.111** (worse), 1/3 seeds
  improved, permutation p = 0.875, preregistered effect gate **FAIL**.
* **SIM-D1 headroom gate** — four candidate banks built, all four failed or were
  invalidated; frontier fractions 0/2, 0/24, 6/41, and a 9/28 pass voided when
  24/28 clips breached a root-XY drift guard.
* **128-motion ZPD pilot** — the literal `E[p(1−p)]` frontier utility CLIMB §3.4
  proposes, against a failure-rate sampler. Mechanism demonstrably activated
  (608 vs 283 effective bins) and still lost all four normalized-AUC metrics.

Two structural points follow.

**The baseline is stronger than "uniform."** mjlab already ships BeyondMimic-style
adaptive sampling upstream, over ~1 s bins within a clip: failure-count EMA
(`adaptive_alpha`), non-causal kernel smoothing (`adaptive_lambda`), and
`adaptive_uniform_ratio = 0.1` — an ε-uniform floor that is *already a crude
grounding term*. Collapse diagnostics (`sampling_entropy`, `sampling_top1_prob`,
`sampling_top1_bin`) are already logged.

**So CLIMB's real delta is narrower and better-posed than the plan states.** The
segment axis exists. What does not exist anywhere is:

* the **clip axis** (`MotionLoader` loads exactly one file),
* the **horizon axis**,
* and the **grounding term** as anything richer than ε-uniform.

That argues for making *grounding-vs-ε-uniform at matched frontier* the primary
contrast, rather than grounded-adaptive-vs-uniform — it is the only part that is
genuinely new, and the frontier term it would be bolted onto has already tested
null-to-adverse twice on this researcher's own data.

It also argues for adding a **dataset-headroom gate to Phase 0** (frontier
fraction ≥ 0.20 against a fixed reference policy). Frontier fraction, not spread,
was the binding constraint in three of four prior failures. Measuring it costs a
fraction of one matrix cell and determines whether the other 44 are interpretable.

---

## 8. Reproducing this

```bash
# Newton
cd /home/robotixx/newton && uv sync --extra dev
uv run -m newton.examples robot_g1 --viewer null --num-frames 30
uv run --extra dev -m newton.tests -j 4 --no-cache-clear

# mjlab v1.6.0 (worktree; the user's own checkout is untouched)
cd /data/robotixx/climb/mjlab-1.6.0
UV_CACHE_DIR=/data/robotixx/climb/.uv-cache uv sync --extra cu128 --group dev
.venv/bin/python -c "import mjlab; print('ok')"
.venv/bin/list-envs | grep Tracking

# throughput curve
/data/robotixx/climb/tools/bench_throughput.sh \
  /tmp/mjlab_cache/lafan1_dance1_subject1_demo_motion.npz 30 1024 2048 4096 8192 16384

# validate any motion before training on it
.venv/bin/python /data/robotixx/climb/tools/validate_motion_npz.py --dir BANK_DIR --quiet

# build a bank
MUJOCO_GL=egl .venv/bin/python /data/robotixx/climb/tools/build_motion_bank.py \
  --input-dir CSV_DIR --output-dir BANK_DIR --input-fps 30    # 120 for AMASS
```

---

## 9. Open decisions

1. **Re-specify the matrix at 5 seeds?** The compute objection does not survive
   measurement (§3); 3 seeds cannot yield significance.
2. **Make the grounding term the primary contrast** rather than an ablation (§7)?
3. **Add the SIM-D1 headroom gate to Phase 0** before committing to the matrix?
4. **Is a physical G1 actually available**, and on what schedule? Two Phase-0 exit
   criteria and all of Phase 3 depend on it; only an SDK checkout and a LAN
   address are visible from here.
5. **Disk**: `/` is at 91%. ~95 GB sits in `~/.cache/uv` (60 G) and `~/.cache/pip`
   (35 G). Not pruned — the uv cache holds the only local copy of the now-404
   mujoco wheel, so pruning it forecloses ever rebuilding the old mjlab lock.
6. **`~/.local/lib/python3.10/site-packages/torch`** is 2.5.1+cu124 and shadows
   every python3.10 environment; it reports `is_available()=True` then fails on
   sm_120 kernels. It breaks the `gmr` conda env. Left in place — renaming it is
   a global change affecting other projects.
