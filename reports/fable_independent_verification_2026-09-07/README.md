# Independent pre-submission verification — 7 September 2026

**Classification: measured document and artifact checks; no scientific contract, seal, threshold,
arm, seed or endpoint changed.** No GPU job was launched, stopped or altered. The live H1 campaign
and its automated reporting chain were read only.

This is an *independent* pass over work produced earlier the same day. It repeats the checks from
its own sources rather than accepting the existing build audit and internal review. Where this
record and an earlier document disagree, the disagreement is stated rather than resolved silently.

## 1. Numbers reproduced from source artifacts

Recomputed with `mjlab-1.6.0/.venv/bin/python` from the named artifacts, not from the manuscript.

| Manuscript quantity | Source | Recomputed | Verdict |
| --- | --- | --- | --- |
| Final feasible-hard R−U mean | `reports/relative_confirmation_results_2026-09-06/summary.json` | −0.015068459268 | matches to 1e-12 |
| Its two-sided seed-t 95% CI, df=2 | same | [−0.094358426, +0.064221508] | matches to 1e-9 |
| All-panel R−U mean and CI | same | −0.009315506, [−0.114046328, +0.095415315] | matches to 1e-9 |
| Seed sd used in Limitations | derived from the three seed deltas | 0.0319185 (paper 0.03192) | matches |
| t half-width in Limitations | `t.ppf(.975,2)·sd/√3` | 0.0792858 (paper 0.07929) | matches |
| Screen prevalence | `reports/feasibility_all/feasibility.csv`, 10,705 rows | 2,442 = 22.8118% | matches |
| Second-bank prevalence | 7/4,950 | 0.1414% | matches |
| Exact-support units | 1,841 − 657 | 1,184 | matches |
| H1 admitted/rejected units | `gate_on.json`, `gate_off.json` | 1,184 admitted; 1,649 − 1,184 = 465 rejected | matches |
| H1 legal starts | same, summing `legal_start_count` | 368,951 of 417,072 = 88.4622% | matches |

**H1 and the allocation study are directly comparable.** Both bind the byte-identical evaluation
panel `reports/g_segment/panel/panel.txt`, SHA-256 `ec23b7b9…`. H1's 25 `hard_indices` are exactly
the `feasible_hard_reference` stratum of `reports/g_segment/panel/strata.csv`. That stratum is
defined only by reference kinematics (`reference_difficulty_score`, `required_mu_p95`,
`vert_force_bw_max`, `contact_switch_rate`, `flight_phase_frac`, `nonfoot_ground_frac`,
`angmom_peak`, `support_margin_mean`). **No policy outcome enters the panel definition**, so the
primary stratum is not selected on the outcome.

**The H1 analyzer implements the sealed decision rule.** `paper/h1/protocol.py:analyze` averages
clips within seed to five paired values, then uses `t.ppf(.975, 4)·sd/√5`; status is `positive`
only when the lower bound exceeds zero and `negative` only when the upper bound is below zero.
The seed pair is the independent unit. The clip/seed bootstrap is computed but is not decision
bearing. This matches `plan/H1_FABLE_FREEZE_2026-09-07.md`.

## 2. Page budget: measured, not estimated

The open question was whether an H1 section plus a fourth full-width figure fits the eight-page
limit. It was answered by building, twice, in a scratch directory.

| Configuration | Pages | Overfull boxes | Unresolved refs | Page-8 text lines |
| --- | ---: | ---: | ---: | ---: |
| Current manuscript (no H1) | 7 | 0 | 0 | — |
| With the eleven repairs in §3, no H1 | 7 | 0 | 0 | — |
| With the H1 insertions `integrate_h1.py` will make | 8 | 0 | 0 | 64 |
| **Shipping configuration: integrate H1, then apply every repair** | **8** | **0** | **0** | **124** |

The last row is the real sequence, not an approximation of it: `integrate_h1.py`'s edits were
applied first (it rewrites the title, abstract, contributions, one conclusion sentence and one
limitations sentence, and inserts two subsections and a figure), and `apply_audit_fixes.py --h1`
was run on the result. All thirteen edits land, the pre-integration abstract variant correctly
skips itself, and the document compiles clean.

Page 8 holds references only. A full page carries 117–129 lines of text, so **the shipping
configuration sits exactly on the eight-page boundary with no usable headroom left.** Nothing
further can be added without cutting something. One cut is prepared and measured: converting
Table IV (earlier controls: E-HYG, soft weighting, E4, repair-all) into a five-line prose
sentence keeps every number and every status label and returns page 8 from 124 lines to 119, so
it buys roughly five lines of reserve. **This table measures the eleven-repair configuration.**
After the eight further repairs in §3b the paper is still 8 pages, but page 8 now carries 47
lines rather than 5, so an H1 section would need roughly 45 lines of cuts to fit. The
`inconclusive` disposition was used throughout because its inserted
sentence is the longest of the three branches; the other two branches are shorter and therefore
safe. An independent synthetic layout check run earlier the same day
(`reports/h1_manuscript_preparation_2026-09-07/synthetic_layout/result.json`) also returns 8
pages, by a different route.

