# fable.md — Research guidance for CLIMB / feasibility-first (2026-08-27, rev 3)

**Author:** Claude Fable 5, from a full read of `plan/STATUS.md`, the sealed result files,
`paper/RESULTS_LOG.md`, `RED_TEAM.md`, the DFRP v0/v1 results, the Newton direction addendum,
the segment-native follow-up, and the autoresearch logs through `autoresearch-260821-0115`.
**Status:** unsealed guidance. Not a preregistration; authorizes nothing by itself.
**Rev 2 (Aug 26, evening):** Phase-W tranche W2–W5 landed and verified (§7).
**Rev 3 (Aug 27, 01:00):** Phase N sealed and the real N-c probe is running (§9). B1–B3 closed. Next directive is §10; §8 is kept as the record of what was asked.
Supersedes the aspirational plan in `/home/robotixx/newton/fable.md` (Aug 2026 v1), which
predates every measured result below.

---

## 0. One-paragraph verdict

The project has already produced its paper. The *measurement* line is strong, sealed, and
public: sampler collapse on a physically impossible clip, the ε-non-floor, the 22.8 % vs 0.14 %
cross-corpus prevalence contrast, the anatomy of clip #44, feasibility features as the first
policy-transferable difficulty labels, and a released tool. The *intervention* line is, as of
today, a sequence of honest nulls: E-HYG (prune) null, FGAS (soft segment) fails its wiring gate,
N7 (repair-all) misses SESOI with the benefit sitting in over-budget edits, P-SIGN fails, the
segment-v2 adaptive arm is 0.014 TV from its own control. **The correct reading is not "the
intervention doesn't work"; it is "we have not yet run an intervention arm whose manipulation
check passes."** That is the single thing the next GPU window must fix, and it is cheaper than
any of the four programs (DFRP-at-scale, Newton fragility, Universal Atlas, SafeTrack) currently
competing for attention. Everything below follows from that.

---

## 1. Where the project actually stands (Aug 26)

### 1.1 What is settled and should not be reopened

| claim | label | artifact |
|---|---|---|
| Failure-adaptive sampler collapses (top-1 0.87–0.89) onto one clip; that clip's descent is dynamically infeasible (~329 N unsupported vs 327 N robot) | sealed ✓ | `reports/A5_coverage_dose.json`, `reports/N1_clip44_knee_id.json` |
| ε/N is not a floor; normalise-then-mix repairs it (+0.030/+0.028/+0.030 per seed) | sealed ✓, upstream-filed | mjlab#1153, wbt#73 |
| 22.8 % of the AMASS→wbt→G1 bank is >10 % infeasible; BONES-SEED/SONIC is 0.14 % — *per corpus-and-pipeline pairing* | measured, pre-registered P10 | `reports/feasibility_all/`, P10 register |
| Feasibility features lift cross-policy difficulty transfer 0.567→0.609 (p = 0.010) | sealed ✓ (F2) | `reports/N_atlas_v21.json` |
| Dual-stack conformance \|Δq̇\| ≤ 3e-5 after four integration fixes | measured | `plan/S1_RESULT.md` |
| G1 physics-fragility gate: #44 is a coverage failure, not physics fragility | sealed ✗ (kept) | `plan/G1_RESULT.md` |
| Exact DFRP repair contract: 22/26 flagged + 4/4 byte-identical controls, 36 units, 10,561 legal starts, fail-closed hash binding | measured (implementation gate) | `reports/dfrp_v1_exact_panel/iter1/` |

### 1.2 The nulls, read correctly

Each null has a *specific* reason that is not "the idea is wrong":

- **E-HYG** (prune 99/800 clips): the treatment differed from control by 12 % of clips that
  the policy was already failing on. A prune removes exposure the policy wasn't converting
  anyway. Expected null; sealed as such. Do not re-run pruning.
- **FGAS soft**: failure weighting swamped the clip-mean multiplier (late rejected mass 0.199 >
  0.15). This is the *raw-failure-flux* sampler bug the three independent reviews later found
  (`SEGMENT_NATIVE_FOLLOWUP` §Load-bearing findings 1–5). The v2 runtime fixes it. The null is
  about the old sampler, not about segment-native curation.
