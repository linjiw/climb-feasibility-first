# FGAS — feasibility-grounded adaptive sampling: directive and mjlab design

Recorded 2026-08-19 from Linji's guidance. Not sealed; this is a design record, not a
pre-registration. The pre-registrations it implies are named at the end.

## The thesis, restated

The auditing result ("22.8% of a bank is dynamically infeasible") does not answer the reviewer's
question, which is *so what*. The claim that does:

> Failure-adaptive curricula treat persistent failure as a learning signal. That signal conflates
> **learnable difficulty** with **reference infeasibility**. A feasibility screen is policy-independent,
> so it can separate them — and restricting failure prioritisation to feasible segments reallocates
> training exposure from impossible transitions to feasible hard skills.

Short form: **failure is only a training signal where success exists.**

## One correction to the premise, which sharpens rather than weakens it

The guidance states that SONIC already implements per-bin / per-motion concentration caps, so the
mjlab floor bug does not exist there. The first half is true in code and **false in configuration**.

| claim | verdict | evidence |
|---|---|---|
| SONIC normalises before mixing, 10% uniform | **true** | `motion_lib_base.py:3225-3238`; `motion.yaml:26 uniform_sampling_rate: 0.1`. Realized uniform mass measured at 0.098–0.163 on the real 1,006-motion BONES-SEED length inventory |
| SONIC implements per-bin/per-motion caps | true **in code** | `:2461-2462`, block at `:3285-3292` |
| ...and they protect the run | **false** | `max_prob_per_bin` and `max_prob_per_motion` are `None` in **every shipped yaml**, so the block early-returns. `"auto"` resolves to 200/N, also inert |
| the 200×mean heavy-tail clip protects the run | **false** | failure rates are ≤ 1, so a 200×mean bound binds only below mean failure rate 0.005 — an almost-solved bank |
| net effect | one always-failing clip still takes **34–45× its fair share** | measured by driving `sync_and_compute_adaptive_sampling` directly |

Why this strengthens the thesis. If the caps were on, the counter-argument would be "adaptivity is
already safe". They are off, and even switched on they are **feasibility-blind**: a 5×-fair cap still
spends 5× fair share on a physically impossible segment, and — the real point — *a cap cannot say
where that mass should go instead*. It bounds waste. FGAS reallocates it.

That contrast is directly measurable and is already pre-registered as a falsifier: P11 in
`GR00T-WholeBodyControl/docs/prediction_register.md` predicts the cheap cap recovers at least half of
the hygiene gain. If P11 holds, FGAS's marginal value is small and we should say so. If it fails
specifically on the ground-contact stratum, that is the FGAS result.

## What this changes in the mjlab work

### 1. The floor fix is a control, not the contribution

mjlab's `_adaptive_sampling` (`src/mjlab/tasks/tracking/mdp/commands.py:258-259`) uses an additive
offset, so `adaptive_uniform_ratio: 0.1` is not a floor. If FGAS were built on top of that, its
effect would be confounded with simply repairing a broken floor. mjlab therefore needs **three**
sampler levels, not two:

| level | what it is | role |
|---|---|---|
| `additive` | upstream mjlab, unchanged | documents the confound; explains why upstream curricula collapse |
| `mixture` | normalise-then-mix, exact floor | the honest baseline FGAS must beat |
| `mixture + FGAS` | eligibility mask `m_b` | the method |

Keeping `additive` as the shipped default (as already specified to the builder) is what makes this
design possible — the baseline stays reproducible.

### 2. mjlab is the better place to *iterate* FGAS; SONIC is where a second claim lives

mjlab's tracking sampler is **natively time-bin-level within one clip** — `bin_count` bins over
`motion.time_step_total` — which is exactly the axis `m_b` lives on. The `climb` overlay adds a clip
axis on top, so mjlab offers both axes, a much faster loop, and nine completed baseline runs.

### 3. The guard band has a different width *and a different reason* in each framework

This is the sharpest technical point in the guidance, and it does not transfer unchanged. Verified:

