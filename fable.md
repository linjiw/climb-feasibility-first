# fable.md — Research guidance for CLIMB / feasibility-first (2026-09-07, rev 4)

**Author:** Claude Fable 5.1, from a full read of `plan/STATUS.md`, `paper/RESULTS_LOG.md`,
`paper/RED_TEAM.md`, `paper/icra/DRAFT.md` + `REVIEW_2026-09-04.md` + `BUILD_AUDIT_2026-09-04.md`,
`reports/relative_confirmation_results_2026-09-06/README.md`, and the September 5–6 plan
addenda (`USEFUL_PRACTICE_SUBMISSION`, `USEFUL_PRACTICE_NEXT_STEPS`, `ICRA_EVIDENCE_ROADMAP`,
`MATCHED_GATE_RUNTIME`, `H1_*`, `RELATIVE_PROGRESS_R1_RESULT`).
**Status:** unsealed guidance. Not a preregistration; authorizes nothing by itself.
**Supersedes** rev 3 (2026-08-27; kept in git history at `d77b226`). Everything rev 3 asked for
has since happened: Newton gate sealed and failed (G3 killed), Phase-G sealed and run, E4
`not_tested`, relative-ALP calibrated, four-arm three-seed confirmation completed. This revision
is written for one purpose: **a complete, honest, eight-page ICRA 2027 submission on
September 15, 2026 — eight days from now.**

---

## 0. One-paragraph verdict

The research programme has done its job: the sealed four-arm confirmation ran to completion
and returned **inconclusive** (final feasible-hard R−U = −0.015, 95 % seed-t CI
[−0.094, +0.064]; exploratory AULC negative in 3/3 seeds). The correct reading is not
"CLIMB failed" — it is that the paper's claim set must now be *chosen*, not *hoped for*. The
draft of Sept 4 still says E4 is "in progress" and frames three method contributions of which
two have no positive policy result. That framing will not survive review and must change this
week. The strong, fully-evidenced spine is the **measurement line**: reference–physics
misalignment (RPM) diagnosed in a sealed campaign, a bank-scale screen with cross-implementation
agreement, feasibility features that transfer difficulty across policies, an exact temporal
support interface, and a *controlled* result that on exact support, outcome-driven allocation
changes exposure but not held-out tracking at this budget. **One** experiment is worth the GPU
before the evidence cutoff: **H1, admission on/off under the same failure-driven allocator on
the contaminated bank**, because it is the only test of the word "feasibility-gated" in the
title and it fits in roughly one GPU-day. Everything else (continuous execution, physical
sensitivity, noise study, practice branches, video, hardware) is stopped until Sept 16.

---

## 1. Where the project stands on Sept 7

### 1.1 Settled evidence the paper can lean on