- **N7**: +0.0397 decomposes as −0.0036 (policy) + 0.0233 (reference) + 0.0200 (interaction),
  with the gain concentrated in 11 over-budget (>15 cm) edits. Lesson: repair changes the
  *target*, so a survival contrast against the raw reference is not a policy claim. The 8 cm
  budget + fidelity metrics in DFRP v1 are the right response; they've been built.
- **P-SIGN**: sign reversal is real on #44 (r = 0.92 across seeds) but not general (7/12) and
  not clean on controls (4/12). Dead as a detector; alive as one anatomy paragraph.
- **Segment-v2 pilot**: mechanically clean (zero invalid starts, exact truncation) but the
  adaptive distribution was 0.014 TV from uniform because conditional failure saturated near 1.
  **This is the load-bearing null.** It means no segment-level adaptive arm has yet been
  *tested*; the arm was a uniform arm wearing an adaptive label.

### 1.3 Calendar reality

- v5 schedule: CPU-only to **Sept 15**; companion submittable **Sept 5** (10 days); flagship
  full draft **Sept 12**; results freeze **Dec 1**; RSS 2027.
- Last commit Aug 21 01:45. Five days of no recorded progress in the writing-first window.
- Companion note is v0.2 with zero unresolved majors; it is blocked on Linji's author/scope
  pass and figure typesetting, not on research.
- GPU (RTX 5090, 32 GB) is a shared box; today it carries three foreign jobs and ~30 GB used.
  The Sept 15 "GPU order" assumption should be treated as *gap capacity*, not ownership.

---

## 2. Strategic assessment

### 2.1 The thesis has narrowed, and that is good

The public README already states the real thesis: **difficulty conflates feasibility, support,
and intrinsic hardness, and pipelines that can't tell them apart optimise the wrong objective.**
The flagship's spine (collapse → non-floor → unsupported attractor → grounded repair →
composition N3 → support-moderation E3) is complete except for E3, which is frozen post-Sept 15.

The DFRP advisor guidance (Aug 21) and the Newton direction addendum (Aug 21) each propose a
*second* paper's worth of work. Both are good programs. Neither should be allowed to pull
effort from the flagship before Sept 12, and neither should be started at scale before one
clean segment-native arm exists — because both of them *depend* on that arm:

- DFRP arms 1–3 are "curated bank × sampler" arms. Without a sampler whose manipulation check
  passes, arm 3 vs arm 2 is uninterpretable (it would be FGAS/segment-v2 again).
- Newton G3 vs G2 is "learning-progress + fragility vs learning-progress". G2 is precisely the
  arm that has never been run.

So the dependency graph is: **G1/G2 wiring screen → (DFRP arm 3, Newton G3)**, not the other
way round. The Newton recertification is a *parallel* CPU/small-GPU track, not a prerequisite
for G2.

### 2.2 Three temptations to refuse

1. **Bank-wide DFRP repair as the next milestone.** The 65.8 % census is a legacy root-only
   number at 15 cm; the exact contract admits 22/26 on a *stratified* panel. Extrapolating to
   ~1,600 clips before a single policy has consumed 26 repaired clips is exactly the pattern
   (build the artifact, then discover the training effect is null) that E-HYG and N7 already
   punished. Scale the repair only after a training arm shows the 26-clip view is worth
   consuming.
2. **Making Newton fragility a training signal before it is a predictor.** The direction
   addendum's gate 2 ("no-training predictive gate: Newton vector must improve held-out
   degradation prediction beyond screen + reference features") is exactly right and should be
   held to. G1 already showed same-solver chaos floors ≈ effect sizes on single trajectories;
   N5 fixed that with replicate means. The fragility vector is plausible as an *instrument*
   (companion of the atlas) even if G3 never runs.
3. **Adding a fourth program** (differentiable feasibility, cross-embodiment atlas, terrain,
   SafeTrack). These go to `plan/PARKING.md` with one paragraph each. The no-new-threads rule
   from v5 stands until the flagship draft is assembled.

### 2.3 Where the remaining scientific upside is

Ranked by (probability the sealed result is positive) × (what it adds to the paper):