- **SONIC** (`sonic_bones_seed.yaml:46-47`): `num_future_frames: 10 × dt_future_ref_frames: 0.1` =
  **1.0 s of future reference inside the observation** (base default is 5 × 0.1 = 0.5 s). Zeroing a
  bad bin's sampling probability is therefore *insufficient*: the encoder is still asked to represent
  impossible future targets from a start point up to a second earlier. A guard band ≥ 1.0 s is
  mandatory, and the contamination is **representational**.
- **mjlab**: the tracking observation group is `command`, `motion_anchor_pos_b`, `motion_anchor_ori_b`
  — the **current** reference anchor, with no future window. So mjlab needs **no observation-side
  guard band at all**. It still needs a dynamics-side one, because an episode started earlier
  physically walks into the bad segment and its termination is charged to whichever bin it lands in.
  The contamination is **credit-assignment only**.

That asymmetry is useful rather than annoying: mjlab isolates the exposure/credit mechanism with the
representation confound absent, and SONIC then tests whether the representational channel adds
anything. Two frameworks, two separable claims.

### 4. Segment-level output is mostly already built

The guidance asks the screen to emit per-frame arrays and segment structure rather than one scalar
per clip. `tools/n1_knee_id.py` already writes per-frame rows (`"frames": rows`) **and** 0.25 s bin
summaries (`"bins"`) in its full, non-`--brief` output. What is genuinely missing is the derived
layer:

```
contiguous high-confidence infeasible windows
  -> guard-band expansion (0 s in mjlab, >= 1.0 s in SONIC)
  -> contiguous feasible segments, minimum-length filtered
  -> projection onto the sampler's bin grid -> m_b
```

That is a reducer over existing output, not a new screen.

## Measured 2026-08-19: what segment-level curation actually recovers

Full-mode (per-frame) screen of the **99 flagged clips of `tier_800`**, reduced by
`tools/screen_segments.py`. Cost: 99 clips in **45 s wall** on 6 nice'd CPU workers — the screen
is cheap enough that re-screening for segment structure is not a budget item. tier_800 is
152.4 min over 800 clips; the flagged clips are 20.2 min of it.

| guard band | recovered from the flagged 20.2 min | sampler bins usable | clips fully lost |
|---|---|---|---|
| **0 s** (mjlab: no reference lookahead) | **12.5 min = 61.7 %** | 584/1259 (46.4 %) | **3 / 99** |
| **1.0 s** (SONIC: `num_future_frames` 10 x 0.1 s) | 5.8 min = 28.9 % | 305/1259 (24.2 %) | 26 / 99 |