| claim | label | artifact |
|---|---|---|
| Failure-adaptive sampler concentrates (peak top-1 0.870–0.893) on a kneel/crawl clip whose 0.75–1.75 s descent demands ≈329 N unsupported vs 327 N robot weight; uniform beats adaptive +0.030/+0.0275/+0.030 in 3/3 paired seeds | sealed ✓ | `reports/A5_coverage_dose.json`, `A7_attractor.json`, `N1_clip44_knee_id.json` |
| ε/N is not a floor; normalise-then-mix is | sealed ✓, upstream-filed (mjlab #1153, wbt #73, still open) | `RED_TEAM` #3 |
| 2,442/10,705 (22.8 %) flagged in AMASS→wbt→G1; 7/4,950 (0.14 %) in BONES-SEED→G1; never pooled | measured | `reports/feasibility_all/`, `reports/feasibility_sonic/` |
| Same-clip 20+20 panel: ρ 0.984/0.997, 39/40 strict flags agree (κ 0.948) | measured | `reports/feasibility_xcheck/` |
| Feasibility features lift cross-policy difficulty transfer 0.567→0.609 (p = 0.010 vs 200 random triples) | sealed ✓ | `reports/N_atlas_v21.json` |
| Exact support over tier_800: 1,841 runs → 1,184 admissible units, 368,951 legal starts; hash-bound; paired evaluator with 100-clip name+hash-disjoint panel, 2,800 conditions | measured (apparatus) | `reports/g_segment/unit_table.json`, `eval_conditions.json` |
| DFRP v1 exact contract: 22/26 flagged qualify, 4/4 controls byte-identical | measured (implementation gate) | `reports/dfrp_v1_exact_panel/iter1/` |
| DFRP fixed-policy deployment: raw 0.3925 → repaired 0.3915, Δ −0.0010, clip-bootstrap CI [−0.0086, +0.0080], one policy, 26 clips | measured exploratory | `reports/dfrp_policy_validation_2026-09-05/result.json` |
| Newton no-training predictive gate FAIL (partial ρ 0.141, p 0.158); G3 killed | sealed ✗ (kept) | `plan/NEWTON_PRED_RESULT.md` |

### 1.2 What changed since rev 3 (the load-bearing new facts)

1. **E4 (absolute-floor ALP, seed 1): `not_tested`.** Mean post-warm-up TV 0.0297 < 0.05. Seeds
   2–3 stopped, endpoint never opened. This is the fourth arm in a row to fail its manipulation
   check (FGAS, segment-v2, E4, and the old adaptive "A" arm at TV 0.03 inside confirmation).
2. **Relative ALP (R) passes the manipulation gate** in every seed run (TV 0.082–0.083; effective
   units > 600; caps respected; zero invalid/censored). So did the conditional-failure allocator
   D (TV 0.082–0.086). **The allocation half of the thesis is now testable and was tested.**
3. **Confirmation (U/A/R/D × seeds 21–23, 512 env × 4,000 it = 49.2 M transitions per policy,
   48 held-out cells): inconclusive.** Per-seed R−U: −0.0340, −0.0330, +0.0218. All-panel guard
   fails (CI lower −0.114). R−D −0.0067 with CI [−0.022, +0.008] — R and D are
   indistinguishable and both slightly below uniform. Exploratory hard AULC R−U negative in
   every seed (mean −0.029). **No allocator beats uniform on exact support at this budget.**
4. **Repair does not move a fixed policy** (Δ −0.001 on 26 clips). Combined with N7, the honest
   sentence is: certified repair is *consumable without harm* on this panel; it is not a
   performance lever we have shown.
5. **H1 is nearly launch-ready.** Matched gate-on/gate-off runtime exists in
   `/home/linjiw/climb-gate-ablation-2026-09-06`; CPU PPO smokes pass from identical actor
   tensors; the candidate partition retains all 1,184 feasible units + 465 rejected intervals
   (368,951 of 417,072 legal starts admitted; 11.54 % excluded); the gate-off prior floor
   guarantees ≥ 0.0923 rejected-start probability; the provenance checker passes 19 tests.
   Missing: the freeze contract, seeds, the analysis decision rule, and the scheduler.
6. **The physics audit** found both knee clamps at ±139 N·m vs Unitree's public 90 (G1) /
   120 (G1 EDU) N·m; zero command delay; plane terrain. This is one limitation sentence, not
   an experiment.
7. **The GPU follow-up queue is in a failed state**: nine CUDA lifecycle cells completed but the
   aggregate original/unchanged CSV parity gate failed, cause unresolved. The physical-
   sensitivity study S1 therefore cannot be trusted to produce a paper number this week.

### 1.3 Calendar and machine

- **ICRA 2027 deadline: Sept 15, 2026** (checked against the official call on Sept 6). Eight pages
  including references. Video window closed Sept 9, reopens Sept 17–22.
- Internal gates already adopted: **Sept 10 claim selection, Sept 12 evidence cutoff,
  Sept 13–15 integration.** This document tightens the first to **Sept 8** (see §3) because the
  claim set no longer depends on any pending result except H1.
- Current draft: `paper/icra/ICRA_DRAFT.pdf` is **7 of 8 pages**, built Sept 4–5, with §5.4
  reading "E4's three-seed policy comparison is in progress". It has never been rebuilt with
  the completed result.
- GPU today: 16 GB card, 1.2 GB used, 1 % utilisation, one foreign eval process. A 512-env,
  4,000-iteration arm took **0.74 GPU-hours** (R1, shared). The 12-run + 48-cell confirmation
  finished in ≈ 14 wall-hours. **H1 at five paired seeds (10 runs + 40 cells) is ≈ 12–14 h.**
- Working tree: 8 modified + ≈ 50 untracked files (plans, reports, `climb/relative_progress.py`,
  two figure scripts, tests). Nothing sealed touched. **Not committed.** Four detached
  worktrees hold the H1, ICRA-evidence, signal-quality, and pages tooling.

---

## 2. Review of the Sept 4 draft (Xiao-rubric pass, read-only)

**Scope:** full `paper/icra/DRAFT.md` (mirrors `root.tex`), plus the claim ledger. Not an ICRA
verdict; an evidence audit.

**Charitable reconstruction.** Outcome-adaptive curricula misread reference defects as learnable
difficulty; CLIMB screens final robot-space references for contact/actuator admissibility, routes
intervals, and lets adaptive allocation act only on exact feasible support. Strongest supported
contribution: the RPM diagnosis + bank-scale screen + exact-support apparatus, backed by sealed
campaign telemetry and cross-implementation agreement.

### 2.1 Claim–evidence table for the abstract as written

| abstract claim | unit / n | comparator | warrant today | smallest repair |
|---|---|---|---|---|
| top-1 peaked 87–89 %, same kneel/crawl attractor recurs | seed; 3 | historical uniform/grounded | supported (peak owner differs in 2 seeds — already stated in §5.1) | none |
| refeas flags 2,442/10,705; 39/40 agreement | clip | one pipeline; enriched panel | supported, scoped | none |
| DFRP qualifies 22/26, 4/4 controls unchanged | clip in frozen panel | qualification gates | supported as *implementation*; abstract implies more | add "fixed-policy deployment unchanged (Δ −0.001)"; drop "restores" verbs |
| "exact-support curriculum … capped learning-progress allocation" as contribution 3 | — | — | **now contradicted as a benefit**: confirmation inconclusive, AULC negative 3/3 | rewrite as *interface + matched negative/inconclusive result* |
| transfer 0.567→0.609, p = 0.010 | clip; 100 | 200 random triples | supported | none |
| "closed-loop data-to-policy framework" | — | — | unclear: the loop has never improved a policy | replace with "a training interface that makes admission and allocation separately testable" |

### 2.2 Prioritised concerns

1. **Validity-critical — §5.4 and contribution 3.** The manuscript's E4 paragraph is stale; the
   completed result contradicts any benefit reading. Consequence: a reviewer who reads "in
   progress" beside an ALP contribution will assume the result was withheld. Repair: replace
   §5.4 with the completed four-arm table (per-seed deltas, both CIs, AULC as exploratory) and
   the existing figure `paired_results_and_learning_curves.pdf`; rewrite contribution 3 and the
   abstract; retitle (§3.3).
2. **Validity-critical — the title word "gated".** No experiment in the paper isolates the gate.
   E-HYG (whole-clip prune) is a null; exact-interval gating has never been contrasted with its
   absence. Repair: H1 (§4), or, if H1 does not land by the cutoff, a title and abstract that
   claim *screening + exact support*, not *gating benefit*.
3. **Major — DFRP page cost vs evidence.** §3.3 spends a full display program plus a two-stage
   description on a component whose only policy-facing number is Δ −0.001. Repair: compress to
   one paragraph and one table row; move the program to a released-code note. This also buys
   the space §5.4 needs.
4. **Major clarification — "closed loop".** Fig. 1 and the abstract call CLIMB closed-loop. The
   only loop actually run is allocation-from-outcomes, which did not help. Repair: describe the
   loop as *what the interface permits* and state that the tested loop gave no measurable gain.
5. **Presentation — pooled tiers.** §5.4's "Alternative routing and allocation controls" mixes
   sealed (E-HYG), failed-manipulation (FGAS) and exploratory (N7) numbers in one paragraph.
   Repair: a four-row table with a status column, one sentence each.

### 2.3 Arithmetic pass

- 2,442/10,705 = 22.81 % ✓; 7/4,950 = 0.141 % ✓; 39/40 = 97.5 % ✓; 1,841 − 657 = 1,184 ✓.
- Confirmation: seed deltas −0.0340, −0.0330, +0.0218 → mean −0.0151, sd 0.0319, t(2, .975)
  = 4.30 → half-width 0.079 → CI [−0.094, +0.064] ✓ matches the ledger.
- **Power fact the paper must state:** with that seed sd, a three-seed design cannot resolve a
  +0.02 target (half-width 0.079). The +0.02 margin was a *point* target with a lower-bound
  rule; it was never a detectable effect size at n = 3. Say this in limitations rather than let
  a reviewer discover it.

| paired seeds | 95 % t half-width at sd 0.032 |
|---|---|
| 3 | 0.079 |
| 4 | 0.051 |
| 5 | 0.040 |
| 6 | 0.034 |

- Iteration 2000 = 2001/4000 = 50.0 % of budget ✓ (zero-indexed checkpoint convention).
- 368,951 / 417,072 = 88.46 % admitted → 11.54 % excluded ✓.

---

## 3. The decision: what the ICRA paper claims

### 3.1 Principle

Claim exactly what the ledger supports on Sept 12, with one status label per number, and let
the *controlled inconclusive* result be a finding rather than an apology. A reviewer can
reject an overclaim; a reviewer cannot reject a matched, hash-bound, preregistered comparison
for returning the answer it returned — provided the paper's contributions are stated so that
they do not depend on a positive allocation effect.

### 3.2 Three contributions, rewritten

1. **RPM and `refeas`** *(sealed/measured).* A final-trajectory contact-capacity screen; the E1
   attractor anatomy; 22.8 % vs 0.14 % per corpus–pipeline pairing; 39/40 cross-implementation
   agreement; feasibility features transfer difficulty across policies. *Unchanged; this is the
   paper's core.*
2. **Exact temporal support as a training interface** *(measured apparatus + controlled result).*
   Frame-run units, hash-bound legal starts, zero rejected mass, explicit truncation, a paired
   evaluator — **and the finding that, on identical exact support and budget, four allocators
   (uniform, absolute-ALP, relative-ALP, conditional-failure) differ in exposure (TV 0.03–0.09)
   but not in held-out tracking at three seeds** (R−U −0.015 [−0.094, +0.064]; R−D −0.007
   [−0.022, +0.008]). State plainly that the design was underpowered for +0.02 and that AULC
   was exploratory-negative. This is the honest replacement for "capped learning-progress
   allocation" as a contribution.
3. **Admission value (H1)** *(conditional; §4).* Same failure-driven allocator D, contaminated
   800-motion bank, admission on vs off, ≥ 5 paired seeds. If it lands by Sept 12, it becomes
   contribution 3 with whatever sign it has, plus the mechanism telemetry (does D's excess mass
   migrate onto rejected intervals?). If it does not land, contribution 3 is **deleted**, not
   left pending, and DFRP + H1 become one "next test" paragraph.

DFRP is demoted to a routing option inside contribution 1 (one paragraph in §3, one row in the
results table with the 22/26 and the Δ −0.001). It stays in the paper because reviewers will
ask "why not repair?"; the answer is now measured: it is safe and, so far, neutral.

### 3.3 Title

- Without H1: **"When Failure Is Not Difficulty: Screening Reference–Physics Misalignment and
  Testing Adaptive Allocation on Exact Support for Humanoid Motion Tracking."**
- With H1 (either sign): **"Feasibility-First Humanoid Motion Tracking: Screening
  Reference–Physics Misalignment and a Matched Test of Admission and Allocation."**

Do not keep "Feasibility-Gated" unless H1 is in the paper. Do not keep "Generalist Humanoid
Controllers" — nothing in the paper tests generality across embodiments or architectures.

### 3.4 Abstract skeleton (numbers only where a table holds them)

RPM definition → E1 anatomy (3/3 seeds, 329 N vs 327 N, uniform +0.03 in 3/3) → screen at bank
scale (2,442/10,705; 7/4,950; 39/40) → transfer (0.567→0.609, p = 0.010) → exact support
(1,184 units, 368,951 starts, zero rejected mass) → **on that support, four allocators change
exposure but not held-out tracking at three seeds (R−U −0.015, CI [−0.094, +0.064])** →
[H1 sentence if landed] → conclusion: feasibility, support, and allocation are separately
measurable, and the measurable damage of RPM is in exposure, not in any allocation rule tested.

---

## 4. The one experiment: H1, admission on/off

### 4.1 Why H1 and nothing else

| candidate | tests the paper's claim? | can produce a paper-bound number by Sept 12? | verdict |
|---|---|---|---|
| **H1 gate on/off under D** | yes — the only test of "feasibility-gated" | yes: ≈ 12–14 GPU-h; runtime, partition, provenance checker exist | **run** |
| C1 continuous execution | no (evaluation-duration question) | no: selection manifest and freeze absent | stop |
| S1 physical sensitivity (96 cells) | no (robustness of already-inconclusive policies) | no: GPU parity gate failed, cause unresolved | stop |
| N stationary-noise study | mechanism of R only | no: 17.6 M-transition burn-in per cell | stop |
| P practice branches | mechanism of R only | no: restoration untested | stop |
| More confirmation seeds | forbidden by the frozen disposition | — | never |
| Video / hardware | not evidence | window closed Sept 9 | Sept 17–22 only if trivial |

### 4.2 Design (freeze before any GPU job; one seal, one analyzer dry-run)

- **Arms:** gate-on (exact admission, current D) vs gate-off (same D over the full candidate
  partition: 1,184 feasible units + 465 rejected intervals, exact H = 50 non-wrapping starts
  everywhere; rejected intervals are *dynamically rejected*, never called admissible).
  Controller, rewards, PPO, randomisation, caps, seeds, evaluator, panel: identical.
- **Seeds: five paired fresh seeds** (not 21–23; not 11/12/31/32/51/71/81). Five seeds give a
  half-width of about 0.040 at the observed seed sd, which still exceeds the historical E1
  effect of 0.03 — so state up front that H1 is powered for effects ≥ ≈ 0.04, and declare the
  outcome format as estimate + CI + per-seed values, with "positive" only if the CI lower bound
  > 0 and "negative" only if the upper bound < 0. Drop the +0.02 SESOI as a pass/fail rule; keep
  it as the reported reference line. Six seeds if the first five finish before Sept 11 12:00.
- **Primary:** paired final feasible-hard TrackingScore, gate-on − gate-off. **Guard:** all-panel
  paired difference reported, no lower-bound rule.
- **Mechanism endpoint (pre-declared, cheap, informative at any n):** in gate-off, the mean
  post-warm-up share of D's *above-prior* mass that lands on rejected intervals, versus the
  rejected intervals' prior share (0.115 of starts; ≥ 0.092 after the floor). Also: top-1
  interval identity per seed and whether it is a rejected interval. This is E1's attractor
  question asked at interval scale and it does not need policy power to answer.
- **Manipulation checks:** gate-on realised rejected trials = 0; gate-off realised rejected
  trials > 0 and post-cap rejected probability ≥ 0.0923; both arms zero invalid/censored;
  exact sampler replay at every checkpoint (the existing checker).
- **Analysis:** one frozen script with `--synthetic` positive/null/inconclusive/gate-fail
  branches, dry-run before launch, hash in the seal. Exactly one printed status.
- **Kill rule / calendar:** if the seal and scheduler are not live by **Sept 8 22:00 EDT**, or if
  fewer than five paired seeds have passed training gates by **Sept 11 12:00 EDT**, H1 is out of
  the paper and is written as the named next test. No partial-seed reporting.
- **Budget:** 10 runs × 0.74 GPU-h ≈ 7.5 h training + 40 cells; run sequentially under the
  existing 14,000 MiB / ≤ 60 % gate; one attempt per job; sentinel per job.

### 4.3 What H1 does to the paper

| outcome | contribution 3 sentence | title |
|---|---|---|
| CI lower bound > 0 | admission protects learning under a failure-driven allocator on a contaminated bank | "Feasibility-First … Matched Test" |
| CI straddles 0, mechanism shows D's excess mass on rejected intervals | admission removes measurable exposure diversion; tracking effect below the resolvable size | same |
| CI straddles 0, no exposure migration | at this contamination level (11.5 % of starts) admission neither helps nor harms; the E1 collapse needed the non-floor sampler *and* RPM | same, softened abstract |
| upper bound < 0 | report it; discuss exclusion cost vs data loss | same |

Every row is publishable because the paper's core (contribution 1) does not depend on it.

---

## 5. Stop list (until Sept 16)

- No S1, C1, N, P, shuffled-score, reliability-calibrated score, smooth gate, repair expansion,
  Newton, hardware, or new preregistrations other than H1.
- No modification of R, D, thresholds, seeds, or endpoints of the completed confirmation. No
  bootstrap or secondary re-labelling. The disposition word is "inconclusive".
- No new tools in the original `tools/` root while the H1 worktree is the launch source; keep
  H1 in `/home/linjiw/climb-gate-ablation-2026-09-06` with its own inventory hash.
- No edits to `docs/`, the companion, or the flagship until after submission.
- No autonomous "development checks" that consume the writing window. Every CPU hour from
  Sept 9 goes to the manuscript unless it is the H1 analyzer dry-run.

Each stopped thread gets **one sentence** in §6 Limitations / future work, with its measured
preparatory fact where one exists (knee 139 vs 90/120 N·m; zero command delay; continuous
adapter runs 8.6 s references; 17.6 M-transition burn-in bound for the noise study).

---

## 6. Schedule, Sept 7 → 15

| day | deliverable | done when |
|---|---|---|
| **Sept 7 (today)** | Commit the tree (§8.1). Read this file. Decide §3 (claim set + title) — this is the Sept 10 "claim selection" moved up. | `git status` clean except worktrees; decision recorded in `plan/STATUS.md` as one dated entry |
| **Sept 8** | H1 seal: contract JSON (arms, five seeds, partition hashes, endpoints, mechanism endpoint, kill rule), analyzer with four synthetic branches, scheduler argv; launch by 22:00 | `plan/H1_FREEZE_2026-09-08.sha256` written; first training job running; sentinel dir exists |
| **Sept 8–9** | Manuscript surgery (CPU): §5.4 → completed four-arm table + figure; contribution 3 rewrite; abstract; title; DFRP compression; §5.4 controls table; limitations power paragraph; AI-disclosure update (Codex *and* Claude assisted) | `paper/icra/build.sh` passes at ≤ 8 pages with H1 as a bracketed slot |
| **Sept 10** | H1 mid-point: ≥ 6/10 training gates passed? If not on track for Sept 11 12:00, invoke the kill rule now and finalise the no-H1 title | decision line in `STATUS.md` |
| **Sept 11** | H1 training complete, 40 cells run, analyzer run once, verbatim result into `RESULTS_LOG.md`, `STATUS.md`, §5.5 and abstract | one status word printed; hashes recorded |
| **Sept 12** | **Evidence cutoff.** Rebuild PDF. Red-team pass on the new text only: every abstract number has a table; every tier labelled; no "closed-loop" verb without its qualifier | `RED_TEAM.md` new rows for E4-final and H1; build audit rerun |
| **Sept 13–14** | Figure polish (Fig. 1 remove the "closed loop" arrow or relabel; Fig. 3 = paired results + learning curves; Fig. 4 = H1 if present); anonymity sweep; PDF checker; references | second build audit; PDF digest recorded |
| **Sept 15** | Submit. Then tag `icra2027-submitted`, push, and only then reopen the stop list | tag exists |

---

## 7. Page budget (eight pages including references) and cut list

| section | Sept 4 draft | target | how |
|---|---|---|---|
| abstract + §1 | 0.9 | 0.9 | rewrite, same length |
| §2 related work | 0.6 | 0.5 | merge "evaluation on fixed support" into §3.4 |
| §3 method | 1.6 | 1.2 | DFRP §3.3: keep the program statement, cut the two-stage prose to four lines |
| §4 design | 0.9 | 0.7 | E4 calibration grid → two sentences; H1 design → one paragraph |
| §5 results | 1.6 | 2.3 | new §5.4 table + figure (0.5); §5.5 H1 (0.4); controls table replaces the paragraph |
| §6–7 limitations, conclusion | 0.5 | 0.5 | add the power paragraph and the knee-torque sentence; delete one paragraph of conclusion |
| references | 0.9 | 0.9 | unchanged (22 entries) |
| **total** | **7.0** | **7.0–7.5** | leaves slack for H1 |

The existing figure `reports/relative_confirmation_results_2026-09-06/paired_results_and_learning_curves.pdf`
is already the right exhibit: seed pairs as points, mean + t-interval, four learning curves,
x-axis in transitions. Use it as is.

---

## 8. Repository hygiene (do today; ten minutes)

1. **Commit** the current tree in two commits: (a) `Record completed confirmation, DFRP
   fixed-policy result, and September plan addenda` — plans, reports, `RESULTS_LOG`, `STATUS`,
   `climb/relative_progress.py`, tests, figure scripts; (b) `Add CLAUDE.md and fable rev 4`.
   Do not commit the lock files or anything under the ignored patterns. Push.
2. **Worktrees:** leave the four detached worktrees; record their purpose and HEAD in
   `plan/STATUS.md` once. After submission, fold the H1 tools into `tools/` with a fresh
   inventory hash and remove the others.
3. **AI disclosure** in `root.tex`: "OpenAI Codex and Anthropic Claude assisted with code,
   analysis tooling, figure composition, and language editing; the authors verified all claims
   and artifact provenance." The current sentence names only Codex.
4. **`AGENTS.md`** says there is no root pytest suite; there are 310 tests that pass with the
   pinned interpreter. Fix the sentence when convenient (not paper-critical).
5. **Site** (`docs/`): unchanged until Sept 16; the public page already carries the completed
   result and is consistent with the ledger.

---

## 9. Standing rules (unchanged; they are why the evidence is trustworthy)

1. Seal before run; frozen analyzer dry-run on `--synthetic` before outcomes exist.
2. Every arm carries a manipulation check; a failed check is "not tested", never a null.
3. One status label per number; pending numbers do no load-bearing work — **including in the
   abstract and title**.
4. Prevalence is per corpus-and-pipeline pairing.
5. Repair changes the target; any repaired-reference contrast reports the 2×2 decomposition.
6. Every background job writes a sentinel; every paper number has a path in `RESULTS_LOG.md`.
7. No new threads until the submission is tagged.

---

## 10. Risks

| risk | signal | mitigation |
|---|---|---|
| H1 slips past Sept 11 | < 6 training gates passed on Sept 10 | kill rule §4.2; no-H1 title is pre-written; nothing else in the paper waits on it |
| GPU is reclaimed by other users | gate wait > 2 h on any job | sequential jobs + one-attempt rule already handle it; do not lower the memory gate |
| Reviewer reads the paper as "method with no positive result" | — | contribution 1 is positive and sealed; contribution 2 is a controlled finding with stated power; the abstract leads with E1 and the screen, not with the allocator |
| Temptation to add seeds 24–26 to confirmation because the GPU is free | anyone proposing it | forbidden by the frozen disposition; the correct use of free GPU is H1's fifth and sixth seed |
| Manuscript rebuild breaks the 8-page gate after adding two exhibits | build.sh fails | the cut list in §7 is ordered; apply top-down |
| Writing window consumed by more "development checks" | new `plan/*_2026-09-0x.md` files that are not H1 or manuscript | §5 stop list; every such file needs a paper sentence it unlocks |

---

## 11. One line for the advisor

*The controlled test ran and was inconclusive at three seeds; the paper is the RPM measurement
line plus an exact-support interface with a matched allocation result, retitled to what it
shows; the one GPU-day before the cutoff goes to admission on/off (H1) because it is the only
experiment that tests the word "gated", and it is publishable whichever way it falls.*