1. **A segment-native adaptive arm with a passing manipulation check** (G2 in the Newton
   addendum; "exact-feasible conditional segment-adaptive v2" in the follow-up). This converts
   §8 of the flagship from "three nulls and an implementation" into a causal test of the
   thesis's intervention half. Even a null *with a passing manipulation check* is publishable
   as "allocation doesn't help once hygiene is exact", which is a clean statement.
2. **E3 support-moderation** (sealed addendum v2, `2c38845b…`, named gainers/losers). Cheap
   relative to its value — it is the scale test of the atlas result and its predictions are
   already on the record. Runs uniform arms only, so it does not depend on item 1.
3. **Newton v1.5 no-training predictive gate.** CPU + short GPU probes; produces a companion
   instrument regardless of outcome; unblocks or kills G3 without a training seed.
4. **DFRP curated-view training arm (26 clips as a treatment inside G1)** — only after item 1
   shows the sampler is interpretable.

---

## 3. Directive — the next six weeks

### Phase W (now → Sept 12): finish the paper; CPU only

| # | task | done when | owner/notes |
|---|---|---|---|
| W1 ⏳ | Companion note author/scope pass + figure typesetting; re-render `docs/companion.html` | Linji sign-off; `RED_TEAM` rows 3/4/8 closed | blocked on Linji since Aug 20 — this is the critical path |
| W2 ✅ | **Durable copy of the BONES-SEED 4,950-row screen CSV** + sentinel under `reports/feasibility_sonic/` | `RESULTS_LOG` cross-bank row loses its ⚠ | flagged since Aug 19; re-run the screen (0.145 s/clip ≈ 12 CPU-min) if the /tmp copy is gone |
| W3 ✅ | Flagship §8 rewrite as *three nulls, one mechanism*: E-HYG (exposure not converted), FGAS/segment-v2 (manipulation failure), N7 (reference-side gain). State explicitly that no interpretable adaptive segment arm has run and that G2 is the slot | §8 has no "pending 🕐" doing load-bearing work | the honest framing is stronger than a slot promising a positive result |
| W4 ✅ | Fold DFRP v1 (22/26, fail-closed contract, four excluded clips as the case for separate residual/IK gates) into flagship §6 method + companion §8 as **implementation-validated, not policy-validated** | numbers pathed in `RESULTS_LOG` (already), prose landed | one page, no more |
| W5 ✅ (assembly; red-team pass still Sept 5–12) | Assemble `DRAFT_full.md` with slots; red-team pass Sept 5–12 per v5 | `RED_TEAM` open items ≤ 2, both "by construction" | |
| W6 ⏳ | Cross-retargeter feasibility comparison (GMR vs wbt on the 40 shared LAFAN1 clips) — **only if** W1–W5 are done before Sept 5 | one CSV + one sentence in companion §4 | parked idea; one CPU afternoon; strengthens "pipeline property" |

Refuse during Phase W: any GPU training, any new preregistration except the ones in Phase G
(sealing is fine; running is not), any bank-wide repair run.

### Phase N (parallel, CPU + gap GPU, Aug 27 → Sept 15): Newton v1.5 recertification

Follow `plan/NEWTON_SEGMENT_DIRECTION_2026-08-21.md` §Staged gates 1–2 exactly:

- N-a. Fresh isolated venv (`newton15/.venv`), pin Newton 1.5.0 / Warp / MuJoCo 3.11 / MJWarp;
  never touch `mjlab-1.6.0/.venv`. Record pins in `plan/NEWTON15_PINS.md`.
- N-b. Recertify with the S1 six-step protocol on one easy exact unit and one contact-rich
  exact unit from the DFRP v1 unit table (the units are hash-bound; use them). Pass = placement,
  first obs, action, state, contact timing match; deterministic repeats give zero dispersion.
  Expect the G0 lessons to bite again (DR mirror, float32 geometry, stale first obs, clip-wrap
  teleport) — they are documented in `STATUS.md` §G0 lessons; check each before debugging.