Against the whole bank: clip-level pruning (what E-HYG's `tier_800_pruned` does) discards
**13.3 % of the bank's duration**; segment-level curation hands **8.2 %** of the bank back in
mjlab, **3.8 %** in SONIC.

Two things follow.

1. **Pruning is expensive.** 61.7 % of what the pruned arm throws away is dynamically feasible
   material, and only 3 of 99 flagged clips are irrecoverable end-to-end. E-HYG's prune arm is
   therefore a *lower* bound on what hygiene can buy, not the ceiling — which is the argument for
   arm C (repair, N preserved) and for FGAS over pruning.
2. **The guard band is the dominant cost, and it is a property of the framework, not the data.**
   A 1.0 s reference lookahead more than halves the recovery (61.7 % -> 28.9 %) and takes clips
   fully lost from 3 to 26. Identical screen, identical clips. This is the sharpest available
   statement of the mjlab/SONIC asymmetry recorded above, and it generalises: **the value of
   segment-level curation falls as the policy's reference lookahead grows.** Worth a figure.

Caveat: `--min-seg-s 1.0` and `--min-bin-frac 1.0` (strict: any severe frame disqualifies a bin)
are choices, not measurements. FGAS-3 should sweep them alongside the guard width.

## Measured 2026-08-19: the sampler fix caps waste but does not redirect it

From the nine completed `mixed100` runs, with no new training. `tier_mixed100` is 100 clips of
which **25 are flagged** (`infeasible_frac > 0.10`). Both the `adaptive` and `grounded` arms route
through `_adaptive_sampling` (`climb/commands.py:174-180` borrows the adaptive branch), so both log
a real `p.argmax()` and are directly comparable. The `uniform` arm is **excluded**: its
`sampling_top1_bin` is the hardcoded sentinel 0.5 and its `top1_prob` is `1/n`
(`climb/commands.py:139-141`), so any log-derived statistic for it is meaningless; its contamination
is analytic (25 % of draws, by construction).

`mean(top1_prob x 1[top-1 clip is flagged])` is a **lower** bound on total flagged mass, since the
total sums over all 25 flagged clips and this counts only the leader:

| arm | P(top-1 is flagged) | enrichment vs 25 % | mean top-1 mass | flagged mass (lower bound) |
|---|---|---|---|---|
| `adaptive` (additive) | **72.9 %** | **2.9x** | 0.488 | **>= 36.9-39.9 %** |
| `grounded` (mixture)  | **73.7 %** | **2.9x** | 0.339 | **>= 27.3-28.8 %** |
| `uniform`             | 25 % (analytic) | 1.0x | 0.010 | 25 % exactly |

How the attractor forms (mean over three seeds):

| iterations | adaptive P(top-1 flagged) | grounded |
|---|---|---|
| 0-500 | 31.9 % (1.3x) | 41.4 % (1.7x) |
| 500-1000 | 42.6 % (1.7x) | 23.9 % (1.0x) |
| 1000-2000 | **96.1 % (3.8x)** | **95.1 % (3.8x)** |
| 2000-3000 | 81.2 % (3.2x) | 91.5 % (3.7x) |
| 3000-4000 | 77.0 % (3.1x) | 75.6 % (3.0x) |

**The result.** Flagged clips are a quarter of the bank and hold the top slot roughly three
quarters of the time — and **that enrichment is identical under the fixed sampler**
(72.9 % vs 73.7 %). What the normalise-then-mix fix changes is only *how much* the leader receives
(0.488 -> 0.339), which is why the flagged-mass bound falls from ~39 % to ~28 %.

So the sampler fix **caps the waste without redirecting it**. That is not a defect of the fix; it
is a statement about what a mixture can do. A uniform floor and a concentration cap are both
*feasibility-blind*: infeasible clips genuinely do fail most often, so they genuinely do win a
failure-weighted competition, and no reweighting of that competition can change who wins it. Only
an eligibility mask changes the ranking.

This is the cleanest available motivation for FGAS, it comes from data already on disk, and it
predicts the FGAS result precisely: **FGAS should leave `mean top-1 mass` roughly where `grounded`
puts it while driving `P(top-1 is flagged)` to ~0.** If instead FGAS also collapses the top-1 mass,
something else changed and the comparison is confounded.

Caveats. The table's flagged-mass column is a bound, not a total — the total is higher, by however
much the non-leading flagged clips hold. Enrichment is the robust half of this result (identical
code path, same statistic, three seeds each); the mass column depends on `top1_prob`, which is a
genuine logged measurement but only of the leader.

## Measured 2026-08-19: clip-level thresholding is wrong in *both* directions

`tools/build_eligibility_sidecar.py` produced per-bin `m_b` for `tier_800` and `tier_mixed100`
(`reports/eligibility/`, `reports/eligibility_summary.md`, set hashes in that file). Binning the
clips by their clip-level `infeasible_frac` and reading off the bin-level eligible fraction shows
the clip-level screen is a lossy proxy in each direction. tier_800, guard 0 s:

| clip-level `infeasible_frac` | clips | eligible bins | what the clip-level rule does |
|---|---:|---:|---|
| [0.00, 0.01) | 585 | 99.6 % | keeps — correct |
| [0.01, 0.05) | 76 | 82.4 % | keeps — but ~1 bin in 6 is bad |
| **[0.05, 0.10)** | **39** | **72.2 %** | **keeps whole — yet 28 % of its bins are infeasible** |
| **[0.10, 0.15)** | **22** | **57.3 %** | **prunes whole — discarding 57 % good bins** |
| [0.15, 0.25) | 37 | 52.8 % | prunes whole |
| [0.25, 0.50) | 41 | 37.6 % | prunes whole — still 38 % good |

The threshold at 0.10 sits in the middle of a continuum, and the vertical spread at every
`infeasible_frac` is large: clips with the same clip-level score differ by more than 50 points of
bin-level eligibility. So:

- **False negatives.** 140 of the 701 *unflagged* tier_800 clips lose at least one bin, admitting
  **5.43 minutes** of infeasible material that the clip-level screen passes (11.39 min at guard
  1.0 s). This direction was not previously measured at all, and it means the "pruned" bank is not
  clean — it is merely *less dirty*.
- **False positives.** Of the 20.21 minutes the clip-level rule deletes, the hard bin mask keeps
  **9.16 min (46.4 %)**.

**The soft mask is worth having.** Frame-level feasible material in the flagged clips is 12.48 min,
but the hard bin mask keeps only 9.16 min: a bin straddling the edge of a severe window is
discarded whole even when most of it is feasible. `bin_score` (fraction of the bin surviving)
recovers the full 12.48 min — **36 % more material than the hard mask** at identical guard. That is
the argument for running FGAS with soft `m_b` rather than a 0/1 mask, and it costs nothing extra:
the sidecar carries both, and thresholding `bin_score` at `min_bin_frac` reproduces `bin_eligible`
exactly (asserted by the builder).

Sample sizes shrink fast per band, so read the [0.10, 0.15) and [0.25, 0.50) rows as indicative
(22 and 41 clips). The two-directional claim rests on the aggregate counts, which are large.

## Measured 2026-08-19: the exposure ledger works, live

The deferred exposure-ledger patch was applied to an **isolated copy** of `climb/` + `tools/`
(`~/.claude/jobs/a4c9ac13/tmp/fgas_iso/`), leaving the live sealed chain untouched — verified:
0/217 protected files changed, chain hashes intact. `tools/climb_train.py` resolves `climb` from
its own parent directory (`:20`), which is what makes the isolation complete. This is the pattern
to reuse for every experiment while the chain runs.

First dump, `adaptive` on `tier_mixed100` at iteration 0: **true flagged mass 25.1 %** against a
25/100 base rate, normalised entropy 0.930, top-1 mass 0.043. The sampler starts unconcentrated, as
it must, and the ledger returns the *total* rather than the top-1 lower bound the completed runs
allow. The mechanism is confirmed.

**Caveat on this pilot, stated before its results exist:** it runs 400 iterations, and the offline
time course puts flagged-clip enrichment at only 1.3x over iterations 0–500, peaking at 3.8x around
1000–2000. So this run measures the *approach* to the attractor, not the attractor. It validates
the instrument and the early trajectory; it cannot confirm or refute the ~39 % figure, and must not
be quoted as if it could.

## Measured 2026-08-19: feasibility predicts failure beyond kinematics — but not the flag we flag on

Evidence layer 1, run on artifacts already on disk: 100 eval clips, endpoints at iteration 3999
averaged over three seeds, for all three arms. `tools/analyze_feasibility_predicts_failure.py`,
output `reports/feasibility_predicts_failure.json`.

**This is a zero-shot measurement.** The campaign eval CSVs score `heldout100.txt`, which is
**disjoint from the training bank** `tier_mixed100.txt` — verified, 0 of 100 clips shared. I
initially described these as "eval clips" without noticing that, and the distinction matters in our
favour: on training clips a failure-adaptive sampler trains *more* on whatever fails, so per-clip
survival would partly measure exposure rather than difficulty. On held-out clips that confound is
absent, and the same partial correlations hold for policies trained under three different samplers,
none of which ever saw these references.

The raw correlation does **not** establish the claim, and it is important to say so. The single
best predictor of survival is a *kinematic* descriptor, `com_height_range` (ρ = −0.598), narrowly
ahead of the best feasibility one (`unsupported_impulse_per_weight_s`, ρ = −0.579). A screen that
merely re-encodes "this clip crouches or jumps" would look exactly like that. The test that matters
is the partial correlation after residualising against ten kinematic descriptors (posture
excursion, flight fraction, jerk, required friction, joint speed, non-foot contact, translation
speed, duration, contact churn, ground clearance):

| arm | outcome | `unsup_impulse` | `infeasible_frac` | `airborne_frac` | `max_tau_ratio_p95` |
|---|---|---:|---:|---:|---:|
| uniform | survival | **−0.299** ** | −0.124 | +0.074 | −0.027 |
| uniform | −body_pos_err | **−0.330** *** | **−0.337** *** | −0.183 | −0.153 |
| adaptive | survival | **−0.447** *** | **−0.279** ** | −0.060 | +0.035 |
| adaptive | −body_pos_err | **−0.319** ** | **−0.369** *** | −0.186 | −0.010 |
| grounded | survival | **−0.363** *** | −0.178 | −0.008 | −0.055 |
| grounded | −body_pos_err | **−0.297** ** | **−0.398** *** | −0.240 * | −0.063 |

Cross-validated predictive R² (5-fold × 20 repeats, ridge on rank features): the four-feature
feasibility block **out-predicts the ten-feature kinematic battery on five of six** combinations
(e.g. adaptive/survival 0.335 vs 0.231), and adds **+0.035 to +0.077** on top of it.

Three things follow, and the second is uncomfortable.

1. **Dynamic feasibility carries real, independent information.**
   `unsupported_impulse_per_weight_s` survives the full kinematic control on **6 of 6**
   arm × outcome combinations (p < 0.01 throughout). This is the claim the project needs, and it
   holds. `com_height_range` also survives control for feasibility (−0.391, p = 0.0001), so
   neither family subsumes the other — they are complementary, which is the honest framing.

2. **The binary flag is the weakest member of the block.** `infeasible_frac`, the quantity the
   whole 22.8 %-prevalence and prune/repair story thresholds on, is **outcome-dependent**: robust
   on tracking error (3/3, p < 0.001) but unreliable on survival (significant in 1 of 3 arms).
   `airborne_frac` alone is essentially null once kinematics are controlled (1 of 6, marginal) —
   which is precisely consistent with the SONIC `kneeling_loop_*` clips that sit at
   `airborne_frac = 1.000` with `infeasible_frac = 0.000`.

3. **Actionable, and it changes the FGAS design.** `m_b` should be built from **continuous
   severity** (`unsupported_impulse_per_weight_s`), not from the binary `infeasible_frac > 0.10`
   threshold. The sidecar already carries a continuous `bin_score`, so this is a change of source
   quantity, not of machinery. It also means the soft-mask arm is the *primary* FGAS arm and the
   hard mask is the ablation, rather than the other way round.

For the write-up: the prevalence headline is a **data-quality** statement and should stay one. It
should not be presented as the quantity that predicts failure — on this bank, the impulse is, and
the flag is a coarser proxy for it.

Caveats. n = 100 clips, one bank, one eval protocol; ten controls on n = 100 is heavy conditioning;
and `both` occasionally scores below `feasibility only` (ridge paying for ten weakly-informative
features), so the incremental column is a floor, not a ceiling. All of this is correlational — the
repaired-vs-raw paired intervention remains the causal test.

## Measured 2026-08-19: contamination, independently verified — and one framing that must not be used

`tools/analyze_adaptive_contamination.py` → `reports/adaptive_contamination.{json,md}`. Every
number below was re-derived a second time by an independent verifier with its own `tfevents`
parser; agreement to ≤ 0.02 pp (float32 accumulation order).

| arm | flagged mass (lower bound) | infeasible-frame share (LB) | P(top-1 flagged) | effective support `exp H` |
|---|---|---|---|---|
| `adaptive` | 38.98 / 39.91 / 36.87 % | 7.00 / 6.49 / 6.72 % | 70–78 % | **7.2 – 9.9 clips of 100** |
| `grounded` | 28.81 / 27.32 / 27.67 % | 4.88 / 4.32 / 4.39 % | 73–82 % | 21.8 – 23.2 |
| `uniform` | 25.00 % (exact, analytic) | 6.060 % (exact) | 25 % | 100 |

Three results worth keeping:

- **The collapse lands on one specific, independently-identified clip.** Index 44 =
  `BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos` (`infeasible_frac` 0.130) is the
  dominant argmax by mass in **all six runs**, both arms, all three seeds — 21.9 % of all top-1
  mass under `adaptive`, 17.7 % under `grounded`. This is the sealed N1 clip #44, established as
  reference-infeasible by knee-ID analysis long before this measurement existed. Two independent
  routes to the same clip.
- **79.2 % (adaptive) / 82.2 % (grounded) of all top-1 mass sits on flagged clips**, against a
  25 % base rate.
- **Adaptive's top-1 clip *alone* delivers more infeasible frames than the uniform arm's entire
  curriculum** — 6.5–7.0 % vs 6.06 %, in all three seeds.

### What must NOT be claimed

1. **`grounded` is not FGAS.** `climb/commands.py:61-62` makes it `mixture` mode with **no
   eligibility mask**. This campaign measures *floor repair*, not feasibility grounding.
   Adaptive-vs-grounded is not evidence for FGAS — grounded is the baseline FGAS has to beat.
2. **No total is available.** The simulation that would have converted the lower bounds into totals
   **failed its pre-declared validation gate on 0 of 8 cells**, and modelled mass spanned a factor
   of 9.9 across cells. No modelled total is reported. The root cause is worth recording: the eval
   CSVs are on the *held-out* bank, so per-clip failure rates for the *training* clips simply do
   not exist in any artifact.
3. **The arm ordering on the total is not robust.** The lower bounds order adaptive (38.6 %) above
   grounded (27.9 %), and both above uniform's exact 25.0 %. But under a self-similar residual
   assumption the totals *reverse* (79.1 % vs 82.1 %). The defensible claims are about
   **concentration** (`exp H`: 7–10 clips vs 22–23 vs 100) and about the **lower bound**, not the
   total.
4. **Grounded's frame-share LB (4.3–4.9 %) is *below* uniform's exact total (6.06 %).** On the
   frame metric the floor-repaired arm cannot be shown to beat uniform from the lower bound alone.

The builder also found and fixed two bugs in its own code that would have shipped wrong numbers —
a ones-vector that silently degenerated the flagged-mass statistic into `mean(top1_prob)` (49.8 %
instead of 39.0 %), and an invalid convex-program endpoint that randomised falsification broke on
9,413 of 21,773 samples. A claim it nearly headlined ("adaptive's rigorous minimum infeasible-frame
share is 1.6× uniform's total") was an artifact and is withdrawn.

## The arm matrix

The guidance's five arms and the matrix already drafted for SONIC each control something the other
misses. The union:

| arm | bank / segments | sampler | controls for |
|---|---|---|---|
| raw | raw | uniform | data + sampler floor |
| raw | raw | adaptive (mixture) | the honest baseline |
| raw | raw | adaptive + **cap** | is bounding waste enough? (P11) |
| feasible segments | ReFeas-curated | uniform | curation alone |
| feasible segments | ReFeas-curated | adaptive + **FGAS** | **the method** |
| random matched | duration/category-matched removal | adaptive (mixture) | "less data trains faster" |

The random-matched control must match removed **frames**, category, duration, source, contact regime,
root speed and body-height — not just clip count. The stronger variant, duration-preserving
substitution (replace each removed segment with a same-category feasible segment of similar length),
keeps total consumed motion duration equal across arms and is worth the extra bookkeeping.

Do not change reward, PPO, or the network. Only motion eligibility and exposure. Reward-aware soft
weighting is an appendix ablation, not the method — an impossible reference contaminates the
observation, the encoder, the critic, the auxiliary reconstruction loss, the sampler statistics and
the termination distribution, so masking its reward alone does not clean it up.

## Evidence order

Four layers, in this order, because each one localises the failure of the next:

1. **Zero-shot audit** — released checkpoint, no training. Does ReFeas severity predict termination
   and MPJPE *at matched category, root speed, posture and contact regime*? The matched comparison is
   the point; a global correlation would only prove the screen re-encodes "jump" and "crawl".
2. **Exposure contamination** — does the adaptive sampler actually give non-trivial probability mass
   to infeasible bins during training? If it does not, nothing downstream can matter.
3. **Stratified outcome** — feasible-heldout (primary), feasible-hard (mechanism), raw-infeasible
   (diagnostic, never a ranking endpoint), repaired-paired (the within-motion counterfactual).
4. **Downstream traversal** — last, with the high-level planner fixed and only the low-level WBC
   swapped.

Statistical unit is the **motion**, not the episode. Uncertainty by motion-level or seed×motion
hierarchical bootstrap.

## Immediate order of work

1. FGAS in `/home/robotixx/mjlab` — three sampler levels, `m_b` mask, telemetry. Blocked until the
   running floor-fix workflow releases that checkout.
2. The segment reducer (frames+bins → guard-banded feasible segments → `m_b`) as a new tool in
   `climb/tools/`.
3. Zero-shot audit on existing climb checkpoints — needs GPU, so queued behind the N3/E-HYG chain.
4. SONIC adapter + released-checkpoint stratified evaluation + N3-on-SONIC, per the guidance's own
   priority ordering, ahead of any full BONES-SEED training.

**Blocked and deliberately not done:** `climb/commands.py` and `mjlab-1.6.0/src/mjlab/**` are
live-imported by the running sealed chain (verified by import path from the running interpreter).
No FGAS lands there until the chain reports `reports/E_HYG/EVALS_DONE` and no `climb_train.py` is
running.

## Pre-registrations

Registered 2026-08-19, before FGAS has been run. FGAS-1 is already resolved by the measurement
above; the other two are open. Baselines to predict against are in the two measured sections.

### FGAS-1 — does infeasible reference actually reach the optimizer? **RESOLVED: yes.**

Registered as a kill-switch: a near-zero contamination would have ended the method honestly.
Measured instead at **≥ 36.9–39.9 %** of sampling mass under `adaptive` and **≥ 27.3–28.8 %** under
`grounded`, against a 25 % base rate, with flagged clips holding the top slot **2.9× more often
than chance in both arms**. The mechanism is real and it survives the sampler fix.

### FGAS-2 — does FGAS move the attractor, or only shrink it? **OPEN.**

This is the load-bearing one, and it is not trivially true. Segment-level masks leave most flagged
clips *partly* eligible (clip #44 keeps 7 of 10 bins at guard 0 s), so a flagged clip can still win
the competition on its feasible parts. Two outcomes are distinguishable in advance:

| | `P(top-1 clip is flagged)` | `mean top-1 mass` | reading |
|---|---|---|---|
| baseline `grounded` | 73.7 % | 0.339 | measured |
| **FGAS predicted** | **falls below 40 %** | **stays 0.30–0.38** | the attractor *moves*: exposure is redirected to feasible-hard clips |
| null outcome | stays ≈ 74 % | ≈ 0.34 | FGAS only trims the infeasible *frames* of the same winners; the clip-level attractor is untouched |
| confounded | any | collapses below 0.20 | something other than eligibility changed; do not interpret the arm |

Prediction: **the attractor moves.** `P(top-1 flagged)` below 0.40 with `mean top-1 mass` held in
[0.30, 0.38]. If instead the null outcome holds, the honest conclusion is that segment-level FGAS
is a *frame-level* hygiene measure with no curriculum effect, and the paper should say exactly
that rather than reaching for the stratified endpoints.

Falsifier that would retire the method: `sampling_ineligible_mass` under FGAS is not ~0 by
construction — if the telemetry shows otherwise, the implementation is wrong, not the theory.

### FGAS-3 — guard-band width. **OPEN.**

The 1.0 s figure is read off `sonic_bones_seed.yaml`, not measured as the width that matters.
Sweep 0 / 0.5 / 1.0 / 2.0 s. Known cost from the tier_800 measurement: recovery falls 61.7 % →
28.9 % between 0 s and 1.0 s, and clips fully lost go 3 → 26 of 99. Prediction: **the useful width
in mjlab is 0 s**, because mjlab's observation carries no future reference, and any benefit seen at
larger widths is the dynamics-side effect (an episode running forward into a bad window), which
should be small relative to the material it costs. `--min-seg-s` and `--min-bin-frac` must be swept
alongside; both are currently choices, not measurements.