`build.sh` fails the build on more than eight pages, and `complete_h1_handoff.py` restores the
original manuscript when the build fails, so an overflow degrades to "no H1 in the paper" rather
than to a broken submission.

## 3. Defects found, with repairs

Eleven repairs are staged in `apply_audit_fixes.py`, a fail-closed script that refuses to write
unless every target string matches exactly once. **All eleven are now applied to the repository**
(see §3a); eight further repairs from the adversarial audit followed in §3b.

Three are disagreements between the manuscript and the code it describes. These are corrections,
not omissions.

1. **`infeasible_frac` silently scores the screen's most severe frames as supported.** In
   `refeas/refeas/screen.py:217` a frame whose torque-limited program is infeasible *while in
   contact* yields `None`, becomes NaN, and is replaced by `0.0` before the `> 0.5·W` test. Such
   frames therefore count as fully supported. The repository's own reducer records this as a
   defect (`tools/screen_segments.py:25-28`). Verified from `feasibility.csv`: 734 clips have
   `torque_infeasible_frac > 0`, and a union rule flags 2,502/10,705 (23.37%) rather than 2,442
   (22.81%). The reported rate is the conservative one, but the convention was unstated, so a
   reimplementer coding the paper's sentence gets a different flagged set. Repair states the
   convention and gives the union count.
2. **The primary endpoint is misnamed.** The manuscript defines MPKPE as "root-relative
   body-position error". `tools/eval_paired_v2.py:644-652` subtracts
   `cmd.motion_anchor_body_index`, and the G1 configuration sets
   `anchor_body_name = "torso_link"` while `pelvis` is a separate entry in a 14-body tracked list.
   The score is therefore a torso-anchor-relative mean over 14 tracked bodies. Nothing in Table II
   or the abstract is reproducible from the stated definition. Repair renames it.
3. **The transfer control is weaker than described.** "200 random three-feature additions" is
   implemented in `tools/analyze_atlas_v21.py:47` as
   `np.c_[Xi, rng.standard_normal((n, 3))]` — three i.i.d. Gaussian noise columns, not three other
   real reference features. The test shows the feasibility features beat noise, which is a
   materially weaker claim. Repair describes the control as implemented and says what it does and
   does not establish.

Four are promises the design section makes that the results section never keeps, plus one omission
that makes a reported contrast easy to misread.

4. **Arm A's exposure is never reported for the completed campaign.** The manuscript gives R and D
   exposure but not A, while reporting an R−A contrast of −0.00668. From the campaign's own
   `analysis.json`, A's mean post-warm-up total variation is 0.029759/0.029339/0.029822 — below the
   0.05 separation level, in every seed. A is close to a second uniform arm, and R−A should be read
   that way. Repair states A's three values.
5. E2's design promises "contamination in the historical evaluator"; no contamination number
   appears in the results. Repair removes the promise.
6. E3's design promises "root, joint, body, velocity, and acceleration deviations" as secondary
   diagnostics; only CPU runtime is reported. Repair narrows the promise to runtime.
7. **The E1 campaign ran three arms and the manuscript reports two.** This is the most consequential
   finding in the pass. Sec. IV-A announces "failure-adaptive, clip-uniform, and normalized
   grounded samplers" and promises held-out survival; Sec. V-A reports only uniform minus adaptive.
   From `reports/A5_coverage_dose.json` and `reports/campaign_summary_3arm.json`, verified
   per-seed:

   | Arm | Final survival (seeds 1/2/3) | Peak top-1 mass |
   | --- | --- | --- |
   | adaptive | 0.78375 / 0.78500 / 0.77250 | 0.884 / 0.870 / 0.893 |
   | uniform | 0.81375 / 0.81250 / 0.80250 | 0.01 by construction |
   | grounded | 0.82250 / 0.83625 / 0.81500 | 0.568 / 0.649 / 0.696 |

   The grounded arm exceeds uniform in all three paired seeds (+0.0088/+0.0238/+0.0125, mean
   +0.015); the campaign summary independently records `uniform_vs_grounded` mean delta −0.015 with
   zero wins for uniform. Omitting it is selective reporting of an arm the design announced, and it
   omits the evidence that most directly supports the manuscript's own non-floor qualification:
   a sampler holding exactly 10% of mass on the uniform prior did not collapse and did not lose.
   Repair reports the arm in Sec. V-A and states that three seeds make the ordering descriptive.
   An earlier, weaker repair that instead narrowed the design promise was dropped in favor of this.
