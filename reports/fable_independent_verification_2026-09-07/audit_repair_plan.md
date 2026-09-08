# ICRA 2027 Repair Plan — `paper/icra/root.tex` @ md5 `b37eb93c2d56410b6555204ed599c452` (mtime 2026-09-07 09:49, 592 lines, 7 pp.)

**Read this first — the manuscript moved after the audits ran.** I re-verified every surviving finding against the *current* source. Nine of them are already repaired in the live file and must **not** be re-edited:

| Finding | Current state (verified) |
|---|---|
| `grounded-arm-omitted-from-e1-results` / `e1-grounded-arm-has-no-result` | Fixed. §5.1 lines 366-374 now report grounded top-1 0.568/0.649/0.696 and survival +0.0088/+0.0238/+0.0125; abstract line 34 now reads "higher held-out survival **than that sampler**". |
| `infeasible-frac-scores-lp-infeasible-frames-as-supported` | Fixed. Lines 186-191 state the NaN→0 convention, "nonzero for 734 clips", and the union count 2,502 (23.4%). |
| `mpkpe-is-torso-anchor-relative-not-root-relative` | Fixed. Lines 344-346: "mean position error of the 14 tracked bodies expressed relative to the `torso_link` anchor". |
| `random-three-feature-control-is-gaussian-noise` | Fixed. Lines 291-293 and 406-409 say "three i.i.d. standard-normal columns" and explicitly disclaim the real-feature comparison. |
| `absolute-progress-arm-undefined` / `allocators-a-and-d-have-no-stated-form` | Fixed. Lines 242-245 give A (floor 0.05, exploration 0.4) and D (exploration 0.8, difficulty power 1). |
| `arm-a-exposure-tv-undisclosed` | Fixed. Line 462-463 now reports A at 0.02976/0.02934/0.02982 and calls it a weak-separation comparator. |
| `e2-contamination-promised-*` | Promise deleted from §4.2 (line 288 now ends at "category/source breakdowns"), so no design/results gap remains. Adding the 29/100 number is now optional (see S6). |
| `e3-secondary-diagnostics-promised-never-reported` | Design narrowed to "Per-clip CPU runtime is a secondary diagnostic" (line 309). Gap closed; the fidelity numbers are now an optional add (S7). |
| `feasible-hard-25-clip-panel-rule-missing` | Substantially fixed (lines 325-329 name all seven quantities, the sign on support margin, and top-25). Residual: eligibility filter and ranking population (S5). |

Everything below is what is **still open in the live file**, ordered by what it changes in a reviewer's conclusion.

---

## 1. MUST FIX before submission

### M1. §5.1 frame-zero survival contradicts the artifact and mixes two protocols
**File/lines:** `paper/icra/root.tex:380-381`
**Current text:**
```
8.0--8.5\,s rise again becomes unsupported. Every trained policy has zero survival from frame
zero, while the tested late 8\,s offset survives.
```
**Replacement:**
```
8.0--8.5\,s rise again becomes unsupported. Under a fixed frame-zero start with a 10\,s horizon,
no trained policy survives the reference (survival 0.00, mean survival 2.38\,s). Under stratified
3\,s windows, every start inside the 1--6\,s ground segment gives zero survival, an 8\,s start
completes the clip's remaining 1.96\,s, and a frame-zero 3\,s window survives in 0.25--1.00 of
episodes across the seven evaluated policies.
```
**Verification:** `reports/eval_tier_mixed100_fixed.csv` line 46 → `0.0, 2.376, 16, horizon 10.0`. `reports/N3_*_strat.csv` at offset 0.0 → 0.25 / 0.5 / 0.25 / 0.75 / 1.0 / 0.5 / 0.75; offsets 1–6 s → 0.0; offset 8.0 → 1.0 at `window_s 1.96`.
**Why first:** this is the only sentence in the paper that a reviewer can falsify by opening one CSV, and it errs toward the thesis. It also silently compares a 10 s whole-clip criterion with a 1.96 s tail. Both audited findings collapse into this one edit.