- N-c. Seal the **no-training predictive gate** *before* measuring: on a development-only
  panel (the 42-unit mechanism panel from `reports/segment_v2_smoke/`), does the Newton axis
  vector (delay, motor clamp, contact pipeline; 0.25–0.5 s canonical-state probes; replicate
  means per N5) improve held-out-policy degradation prediction beyond `infeasible_frac` +
  reference kinematics? Pre-declare the statistic (partial Spearman / permutation, as in
  atlas v2.1) and the threshold.
- Kill rule (already written, keep it): if N-c fails, Newton is an analysis instrument in the
  companion/appendix and **G3 never runs**. Do not soften this after seeing the data.

### Phase G (Sept 15 → Oct 31, gap-gated GPU): one clean causal test, then E3

**G-0. Seal first (CPU, before Sept 15):** a single preregistration covering a one-seed wiring
screen and a three-seed confirmation of the four-arm design in the Newton addendum, *minus G3*
unless N-c has passed by the seal date:

| arm | support | priority | contrast |
|---|---|---|---|
| G0 | unmasked grounded starts (tier_800, normalise-then-mix) | deployment prior | control — must be a **fresh** arm, not the old grounded checkpoint |
| G1 | exact feasible segments (unit table, guard 0, 50-step trials, explicit truncation) | deployment prior | G1−G0 = exact hygiene |
| G2 | exact feasible segments | learning-progress / uncertainty rank, ρ = 0.10 floor, caps 0.05/0.25 | G2−G1 = allocation |

Mandatory pre-declared **manipulation gate** (the thing every prior arm lacked): after warm-up,
TV(G2, G1) ∈ [0.05, 0.15]; entropy-effective units ≥ 12; realized invalid frames = 0; late
rejected-start mass = 0 (exact support makes this trivially checkable). If the one-seed wiring
screen fails the gate, **stop, fix the rank, re-screen** — do not spend seeds 2–3. This is the
single procedural change that would have saved FGAS and segment-v2.

Primary endpoint: feasible-disjoint survival + AULC under the paired v2 evaluator
(`tools/eval_paired_v2.py`; frozen condition manifest; auto-reset disabled for terminal reads;
no `heldout100` — build a disjoint panel and verify disjointness by hash *before sealing*, per
the N7 audit). Secondary: common-survivor quality noninferiority (MPKPE, anchor orientation,
work) with the CI lower bound, not the point, above margin. Seed × unit hierarchical bootstrap.

Budget note: the segment pilot was 2 arms × 512 envs × 200 it. The confirmation needs
4000-iteration arms; measure realized GPU-hours on the wiring screen and *then* decide whether
three seeds of three arms fit before Dec 1. If not, drop G0 (the hygiene contrast G1−G0 is the
least novel; E-HYG already bounds it) before dropping seeds.

**G-1. E3 under addendum v2** (uniform arms only, 100 vs 800 bank; predictions sealed
`2c38845b…`). Independent of G-0; schedule it in whichever gap opens first. It is the cheapest
positive-expected-value experiment on the board because the predictions are already named.

**G-2. DFRP curated-view arm** — a G1 variant whose 800-clip bank swaps in the 22 repaired
clips (exact sidecars) — only if G-0's wiring screen passes and E3 is scheduled. This is where
the DFRP program earns its first policy number; 26 clips is enough for a paired per-motion
contrast on those 26, not for a bank-level claim. Say so in the seal.

Deferred to post-freeze (Dec 1+), one paragraph each in `PARKING.md`: bank-wide DFRP repair,
G3 fragility-weighted sampling, differentiable feasibility, cross-embodiment atlas, terrain
refeas, SafeTrack runtime guard, SONIC as anything other than an evaluation target.

---

## 4. Standing rules (unchanged, restated because they keep working)

1. Seal-before-run; frozen analysis dry-run on `--synthetic` before outcomes exist.
2. Every arm has a **manipulation check** sealed alongside its endpoint. An arm that fails
   its manipulation check is reported as "not tested", never as a null.
3. Repair changes the target: any repaired-reference contrast reports the 2×2 decomposition
   (policy / reference / interaction) as N7 did, plus fidelity diagnostics.