8. **An internal note would ship inside the submitted PDF.** The acknowledgments end with "with
   final author review required before submission", which tells a reviewer the authors have not
   completed their review. Repair removes the clause and keeps the provenance statement.

Two are configuration facts a reimplementer needs and cannot recover from the text.

9. **Arms A and D are contrasted but never given a form, and the concentration caps are never
   printed.** From the frozen `confirmation_freeze/profiles.json`: all arms share a 10-tick
   progress window and per-unit/per-clip ceilings of 0.05 and 0.25; A ranks absolute progress with
   a fixed 0.05 floor at exploration 0.4; D ranks conditional failure at exploration 0.8 with
   difficulty power 1. Worth recording separately: the paper's Eq. (2) is *correct* and is the
   composition of `relative_factor` 2 with exploration ratio 0.4, since
   `0.4b + 0.6[(2/3)b + (1/3)bg/µ] = 0.8b + 0.2bg/µ`. Repair prints the constants.
10. **"25 feasible-hard clips selected from reference features" is not an applicable rule.** The
    implemented rule (`tools/build_g_eval_strata.py:19-30,82-107`) restricts to clips of at least
    250 frames with `infeasible_frac` and `airborne_frac` both at most 0.10, ranks by the mean
    percentile rank of seven reference quantities with mean support margin negated, and takes the
    top 25. Repair states it, and states that no policy outcome enters it.

One further repair applies only after H1 is integrated.

11. **H1 confounds admission with support composition.** Both arms consume the same 49,152,000
   transitions, but gate-off draws from 11.5378% more legal-start mass (417,072 versus 368,951,
   verified above). If the arms separate, the paper cannot attribute the difference to
   physics-informed selection rather than to a narrower support. The discriminating control is a
   reference-blind exclusion arm matched on removed start mass; it is named in
   `plan/USEFUL_PRACTICE_NEXT_STEPS_2026-09-06.md` but is outside the frozen two-arm design and is
   not disclosed in the inserted manuscript text. Repair discloses it and names the control.

## 3a. Outcome: the repairs are applied; H1 stopped pre-endpoint

Both open items closed on the same morning, in opposite directions.

**H1 stopped.** At 09:45 EDT the campaign completed all ten training runs and then failed on its
first evaluation cell, because the sealed evaluation path omits the condition-manifest adapter the
completed confirmation used. The failure is provably before any checkpoint load or CSV write, so
no held-out endpoint was observed, and every scientific setting is verified correct. Continuation
in place is blocked by design. Full diagnosis, the three options and the recommendation are in
`plan/H1_EVALUATION_FAILURE_2026-09-07.md`. **No H1 number exists.**

**The repairs are applied.** Because the handoff terminated, `root.tex` unlocked, and all twelve
repairs were written and the paper rebuilt. `paper/icra/build.sh` passes: 8 pages, US Letter,
every font embedded, zero Type 3, zero overfull boxes, no undefined citation or reference, 24
citations exported. The four remaining `undefined` strings in the log are `TU/ptm` font-shape
warnings, which are pre-existing and are not what the build gate tests. Page 8 carries 5 lines,
so the H1 section still fits inside eight pages exactly as measured in §2.


## 3b. Second repair pass: the adversarial audit's must-fix list

A ten-dimension adversarial audit ran in parallel with this pass: 10 independent auditors, 72
findings, 40 verified by two diverse lenses each, 32 surviving refutation, one synthesis. Its full
prioritized plan is `audit_repair_plan.md` beside this file. It independently re-derived the
manuscript state and correctly identified that nine of the repairs in §3 were already applied.

Eight further repairs were applied and are staged in `apply_mustfix.py`. Every number was
recomputed from its artifact before being written.

1. **The attractor's survival sentence was contradicted by its own artifact.** "Every trained
   policy has zero survival from frame zero" holds only under a 10-second whole-clip horizon
   (survival 0.0, mean survival 2.376 s). Under the three-second stratified protocol the same
   reference survives from frame zero in 0.25 to 1.00 of episodes across seven policies, and the
   8-second start that the sentence contrasts it against completes a 1.96-second remainder. The
   sentence compared two protocols without naming either, and it erred toward the thesis. Note for
   the record: the audit named the right values but the wrong clip. The E1 attractor is
   `BMLmovi_Subject_64_F_MoSh_Subject_64_F_9` (499 frames at 50 fps), not the KIT kneel-to-crawl
   clip; the numbers were re-derived against the correct one before use.