### M2. §5.4 exposure TV is reported without the measured learning-free floor
**File/lines:** `paper/icra/root.tex:463` (insert after "…second strong intervention.")
**Insert:**
```
A learning-free synthetic reference for this functional form---1,184 units, equal prior mass,
inactive caps, and independent Gaussian progress changes---yields mean total variation 0.0605
over 2,000 replicates and exceeds 0.05 in every replicate. Exposure change above the gate
therefore records that allocation moved, not that it tracked learning progress; the synthetic
reference is an illustration and is not subtracted from the observed values.
```
**Verification:** `/home/linjiw/climb-signal-quality-2026-09-06/reports/research_next_2026-09-06/noise_only_tv.json` → `analytical_large_unit_tv 0.06049`, `finite_unit_mean_tv 0.06040`, `fraction_above_005 1.0`; ledger row `paper/RESULTS_LOG.md:440`.
**Attached chore (house rule):** that artifact lives outside this repo. Copy `noise_only_tv.json` + its generator into `reports/` and repoint the RESULTS_LOG:440 artifact path before the number is paper-bound. The wording above deliberately preserves the artifact's own caveat ("Never subtract from actual R TV").
**Why:** the 0.05 gate is the only thing separating A's `not_tested` from R's "live intervention"; the team has measured that the gate sits below the no-learning floor and the paper does not say so.

### M3. Table I deployment row: undisclosed denominator and no-op floor
**File/lines:** `paper/icra/root.tex:446-447`
**Current text:**
```
Deployment / exploratory & One policy, 26 clips, 656 paired conditions per arm: raw 0.3925,
repaired 0.3915; difference $-0.0010$, clip-bootstrap 95\% CI $[-0.0086,+0.0080]$. \\
```
**Replacement:**
```
Deployment / exploratory & One policy, 26 clips (22 repaired plus 4 byte-identical controls),
656 paired conditions per arm: raw 0.3925, repaired 0.3915; difference $-0.0010$,
clip-bootstrap 95\% CI $[-0.0086,+0.0080]$. Repaired-only stratum (22 clips, 568 conditions):
$-0.0015$, $[-0.0105,+0.0090]$. The byte-identical control stratum returns $+0.0020$,
$[-0.0025,+0.0085]$, bounding evaluator reproducibility. \\
```
**Verification (recomputed from `reports/dfrp_policy_validation_2026-09-05/result.json`):** `all` 26 clips / 656 cond / −0.00100271 [−0.00858776,+0.00802024]; `qualified_repairs` 22 / 568 / −0.00154221 [−0.01053489,+0.00904977]; `unchanged_controls` 4 / 88 / +0.00196451 [−0.00250097,+0.00854311].
**Why:** a four-decimal near-null is quoted on a set where 13% of conditions had nothing repaired, and the pipeline's own no-op floor is twice the headline magnitude.

### M4. Threshold-sensitivity scope overreach (two edits)
**(a) File/lines:** `paper/icra/root.tex:546-548`
**Current:**
```
Finite differences, the 6\,cm contact band, and the half-weight residual threshold introduce
modeling choices. Local sensitivity checks bound the two thresholds on this bank, but a new robot
or retargeter must recalibrate them.
```
**Replacement:**
```
Finite differences, the 6\,cm contact band, and the half-weight residual threshold introduce
modeling choices. The sensitivity evidence is local: two clips at three contact bands and one
clip at three residual thresholds (\texttt{reports/N1\_gap\_sensitivity.json}). Bank-scale
sensitivity of either threshold is untested, and a new robot or retargeter must recalibrate them.
```
**(b) File/lines:** `paper/icra/root.tex:163-164`
**Current:**
```
The 6\,cm band is a declared tolerance. At 3\,cm a known feasible control is flagged on 42\% of
frames because the bank carries an approximately 3\,cm ground-alignment offset.
```
**Replacement:**
```
The 6\,cm band is a declared tolerance. At 3\,cm a known feasible control is flagged on 42\% of
its frames because that clip's stance frames sit approximately 3\,cm above the plane, a residual
we attribute to retarget ground alignment but have not measured bank-wide.
```
**Verification:** `reports/N1_gap_sensitivity.json` holds six rows (2 clips × gaps 0.03/0.06/0.10) plus one `bound_sensitivity_clip44` triple; no bank-wide sweep of either threshold exists in `reports/`.
**Why:** these two thresholds produce the headline 22.8% / 0.14% prevalence, and the project's own house rule forbids exactly this corpus-scope generalization. See **E1** below — the bank-wide version is a cheap CPU experiment if you'd rather strengthen than narrow.