4. Prevalence numbers are per corpus-and-pipeline pairing. Never "retargeted banks in general".
5. One status label per claim; pending results do no load-bearing work.
6. Every background job writes a sentinel; every paper number has a path in `RESULTS_LOG`.
7. No new threads until the flagship draft is assembled (Sept 12). Ideas → `PARKING.md`.

---

## 5. Risks and what to do about them

| risk | signal | mitigation |
|---|---|---|
| Companion slips past Sept 5 waiting on the author pass | no commits since Aug 21 | Linji: 2-hour scope pass is the only blocker; everything else is done |
| GPU never becomes free enough for 4000-it arms | today: 30/32 GB used by other groups | keep `run_when_free.sh` gap-gating; pre-decide the drop order (G0 first, then seeds) in the seal |
| G2's learning-progress rank saturates like conditional failure did | wiring-screen TV < 0.05 | the manipulation gate catches it in one seed; have the uncertainty/progress variant ready as the pre-declared fallback rank |
| Newton 1.5 recert repeats G0's four integration errors | Δq̇ > 3e-5 on the easy unit | check the four documented classes first; budget 1 week, not 3 |
| Reviewers read §8 as "the method doesn't work" | — | W3 framing: the intervention half is *untested* with a passing manipulation check; the measurement half is the contribution |
| BONES-SEED per-clip CSV is lost | `/tmp` scratchpad gone | re-run the screen: 12 CPU-minutes; do it this week (W2) |

---

## 6. What I would tell the advisor in one line

*The measurement paper is done and public; the one experiment worth GPU before Dec 1 is a
segment-native adaptive arm whose manipulation check passes, with E3 alongside; DFRP and Newton
are excellent second-paper programs and should be gated on that arm, not run ahead of it.*

---

## 7. Progress ledger — 2026-08-26 evening (verified against the tree)

| item | evidence | disposition |
|---|---|---|
| W2 BONES-SEED screen reproduced | `reports/feasibility_sonic/hygiene_screen.csv` (4,950 rows), `COMPLETED.json` (0 failures, 179.8 s wall, 8 workers, μ 0.7 / gap 0.06 / ½-weight, MJCF sha `15a330f1…`); counts 29/7/5 infeasible and 225/111/32 airborne at >0.05/>0.10/>0.20; flagged duration 0.000939 | **closed.** `RESULTS_LOG` cross-bank row loses its ⚠. External screen/runner SHAs recorded in `autoresearch/autoresearch-260826-1617/research_log.md` |
| W3 §8 reframed | `paper/flagship/S8_causal_slots.md` §8.5 "exact mechanics, failed manipulation [exploratory; not tested]"; 0.014 TV / corr 0.998 stated | **closed** |
| W4 DFRP v1 folded | flagship §6, companion §8, §10 limitations; `RED_TEAM` row 26 | **closed** |
| W5 assembly + render | `DRAFT_full.md`, `docs/{companion,flagship}.html` regenerated; section↔draft diff content-identical | **closed** (red-team pass itself still scheduled Sept 5–12) |
| RED_TEAM #3 upstream threads | mjlab #1153 and wbt #73 both open, no maintainer ack or linked fix | **closed as a check**; drafts say only "filed" — keep it that way |
| PARKING | five deferred programs written with their wait conditions | **closed** |
| Working tree | 14 modified + 3 untracked, no sealed file or manifest touched, `git diff --check` clean, **not committed** | see §8.0 |

Remaining companion blockers (as reported): Linji's author/scope sign-off; the expanded 5+5
extreme-source inspection; final bibliography pass; same-clip cross-implementation check.

---

## 8. Next directive (rev 2)

Phase W's deliverables that did not need Linji are done. The critical path is now Linji's
sign-off, which is external to this workspace; the correct move is to **start Phase N in
parallel** and to **draft the Phase-G seal on CPU** so that neither waits on Sept 15.

### 8.0 Commit the tranche first (today)

One commit, scoped to the Phase-W files, subject like `Close second-bank artifact hygiene and
reframe §8 around null mechanisms`. Include `fable.md` and `autoresearch/autoresearch-260826-1617/`.
Do not commit `reports/feasibility_sonic/` per-clip intermediates (already removed — good). Push
so the public page reflects the reframed §8 before any external reviewer reads it.