2. **The 0.05 exposure gate sits below a learning-free floor.** A synthetic reference for the
   sampler's functional form at 1,184 units gives mean total variation 0.0605 over 2,000
   replicates and exceeds 0.05 in every replicate. Passing that gate therefore shows allocation
   moved, not that it tracked learning progress. The artifact was copied into this directory so
   the number has a repository path, and its own instruction not to subtract it from observed
   values is carried into the manuscript prose.
3. **The DFRP deployment row pooled repaired clips with no-op controls.** Separated: 22 qualified
   repairs give −0.0015 [−0.0105,+0.0090]; the 4 byte-identical controls give +0.0020
   [−0.0025,+0.0085], which bounds evaluator reproducibility at twice the headline magnitude.
4. **The screen-cost pair was internally inconsistent by 2.1×.** The bank has 367.36 frames per
   clip, so 0.145 CPU-s per clip is 0.395 ms per frame, not the 0.84 printed beside it. Replaced
   with the sourced pair from the completion sentinel: 0.29 CPU-s per clip, 0.79 ms per frame.
5. **Threshold-sensitivity scope** narrowed to the two clips and one clip actually swept, and the
   3 cm ground-alignment offset attributed to the measured clip rather than to the bank.
6. **An unsourced number removed.** The 5.6 rad/s peak joint speed had no artifact path.
7. **The failure criterion and the −10 terminal cost are stated for the first time.** Both underlie
   the allocator's signal, D's ranking and the evaluator's liveness weight, and the terminal cost
   is a departure from stock rewards that the text had called common across arms.

After both passes the paper builds to 8 pages with zero overfull boxes and no undefined citation
or reference. Page 8 carries 47 lines against a 117–129 full-page range. **An H1 section would no
longer fit without cuts**: it needs roughly 119 lines on page 8 and about 75 remain, so roughly 45
lines would have to come out, of which the prepared Table IV cut supplies 5.

## 4. Operational state as it was while H1 was running

`paper/icra/root.tex`, `build.sh` and `references.bib` are **locked**. The armed handoff
(`reports/h1_manuscript_preparation_2026-09-07/manuscript_handoff_r2/design.json`) records their
SHA-256 digests and aborts with "file changed while waiting" if any of them differs when H1
completes. All three digests were confirmed to match at the time of writing, so the automated
integration will proceed. Editing them now would break it.

The chain is armed end to end and was verified process by process:

| Stage | Process | Behavior on failure |
| --- | --- | --- |
| 52-job campaign | `paper/h1/campaign.py`, PID 3010547 | one attempt per job; no silent retry or restart |
| result replay and export | `paper/icra/follow_h1.py`, PID 3357512 | refuses a non-complete campaign; writes a status file |
| integrate, build, package, ledger | `paper/icra/complete_h1_handoff.py`, PID 3377266 | restores the original manuscript and rebuilds if the eight-page/font/layout build fails |

`report_h1.py` re-derives the whole frozen analysis and requires it to reproduce exactly, checks
every job sentinel, and refuses to proceed unless every training job completed before the first
evaluation started. `integrate_h1.py` refuses to run twice and refuses to write a mechanism share
that is undefined. `complete_h1_handoff.py` prepends the H1 entry to `paper/RESULTS_LOG.md` and
`plan/STATUS.md`, which keeps the house rule that every paper-bound number has a ledger path.

At 07:45 EDT the campaign had completed both GPU smokes and eight of ten training runs, all with
`gate_training_pass`, and `train_on_s1045` was 36 minutes in with a 13-minute estimate remaining.
Mean completed training wall time is 28.2 minutes. Iteration time has risen from about 0.45 s to
0.77 s because unrelated jobs share the GPU, so the remaining schedule is slower than the early
runs but far inside the 11 September training cutoff.

**No endpoint telemetry was read.** The mechanism and tracking endpoints were left unopened even
though four gate-off training runs are already complete, because nothing in this pass depends on
them and reading them early would weaken the seal's meaning.

## 5. What this pass did not establish

This is a document and artifact audit. It does not revisit the science of the completed allocation
comparison, does not re-derive the screen's physics, and does not evaluate whether the paper will
be accepted. The nine repairs are wording and disclosure changes; none changes a measured value.
A separate ten-dimension adversarial audit was run in parallel and its surviving findings are
recorded with this one. Items it raised that are not listed above were either refuted on
inspection or are presentation-level and deferred.

Reproduce the staged repairs and the page-budget result with:

```bash
mjlab-1.6.0/.venv/bin/python reports/fable_independent_verification_2026-09-07/apply_audit_fixes.py --check
```