### M5. §3.2 screen cost is internally inconsistent by 2.1×
**File/lines:** `paper/icra/root.tex:197-200`
**Current:**
```
The screen takes approximately one CPU-second per clip in the primary implementation. An
independent implementation processes the production bank at 0.145 CPU-s per clip
(0.84\,ms/frame). The screen therefore runs as an offline bank-ingestion stage rather than in the
policy control loop.
```
**Replacement:**
```
A second implementation screens the 4,950-clip production bank in 179.8\,s wall on eight workers:
0.29 CPU-s per clip over 1,818,423 screened frames, or 0.79\,ms per frame. The screen therefore
runs as an offline bank-ingestion stage rather than in the policy control loop.
```
**Verification (recomputed):** `reports/feasibility_sonic/hygiene_screen.csv` → 4,950 clips, 1,818,423 frames, 367.36 frames/clip. `0.145/367.36 = 0.395 ms/frame`, **not** 0.84. `COMPLETED.json` → `wall_clock_s 179.838`, `workers 8` → 0.291 CPU-s/clip = 0.791 ms/frame.
**Note:** I dropped the "approximately one CPU-second per clip in the primary implementation" clause because no artifact for it exists in `RESULTS_LOG.md` (only flagship prose). If you want it back, add a ledger row first; otherwise the sentence above is fully sourced. If you keep 0.145, you must say which frame count it was measured over — it is not this bank's.
**Why:** a reviewer divides 0.145 by 367 and the sentence contradicts itself, and it quotes the faster of two known costs for the number that supports the "offline stage" argument.

### M6. §5.1 peak joint speed 5.6 rad/s has no artifact
**File/line:** `paper/icra/root.tex:376`
**Current:** `The reference has no joint-limit violation and peak joint speed is at most 5.6\,rad/s. The`
**Replacement (edit-only path):** `The reference has no joint-limit violation against the model's declared ranges. The`
**Preferred path:** keep 5.6 and add a `RESULTS_LOG.md` row binding both values to a regenerable artifact — a ~20-line CPU script over the reference qpos/qvel against mjlab's G1 ranges, written to `reports/`. Minutes, no GPU. Its only current source is prose at `plan/G1_RESULT.md:72`; `grep 5.6` in `RESULTS_LOG.md` returns nothing.
**Why:** house rule — every paper-bound number needs an artifact path, and this sentence is what establishes that kinematic QC could not have caught the attractor.

### M7. Failure/termination criterion and the −10 terminal cost are never stated
**File/lines:** `paper/icra/root.tex:250` (append to the §III-D runtime paragraph, before line 252)
**Insert:**
```
A trial fails when a non-timeout termination fires: anchor height error above 0.25\,m, anchor
gravity-projection error above 0.8, or height error above 0.25\,m at either ankle or wrist.
Truncation at a segment boundary is not a failure. All arms add a one-off terminal cost of $-10$
on failure to the inherited mjlab tracking rewards.
```
**Verification:** `mjlab-1.6.0/src/mjlab/tasks/tracking/tracking_env_cfg.py:259-275` (thresholds 0.25 / 0.8 / 0.25); `climb/segment_env_cfg.py:37,78-85` (`failure_number = -10.0`, entered as `weight = failure_penalty/step_dt` on `mdp.is_terminated`, upstream `time_out` term removed).
**Why:** the allocator's adaptation signal (`conditional success`), D's ranking (`conditional failure`), and the evaluator's $h$ all rest on a criterion the paper never defines — and the reward differs from stock mjlab in an undisclosed way while line 311 asserts "rewards … are common".