### 8.1 Close the four companion blockers (CPU, this week, in this order)

| # | blocker | definition of done | notes |
|---|---|---|---|
| B1 | **Same-clip cross-implementation check** | Pick ≥ 10 clips present in *both* banks' source families is impossible (different corpora) — so instead run the CLIMB screen (`tools/n1_knee_id.py` / `refeas`) on 20 BONES-SEED clips (the 7 flagged + 13 random feasible) and the SONIC screen on 20 AMASS clips (10 flagged incl. #44, 10 feasible). DoD: a 40-row table with both implementations' `infeasible_frac`/`airborne_frac`, Spearman ρ, and the flag agreement matrix; goes to companion §4 as one sentence + appendix table; artifact `reports/feasibility_xcheck/` with sentinel | This is the single most reviewer-proofing item left: the 160× contrast currently rests on two *different* implementations. If agreement is poor, the contrast becomes "two screens, two banks" and must be reworded before submission. Do it before B2. |
| B2 | **5+5 extreme-source inspection** | For CNRS (100 %) and Transitions (90 %): 5 clips each, hand-inspected with rendered airborne-window frames + lowest-geom clearance trace; extends `reports/upstream_drafts/CNRS_AUDIT.md`. DoD: verdict per clip (ingest / content / scene-mismatch), median clearance, one figure panel | Reuse the CNRS_AUDIT script; budget one afternoon |
| B3 | **Bibliography pass** | Every citation in companion + flagship §2 live-verified (the 12 already are); ○-standards entries resolved; `/ars-citation-check` on the companion source | Mechanical; do last |
| B4 | **Linji sign-off** | author list, scope, venue (arXiv + workshop per D2b), title; approval to file the upstream drafts | Send Linji a 10-line summary with links to `docs/companion.html` and the three decisions needed. Nothing else in this file blocks on it. |

Optional W6 (GMR vs wbt on 40 LAFAN1 clips) only after B1–B3.

### 8.2 Start Phase N now (Aug 27 →)

Nothing in Phase N needs Linji or the GPU beyond gap minutes. Concretely, in order:

1. `newton15/` isolated env: Newton 1.5.0, Warp, MuJoCo 3.11, MJWarp pinned; write
   `plan/NEWTON15_PINS.md` with every version + G1 MJCF sha. Verify `mjlab-1.6.0/.venv` is untouched.
2. Port the S1 six-step conformance protocol into the new env against the **DFRP v1 unit table**
   (`reports/dfrp_v1_exact_panel/iter1/unit_table.json`): one easy unit, one contact-rich unit.
   Pass criterion unchanged: placement, first obs, action, state, contact timing match; |Δq̇| ≤ 3e-5;
   deterministic repeats zero dispersion. Check the four G0 error classes *before* debugging.
3. **Seal the no-training predictive gate before measuring** (`plan/PREREGISTRATION_NEWTON_PRED.md`):
   panel = the 42-unit mechanism panel; axes = delay, motor clamp, MuJoCo-vs-Newton contact
   pipeline; horizon 0.25–0.5 s from canonical state; statistic = replicate-mean signed S (N5);
   prediction target = held-out-policy degradation; test = partial Spearman with permutation
   baseline, controlling for `infeasible_frac` + reference kinematics (mirror atlas v2.1 F2);
   threshold declared in the seal. Kill rule: fail → Newton is an instrument, G3 never runs.
4. Frozen analysis with `--synthetic` dry-run, then run.

Budget: one week for 1–2; if recert is not passing by Sept 5, stop and write it up as a limitation
rather than sinking the writing window.

### 8.3 Draft the Phase-G seal on CPU (target seal date Sept 10)

`plan/PREREGISTRATION_G_SEGMENT.md`, covering the one-seed wiring screen and the three-seed
confirmation of G0/G1/G2 (§3 Phase G). Items that must be *in the seal*, because their absence is
what sank the earlier arms:

- the exact rank used in G2 (learning-progress or uncertainty — pick one and name the fallback);
- the manipulation gate: TV(G2,G1) ∈ [0.05, 0.15] after warm-up, ≥ 12 entropy-effective units,
  0 realized invalid frames, 0 rejected-start mass; fail → stop after seed 1, fix rank, re-screen;