### M8. H1 reporting guards — write these into the addendum *before* `integrate_h1.py` runs
**Files:** new dated addendum under `/home/linjiw/climb-gate-ablation-2026-09-06/reports/h1_fable_2026-09-07/` (never edit the sealed `contract.json` or `H1_FREEZE.sha256`), plus the `result_text` block in `report_h1.py`/`integrate_h1.py`.

**(a) Two of three manipulation checks are design identities.** Add:
```
Two of the three allocation manipulation checks are structural invariants re-verified at every
checkpoint, not empirical outcomes: the off-arm minimum rejected mass 0.0923 is the exploration
floor 0.8 x 0.1153782 by construction, and the on-arm zero-rejected condition is enforced by the
admitted-unit manifest itself. The empirical quantities are the off arm's 175,223 rejected
completed trials at iteration 3999 and the rise of post-cap rejected mass from the 0.1154 prior
to 0.1751.
```
Verified: `climb/gate_ablation.py:44` (`exploration_ratio=0.8`), `climb/segment_curriculum.py:180,263-266` (floor), `gate_off.json` 48,121/417,072 = 0.1153782, `tools/gate_training_provenance.py:91`.

**(b) The SESOI was dropped after the sister result; state the power.** Add:
```
The archived draft contract specified a +0.02 benefit target and a -0.01 non-regression margin;
both were removed before sealing on power grounds. At the completed confirmation's hard-panel
seed sd 0.03192 and df=4, the expected two-sided 95\% half-width is approximately 0.040, so H1 is
powered for effects of roughly that size; +0.02 is a reported reference line, not a decision rule.
```
Verified: `reports/gate_entrypoint_2026-09-06/preparation/draft_contract.json` (benefit_target 0.02, nonregression_margin −0.01, mtime 2026-09-06 01:57) vs sealed contract (both `null`, frozen 2026-09-07T05:11:17Z); `fable.md:247`; `protocol.py:175` still emits `reference_effect: .02`.
**Why:** without (a), "all manipulation checks passed" is offered as verification of a contrast that two checks cannot fail to certify; without (b), a relaxation of the pass/fail threshold made after the sister experiment's variance was known is invisible in the sealed record.

### M9. The public site defeats the anonymity gate
**Files:** `docs/index.html:98`, `docs/archive-2026-09-05.html:480-482`, `paper/icra/BUILD_AUDIT_2026-09-07.md:17`
**Current (`docs/index.html:98`):**
```html
<footer><div class="wrap"><p>CLIMB · Research toward an ICRA submission · <a href="https://github.com/linjiw/climb-feasibility-first">Code and experiment ledger</a></p></div></footer>
```
**Action, in order:** (1) confirm ICRA 2027's blinding policy from the official call and record the decision in `plan/STATUS.md`. (2) If blinding is required: replace the footer with `<footer><div class="wrap"><p>CLIMB · Code and experiment ledger</p></div></footer>` (drop the handle link and the "Research toward an ICRA submission" phrase), and delete the three `paper/icra/{OUTLINE.md,DRAFT.md,ICRA_DRAFT.pdf}` links at `docs/archive-2026-09-05.html:480-482`. (3) Rewrite the `BUILD_AUDIT_2026-09-07.md:17` anonymity row to say the screen covers PDF-internal text only. (4) If blinding is *not* required, drop `\author{Anonymous Authors}` (root.tex:22) and retire the anonymity gate rather than shipping a half-blind package.
**Verification:** the PDF itself is clean (all streams decompressed, zero hits for `linjiw`, `/home/`, `github`, `.io`); the exposure is entirely external, and `plan/STATUS.md:694-696` confirms the Pages site is live and deliberate. No repo file discusses this risk.
**Why:** a search for "CLIMB" or "reference-physics misalignment" reaches a page naming the author's handle and serving the submission PDF. This is the only finding on the list with desk-reject potential, and it is a docs edit, not a science edit.

---

## 2. SHOULD FIX if time permits

Ordered by reviewer impact per line spent. All are one- or two-line edits.

**S1. §5.3 — three different sets are all called "26".** `root.tex:431-432`
Current: `The resulting 26-clip curated view contains 36 admissible units and 10,561 legal 50-step starts. Median and 95th-percentile CPU runtime are 2.57 and 6.29\,s per clip.`
Replace with:
```
The resulting curated view (the 22 qualified repairs plus the 4 controls) contains 36 admissible
units and 10,561 legal 50-step starts. Across all 30 panel clips, median and 95th-percentile CPU
runtime are 2.57 and 6.29\,s per clip.
```
Recomputed from `dfrp_v1_exact_panel/iter1/result.json`: p50/p95 over 30 clips = 2.5678/6.2911 (matches the paper); over the 26 candidates alone = 2.6263/**7.1249**. The quoted p95 is 13% low because the four no-ops are pooled in.

**S2. Table III — E-HYG's resampling unit is clips, not seeds.** `root.tex:524-525`
Replace `$\Delta=-0.0101$, one-sided permutation $p=0.951$.` with `$\Delta=-0.0101$; one seed pair, permutation over 71 feasible held-out clips, $p=0.951$.`
Only `E_HYG_*-s1_*` artifacts exist; `p=0.951` is unattainable from a 3-seed sign-flip (granularity 1/8), and the paper declares elsewhere (line 347) that the independent unit is the seed pair.

**S3. Table III — three of four rows are uninterpretable, and one collides with Table I.** `root.tex:524-528`
Add a half-clause gloss to each left cell (what the study did), and after line 442 add: `The Repair-all row in Table~\ref{tab:controls} is an earlier training contrast under whole-bank repair; Table~\ref{tab:repair} is a fixed-policy raw-versus-repaired-target comparison. They are different studies.` As typeset, `+0.0397` (line 528) and `−0.0010` (line 447) sit on one page with opposite signs and no distinguishing text.

**S4. §III-D — sampler constants and clock.** After `root.tex:245` add:
```
The sampler clock advances every 50 environment steps, so the 10-tick window spans 500 steps;
conditional rates use a Beta(0.5,2) prior with per-tick decay 0.99; Eq.~\eqref{eq:gate} is the
general rule at exploration ratio 0.4 and relative factor 2.
```
Verified in `climb/segment_command.py:288-296,430-436` and re-derived from `climb/relative_progress.py` + `confirmation_freeze/profiles.json`.

**S5. §IV-D — averaging domain and cell composition.** After `root.tex:330` add:
```
The two error terms are means over the survived prefix of each episode; the window is 3.0\,s at
50\,Hz control, and a cell's 2,800 conditions are 100 clips $\times$ 7 phase starts $\times$ 4
replicates. Panel clips are ranked over the eligible population (at least 250 frames,
\texttt{infeasible\_frac} at most 0.10, \texttt{airborne\_frac} at most 0.10), not over the panel.
```
Verified: `eval_paired_v2.py:605-613,905`, `analyze_relative_policy.py:51-63`, `build_g_eval_strata.py:19-30,82-107`. This closes the last reproducibility gap on the headline endpoint.

**S6. §5.2 — one sentence of contamination context.** Add after line 401: `Twenty-nine of the 100 historical-evaluator clips are themselves flagged under the strict rule (\texttt{reports/feasibility\_e3/feasibility.csv}).` Ledger row `RESULTS_LOG.md:484`. Now optional (the promise was deleted from §4.2) but it is the reason the E-HYG study exists and it strengthens the transfer result rather than weakening it.

**S7. §5.3 — the repair-fidelity numbers the paper gestures at but never gives.** Add after line 434: `Admitted clips show zero manifest-integrity, joint-limit, and IK-residual violations; root displacement is 0.0509\,m median and 0.0756\,m at p95 against the 8\,cm ceiling, and body MPJPE p95 is 0.0725\,m.` From `dfrp_v1_exact_panel/iter1/result.json`. This quantifies the "repair changes the tracking target" caveat made verbally at line 204.

**S8. §IV-D — the stochastic environment is unstated.** One sentence naming the inherited observation noise (anchor pos ±0.25, anchor ori ±0.05, base lin/ang vel ±0.5/±0.2, joint pos/vel ±0.01/±0.5), the `push_robot`/`base_com`/`encoder_bias`/`foot_friction` events, and the evaluator's `--joint-noise 0.05` with seeds 20260820/20260821. Cite mjlab's G1 tracking config as the source so it costs two lines, not ten.

**S9. Reproducibility §  — make the release statement actionable.** `root.tex:583-584`. Name what ships and where (anonymized `refeas` repo, unit table, condition manifests, per-condition metric CSVs), state that the second implementation (`gear_sonic/research/hygiene/screen.py`) is a separate codebase not included, and pin the screen's MJCF by name and hash instead of `tools/n1_knee_id.py:37-41`'s newest-`/tmp/s1_*/g1_compiled.xml.mj.xml`-by-mtime glob.

**S10. Naming hygiene.** Give the fourth study a stable name ("E5: four-arm allocation on unchanged exact support" in both Design and Results headings) and rename `\label{sec:e4results}` (line 456) to match, since "E4" is reserved throughout for the abandoned protocol that Table III lists as `not tested`.

---

## 3. DO NOT FIX — correct as written; defenses to keep on hand

| Item a reviewer may challenge | One-sentence defense |
|---|---|
| Conservative `infeasible_frac` convention (LP-infeasible frames score 0) | The convention is now stated at lines 186-191 together with the union count 2,502 (23.4%), so the headline 2,442 is the explicitly conservative choice, not a hidden one. |
| Grounded arm beats uniform but we make no recommendation | Reported at lines 366-374 with the sign pattern and the explicit statement that at three seeds the ordering is descriptive and licenses no grounded-sampler recommendation. |
| Only three seed pairs; interval spans harm and benefit | Declared in Limitations (sd 0.03192, half-width 0.07929) as an observed precision limitation; the frozen decision was pre-registered and is reported as inconclusive rather than reinterpreted. |
| Prevalence 22.8% vs 0.14% never pooled | Different corpus-and-pipeline pairings with different filtering, robot file, friction, and implementation; Fig. 2's caption already says this is not a causal retargeter comparison. |
| E4 reported as `not_tested` rather than as a null | House rule: a failed manipulation check means the intervention was not delivered, so no policy endpoint was opened and no null exists to report. |
| H1 fixed at five seeds while `fable.md:248` mentions six | The seal fixes n=5 in three independent places; the sixth-seed sentence is an unexecuted contingency that the frozen analysis cannot consume. |
| H1 campaign is non-resumable / fail-closed | Deliberate and pre-registered: any gate failure invalidates the run rather than silently degrading it, which is the property that makes the sealed verdict trustworthy. |
| H1's 0.05/0.25 caps never bind (max realized unit mass ≈0.018) | The caps are declared identical across arms as a matched-configuration guarantee; the claim is that they do not differ, not that they are active. |
| `BUILD_AUDIT_2026-09-07.md` PDF hash looks stale | A dated addendum (`BUILD_AUDIT_2026-09-07_ADDENDUM.md`) already records the superseding hash, which is the prescribed correction mechanism for a non-editable audit. |
| Difficulty transfer "fails" on the two grounded-policy pairs | All six directed pairs move in the same direction; four reach p<0.05, and line 410 states the scope as within-architecture cross-policy transfer. |
| Exact-support segmentation "uses a different frame mask" | The 1.0 s minimum-run rule and the reducer's eligibility union are the same artifacts that produced the published unit table; the claimed divergence does not exist in the generating path. |

---

## 4. Findings that need an EXPERIMENT rather than an edit

Only two, and neither is on the critical path. **The GPU is not the constraint for either** — both are CPU-only, so they can run alongside the live H1 campaign without touching it.

**E1 — Bank-wide threshold sensitivity (converts M4 from narrowing to strengthening).** Re-run `refeas` over the 10,705-clip primary bank at contact bands 0.03/0.06/0.10 and at half-weight residual thresholds 0.25/0.50/0.75 W. Cost estimate from the durable receipt: 0.29 CPU-s/clip × 10,705 × 3 ≈ 9,300 CPU-s ≈ 20 min wall on 8 workers per sweep; both sweeps comfortably fit in an afternoon on CPU. **Verdict: feasible before the Sept 12 cutoff, GPU-independent.** If it runs, replace the M4(a) text with the measured bank-wide curve; if it slips, ship M4(a) as written — the narrowed sentence is correct either way, so this is opportunistic, not blocking.

**E2 — Random-*real*-feature control for the E2 transfer claim.** 200 designs drawing three real reference features instead of three Gaussian columns; ridge fits over 100 clips, seconds of CPU. **Feasible.** Optional only: lines 291-293 and 406-409 now describe the implemented control honestly and disclaim the real-feature comparison, so this would upgrade the claim rather than repair a defect.

**Not experiments, despite appearances:** M2 (the null is already computed — it needs copying into `reports/` and one sentence), M3 (the strata are already in `result.json`), M8(b) (arithmetic from the sister study's sd), S7 (already in `result.json`). M6's preferred path is a regeneration script, not an experiment — minutes on CPU.

**One thing to explicitly *not* do:** do not run a matched-horizon frame-zero re-evaluation to rescue M1's original sentence. It would need the GPU that H1 owns, and the corrected sentence is stronger than the original because it reports both protocols.

**Page budget.** The MUST edits add ~17 column-lines (≈165 column-pt); the full SHOULD list adds ~20 more. The current 7-page build leaves ~304 pt of tail slack, and the synthetic H1 insertion lands at 8 pages with ~690 pt still free on page 8. Everything here fits inside the 8-page limit with headroom, but re-run `build.sh` and re-check for overfull boxes after M7/S4/S5/S8, which are the paragraph-growing edits.

---

## 5. Residual risk

What remains unverified after this plan is executed. First, the H1 result itself is not yet in hand: the campaign is live, no H1 number appears in `root.tex`, and the sealed decision rule has one untested degenerate branch (sd = 0 across the five paired seeds). If H1 returns positive, its verdict rests on a criterion whose SESOI was removed after the sister study's variance was known — M8(b) discloses that, but disclosure is not power. Second, the calibration behind the headline prevalence stays local unless E1 runs: two clips bound the contact band and one clip bounds the half-weight residual, so the 22.8% and 0.14% rates are reproducible but their threshold sensitivity is not characterized at bank scale. Third, the "independent implementation" that supplies the 39/40 agreement and the screen-cost figure lives in a different workspace and is not in this repository; I verified its outputs but could not verify the code, and a reader cannot obtain it — S9 makes that explicit rather than fixing it. Fourth, `refeas/refeas/screen.py` is byte-equivalent to `tools/n1_knee_id.py` apart from path handling, so what the paper calls two implementations is one primary plus one genuinely separate codebase, and the primary resolves its robot model by a `/tmp` mtime glob that no artifact pins. Fifth, everything model-relative stays model-relative: no hardware validation, no terrain, no measured sim-to-real, and the physical-sensitivity check remains unresolved and unreported. Sixth, the anonymity exposure (M9) depends on a policy fact I did not verify — nobody in the repo has read ICRA 2027's blinding requirement, and the correct action flips entirely on it. Finally, `root.tex` was under active edit while every audit in this cycle ran (three distinct hashes today); all line numbers and quoted text above are pinned to md5 `b37eb93c2d56410b6555204ed599c452` and must be re-matched before applying if the file moves again.