- a **disjoint evaluation panel** built now, with a hash-verified empty intersection against
  tier_800 and the DFRP panel (N7's 8-clip overlap must not recur);
- the drop order under GPU scarcity (G0 first, then seeds), decided in advance;
- the 2×2 decomposition template for any repaired-reference contrast (G-2 later).

Dry-run the frozen analyzer on synthetic data before Sept 15. Then E3 (addendum v2) and the
wiring screen go into the gap queue in whichever order capacity allows.

### 8.4 What not to do this week

No GPU training. No bank-wide repair. No G3. No new preregistrations beyond the two named above.
No edits to sealed files. Do not soften §8's "not tested" wording to make the draft read better.


---

## 9. Progress ledger — 2026-08-27 (verified against the tree; probe in flight)

| item | evidence | disposition |
|---|---|---|
| 8.0 commit | `529e97a`, `c4d1d6f` pushed; tree clean at session start | **closed** |
| B1 cross-implementation check | `reports/feasibility_xcheck/`: ρ 0.984 / 0.997, flags agree 39/40 (κ 0.948) | **closed** |
| B2 5+5 extreme-source audit | recorded in STATUS; no sealed claim changed | **closed** |
| B3 bibliography | 20/20 live-verified | **closed** |
| B4 Linji sign-off | `paper/LINJI_SIGNOFF_ASK_2026-08-26.md` drafted, **not sent** | **open — the only external blocker; send it** |
| N-a pins | `plan/NEWTON15_PINS.md`; trainer venv untouched (freeze hash identical) | **closed** |
| N-b recert | `plan/NEWTON15_RECERT_RESULT.md` **PASS**: easy + contact-rich DFRP v1 units, zero dispersion after seven live-model residuals were mirrored | **closed** |
| N-c seal | `plan/PREREGISTRATION_NEWTON_PRED.md` sealed `b1773fc5…` before outcomes; analyzer `1324aa6f…` passes pass/null/discordant synthetic | **closed** |
| N-c probe | launched 2026-08-27 00:5x on the real 42-unit panel, pid in `reports/newton15_pred/probe/probe.pid`, log `probe_run.log`; ≈ 22 h at 4 worlds/batch | **running** |
| Probe harness repairs | int32 scatter overflow at 42 worlds → subprocess batching; `TensorDict` flatten; OOM retry. Log: `autoresearch/autoresearch-260827-0040/research_log.md` | **closed** (unsealed implementation; batch size in manifest) |
| G-0 panel | `reports/g_segment/panel/` 100 clips, disjoint by name + hash, `ec23b7b9…` | **closed** |
| G-0 seal draft | `plan/PREREGISTRATION_G_SEGMENT.md` DRAFT; pre-seal checklist S1–S7 | **open — target seal Sept 10** |
| S1 G2 rank | `SegmentSampler(rank="learning_progress"\|"uncertainty")`, W = 10, λ = 0.01; ledger logs `rank_saturation_fraction`; 59 tests pass | **closed** (2026-08-27 01:20) |
| S2 exact unit table | `reports/g_segment/unit_table.json`: 800 clips → 1,184 admissible units, 368,951 legal starts; 701 unflagged clips newly screened in full mode (4.5 min, 8 CPU workers) | **closed** |
| S3 eval conditions | `reports/g_segment/eval_conditions.json`: 2,800 conditions, all full-window | **closed** |
| Probe harness, 2nd repair | mjlab's `auto_reset=False` guard refused to step a fallen world at batch 6; the probe now clears `_manual_reset_pending` each step (no reset, no RNG consumed; `alive` masks). Relaunched 01:2x | **closed**; probe **running** |

Three facts the seal work surfaced that change the plan: **G2's learning-progress rank did not
exist in code** (now implemented, S1); the **DFRP v1 panel overlaps `tier_800` by 2 clips** (the
G-2 arm must exclude or disclose them); and **140 of the 701 "unflagged" tier_800 clips contain
severe windows at guard 0** — the FGAS-era `assumeunflagged` eligibility was not exact, which is
one more reason the FGAS null is about wiring, not about segment-native curation.

## 10. Next directive (rev 3)

### 10.0 While the probe runs (≈ 22 h; CPU only; do not touch the GPU)

Do not start any other GPU job; the probe's batches need ~5.6 GB and the foreign jobs already
spike to 27.9 GB. `run_when_free.sh` must not be used to queue anything alongside it.

1. **Send B4.** The 10-line ask is written. Nothing else in this file blocks on Linji, but the
   companion release does.
2. ~~S1~~, ~~S2~~, ~~S3~~ — done (see §9). Remaining before the seal: S4–S7.
2′. *(record)* **S1 — implement the G2 rank** (`climb/segment_curriculum.py`, `segment_runtime.py`): the LP
   rank exactly as §3 of the draft seal defines it (W = 10 ticks, λ = 0.01, `difficulty_power` 0),
   plus the uncertainty fallback; extend `tests/test_segment_{curriculum,runtime}.py` with the
   resume-equivalence property for the new state (`s_u(k − W)` ring buffer must round-trip
   through `state_dict`). This is the single prerequisite the wiring screen cannot start without.
3. **S2 — build the `tier_800` guard-0 unit table** with `tools/build_segment_unit_table.py`
   (`--sidecars reports/segments_v2_tier800_guard0 --horizon-steps 50`) →
   `reports/g_segment/unit_table.json`; record admissible units and legal starts in the draft.
4. **S3 — build the panel's condition manifest** with `eval_paired_v2.build_conditions`
   (7 phases × 4 reps × 3.0 s) → `reports/g_segment/eval_conditions.json`; hash it into the draft.
5. **S4 — frozen analyzer `tools/analyze_g_segment.py`** with four `--synthetic` branches
   (positive / null / inconclusive / gate-fail) that fails closed without the sampler ledger.
6. **S5 — bring `run_when_free.sh` into `tools/`** and make it gate on free memory *and*
   utilization; the `need_MiB` for a 512-env arm is still a guess until the wiring screen.

### 10.1 When the probe finishes

1. Check `reports/newton15_pred/probe/COMPLETED.json` and the manifest: `pass_preflight`,
   `deterministic_repeat_max_abs_delta = 0`, `cross_condition_initial_state_max_abs_delta = 0`,
   `invalid_starts = 0`, `escaped_reference_frames = 0`, motor-clamp realized in ≥ 12 units,
   paired-alive ≥ 0.80 everywhere. **If any fails → "not tested"**; repair under a dated
   addendum; re-run. Do not look at the effects table first.
2. Run the frozen analyzer unchanged (10,000 permutations, seed 20260826) →
   `reports/newton15_pred/result.json` + sentinel. Record the verdict verbatim in
   `plan/STATUS.md`, `paper/RESULTS_LOG.md`, and `PARKING.md` (G3 entry).
3. **Kill rule stands:** valid-data fail → Newton is an instrument; G3 never runs; the
   fragility vector goes to the companion appendix. Pass → G3 remains *eligible* for its own
   later seal; it still does not run before G2 has a passing manipulation check.
4. Commit the probe artifacts (`effects.csv`, `probe_manifest.json`, `COMPLETED.json`,
   `result.json`, `launch_env.txt`, `gpu_watch.log`) in one commit with the research log.

### 10.2 Seal Phase G (target Sept 10)

When S1–S6 are closed: freeze `plan/G_SEGMENT_FREEZE.sha256`, append the document hash to
`plan/SEALS_2026-08-19.sha256`, dry-run the analyzer on synthetic data, and put the one-seed
wiring screen and E3 (addendum v2) into the gap queue in whichever order capacity allows.
The wiring screen's sentinel must record realized GPU-hours and peak memory; the three-seed
decision (and the G0-first drop) is made from that number, not from an estimate.

### 10.3 What not to do

No second GPU job while the probe runs. No G3. No bank-wide repair. No edits to sealed files or
to the frozen analyzer. No softening of any threshold in the draft seal after S1–S4 exist —
the draft is a draft only until the hashes are written, not until the numbers look right.
