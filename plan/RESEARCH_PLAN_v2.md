# CLIMB Research Plan — v2 (post Experiment 1)

**Date:** 2026-08-16 · supersedes §3.4–§5 of fable.md; §1–§3 of v1 (thesis, RQs, stack, banks) stand unless amended below.
**State:** Exp-1 complete (uniform vs error-adaptive, 100 clips, 3 seeds, 43,200 eval episodes). Grounded ×3 running. LUCID holds GPU priority through Sept 15 (ICRA).

> Received from the advisor 2026-08-16, stored verbatim. Amendments go in a dated
> addendum file, never inline — the branch decisions below are only meaningful if
> the version that preceded the data stays recoverable.

---

## 0. Evidence register — what is now established

| # | Claim | Evidence | Status |
|---|---|---|---|
| E1 | Error-adaptive clip sampling loses to uniform on a headroom-passing bank | 3/3 seeds; endpoint 0.780 vs 0.810; AULC 0.640 vs 0.698; peak Δ 0.145 @ ~iter 2500; Δ ≈ 20 seed s.d. | Established (one bank, one robot, 4k/30k iters) |
| E2 | Mechanism is sampler collapse, not a diffuse effect | Top-1 clip mass 0.870–0.893 in all 3 seeds; entropy minimum (1500–2500) coincides with peak performance gap | Established |
| E3 | The "uniform floor" is not a floor | p = counts + ε/N ⇒ uniform share = ε/(Σq+ε) < 1% at realistic failure rates; effective strength varies with num_envs and failure rate; inherited from mjlab upstream (bin-level sampler) | Established analytically + empirically |
| E4 | Normalize-then-mix restores coverage | Grounded telemetry: top-1 peaks 0.186 → decays 0.045; entropy ≥ 0.754 → 0.983 | Mechanically confirmed; performance pending |
| E5 | Atlas features predict per-clip difficulty for this policy | ρ ≈ 0.74 out-of-fold, single policy | Partial — cross-policy test pending (A3) |
| E6 | Gate-failing banks produce uninterpretable sampler nulls | 50-clip stratified bank: 88% mastered at 13% of a run; reinterprets SIM-M3's null | Established |
| E7 | Per-clip survival is near-bimodal | Eval distributions; frontier-band mass unmeasured | Observed; quantify in A1 |
| E8 | Early adaptive advantage exists | +0.043 at iter 500, 3 seeds, one checkpoint | Suggestive only |

Framing note for the paper: E1–E4 are *realized-exposure* results — the arm's configured curriculum and its delivered curriculum diverged, and telemetry caught it. Same methodological thesis as LUCID's dose ledger; state the through-line explicitly in both papers.

## 1. Revised hypothesis register

- **H1 (atlas):** Physics-grounded features predict per-clip difficulty *as a property of the motions, not of one training run.* Supported at ρ≈0.74 for one policy; test criterion: ρ ≥ 0.6 when fit on one arm's policies and evaluated on another's (A3). If it fails, the atlas is descriptive only and the atlas-prior branch (E7) closes.
- **H2a (repair):** Coverage-grounding rescues failure-weighted adaptivity from collapse — grounded ≥ uniform, and ≫ error-adaptive, at 100 clips. *Being tested now.* Interpretation pre-registered in the Exp-1 report §05; do not amend.
- **H2b (diversity):** The curriculum effect grows with bank diversity — Δ(grounded − uniform) at 800 clips > at 100 clips. This is the plan's central bet and the make-or-break cell (E3).
- **H2c (granularity, conditional):** Within-clip start-frame adaptivity under clip-level coverage outperforms clip-level adaptivity — i.e., the collapse was partly about the unit of prioritization (E6). Motivated by mjlab's segment-level mode not collapsing in its native single-clip setting.
- **H4 (new — moderator):** Curriculum benefit is moderated by frontier-band occupancy. Predicts: benefit correlates with band mass/flux across runs; banks constructed to hold the band populated show larger effects. Tested observationally first (A1 across all existing runs), then by construction if warranted.
- **H3 (transfer):** unchanged from v1, deferred to Phase 3; engine-transfer instantiation in §6.

## 2. What "grounded" means — fix the hierarchy before writing

A reviewer will read normalize-then-mix as a PER/PLR-style mixing coefficient. Preempt by defining grounding as a *principle with graded instantiations*, and by making the diagnosis a first-class contribution:

- **L0 — repair (not a contribution by itself):** normalize q before mixing so ε is a true, scale-invariant coverage floor. This is the fix to a measured bug with upstream reach.
- **L1 — coverage grounding:** guaranteed minimum mass on the full bank distribution (the deployment proxy). Current grounded arm = L0+L1.
- **L2 — deployment grounding:** the ε-floor targets a *weighted* deployment distribution rather than uniform-over-bank (future; connects to GACL directly).
- **L3 — physics grounding:** the prior is shaped by atlas features — down-weight predicted-infeasible clips, stratify by feature — so adaptivity operates inside a physically-informed envelope (E7; gated on H1 cross-policy).

Contribution ordering for the paper: (1) diagnosis E2/E3 with upstream impact, (2) the grounding principle + L1 result, (3) the conditions under which prioritization helps at all (headroom gate, band occupancy, diversity, granularity), (4) atlas. Related-work must engage PER (α/β), PLR (staleness mixing), and BeyondMimic's adaptive sampling head-on; the differentiator is the measured non-floor mechanism, its num_envs scale-dependence, and the domain evidence.

## 3. Decision tree on the grounded arm (extends the pre-registered table)

**Branch A — grounded beats uniform (AULC and/or time-to-target):**
Next: E3 (800-clip, uniform + grounded ×3) to test H2b; E5 seed top-up to n=5 on the headline pair; E4 long-horizon cell to establish whether the gap persists or uniform converges to parity; quantify compute reduction via iterations-to-target (§5). Extensions in order: E6 granularity, E8 ε-sensitivity (1 seed each), E7 atlas-prior if H1 passes. Paper Frame 1: *coverage-grounded curricula for generalist motion tracking* — mechanism, repair, payoff, moderators.

**Branch B — grounded ≈ uniform:**
E3 becomes decisive. Effect appears at 800 → Frame 1 with the diversity interaction as headline. Null at both → Frame 2: *when and why adaptive curricula fail in humanoid motion tracking* — collapse mechanism, non-floor bug + upstream reach, headroom gate, band-occupancy analysis, diversity test, atlas, SIM-M3 reinterpretation. E6 (granularity) is elevated as the constructive counterpart. Frame 2 is honest and publishable but a harder RSS sell; consider CoRL 2027 or RA-L as primary and stake the mechanism early via the mjlab issue + a workshop note.

**Branch C — grounded still loses:**
Collapse was insufficient as an explanation; the failure signal itself is harmful at clip granularity. Diagnostic first, no GPU: is adaptive/grounded failure mass concentrated on atlas-predicted-infeasible or irreducibly hard clips (wasted compute on unlearnable content)? If yes → E7 (atlas-capped prior) is the direct test and L3 becomes the story. Also expect A1 to show a depopulated frontier band — H4 becomes headline evidence and the ZPD premise is revised in print.

All branches keep: the diagnosis, the gates, the atlas, the exposure-ledger methodology.

## 4. Queues

### Analysis queue (CPU only — this week, before/while grounded resolves)

| ID | Question | Method | Decision it feeds |
|---|---|---|---|
| A1 | Is the frontier band populated? | From eval CSVs + training EMAs: band mass p∈[0.3,0.7] per checkpoint per arm; **plus band flux and per-clip dwell time** (bimodality with fast transit ⇒ temporal frontier, not static) | H4; whether any frontier-band sampler variant is worth an arm |
| A2 | Pre-registration of outcome upgrade | Commit §5 (endpoints, target level, seed rule) to the repo **before** grounded evals are analyzed | Protects H2a interpretation |
| A3 | Does the atlas transfer across policies? | Fit features→difficulty on uniform-arm policies, test on adaptive-arm (and grounded when done); optionally on LUCID G1 policies over the same clips | H1; gates E7 (L3) |
| A4 | Upstream reach | File mjlab issue/PR with ε/(Σq+ε) derivation + minimal repro; audit BeyondMimic's adaptive-sampling formulation for the same count-vs-distribution pattern | Priority-staking; generality of E3 claim |
| A5 | Coverage → performance dose-response | Persist per-clip visitation ledger (see §7); scatter realized coverage/entropy vs held-out AULC across all runs/seeds/checkpoints | The paper's mechanism figure |
| A6 | Early-phase read | Does grounded reproduce adaptive's iter-500 lead? Grounded self-anneals toward uniform as failures equalize — check whether it captures the early benefit automatically | Whether an ε-schedule arm is ever needed (default: no new arm) |

### Experiment queue (GPU)

| ID | Cell | Config | Cost est. | Gate |
|---|---|---|---|---|
| E2 | grounded @100 | 3 seeds × 4k iters × 4096 envs | running | — |
| E3 | diversity | 800-clip bank (screened; verify headroom + build matched holdout): uniform + grounded × 3 seeds; **no** further error-adaptive seeds (1 optional demo seed max) | ~6 runs | after E2; heavy launch post-Sept 15 unless queue gaps |
| E4 | long horizon | uniform + grounded @100 × 2 seeds → 12–15k iters | 4 runs | Branch A/B; feeds time-to-target and "does the gap persist" |
| E5 | seed top-up | +2 seeds on the headline pair → n=5 | 4 runs | after branch known |
| E6 | granularity | grounded-over-clips × failure-weighted start-frame within clip vs grounded-clip-only, @100, 3 seeds | 3 runs (shares uniform/grounded controls) | Branch B/C, or A-extension |
| E7 | atlas prior (L3) | p ∝ atlas-shaped prior × adaptive × ε-floor | 3 runs | H1 passes (A3) |
| E8 | ε sensitivity | ε ∈ {0.05, 0.2} × 1 seed | 2 runs | Branch A only |
| E9 | engine transfer | Frozen checkpoints (all arms) evaluated in Isaac Lab / PhysX on held-out clips, conformance-gated per LUCID's harness philosophy | eval-only | Phase 3; cheap insurance for H3 |

Dropped from v1: anti-curriculum arm (superseded — the comparator already lost to uniform with mechanism); 50-clip bank (failed headroom gate); bank axis revised to {100, 800} gate-passing banks.

## 5. Statistics and pre-registration (commit as A2)

- **Primary endpoint:** normalized AULC of held-out survival, iterations 0–4000.
- **Co-primary:** iterations-to-target, target = 0.810 held-out survival (uniform's Exp-1 endpoint mean; fixed now, derived from the control arm only, before grounded analysis). Reported as the "×" compute-reduction number; right-censored if unreached.
- **Secondary:** RMST-style mean steps-survived (right-censored at horizon — reuse LUCID's treatment); tracking error on survived episodes (report with explicit survivorship caveat); a blended outcome may be *explored* but cannot replace the primary post hoc.
- **Design:** arms share seed IDs (network init + env seeds) → paired-by-seed analysis. n=3 for screening cells; n=5 for the headline pair. Paired permutation/bootstrap on AULC with hierarchical bootstrap CIs; sign test retained as the assumption-free companion with its n-floor stated. Per-seed curves in the appendix.
- **Eval resolution:** 8 episodes/clip gives p in steps of 0.125 — adequate for arm means, coarse for band membership. For A1, co-estimate band occupancy from training-time EMAs; for headline cells add 16-episode evals at 3 key checkpoints (iter ~1500/2500/4000).

## 6. Sequencing vs LUCID (shared 5090, ICRA Sept 15)

- **Now → ~Aug 23:** A1–A6; E2 resolves; branch decision; mjlab issue filed; pre-registration committed.
- **Aug 24 → Sept 15:** LUCID owns priority. CLIMB does CPU work: 800-bank headroom verification + matched holdout construction; Exp-1 paper section drafted (it is evidence-complete); E3 launches only into genuine queue gaps via the shared run queue.
- **Sept 16 → Oct 31:** E3, E4, E5.
- **November:** conditional arms (E6/E7/E8); E9 engine-transfer evals; atlas section; A5 figure.
- **Dec 1:** CLIMB results freeze — GPU output thereafter only regenerates figures from the artifact log. Optional real-G1 demo (few motions, best grounded vs uniform checkpoints through the LUCID deployment path) only if Branch A *and* hardware/schedule slack post-ICRA.
- **January:** writing → RSS 2027 (verify CFP date when posted). Fallbacks: IROS 2027 (~Mar), CoRL 2027 (~May) — the natural home if Frame 2.

## 7. Process and infrastructure (ports from LUCID, plus Exp-1 lessons)

1. **Sampling ledger:** persist per-clip cumulative visitation counts and per-checkpoint distribution snapshots for every run (not only entropy/top-1 summaries). This is CLIMB's realized-exposure object; it enables A5 and makes every "what did this arm train on" claim auditable.
2. **Frozen launch copies:** run_campaign.sh copies itself and the resolved config into the report directory and execs the copy — closes the edit-while-executing hazard (bash reads by byte offset) structurally, not by discipline.
3. **Resume safety:** arms resume from the frozen resolved config, hash-checked, never re-resolved — same principle as LUCID T4; a resumed CLIMB arm with silently different ε or bank is exposure hazard territory.
4. **Shared queue:** CLIMB jobs enter the same machine-level queue and concurrency cap as LUCID; no third concurrent arm (the 25× lesson).
5. **Bank gates:** headroom gate mandatory (v1 amended); after A1, decide whether band-occupancy becomes a second admission gate or a reported covariate.

## 8. Risks (updated)

- **Grounded ≈ uniform at both bank sizes** → Frame 2 exists and is pre-built (§3B); the diagnosis + gates + atlas carry it. Cost: venue ambition, not validity.
- **Gap closes at long horizon** (adaptive was already recovering by 4k) → time-to-target is the claim that survives this; E4 exists to find out early rather than at review.
- **Novelty attack "it's just normalization"** → §2 hierarchy + A4 upstream validation + A5 dose-response figure are the defense-in-depth.
- **Atlas is run-specific** (A3 fails) → drop L3 quietly; atlas remains a descriptive contribution.
- **Compute contention** → everything heavy is post-Sept-15 by default; the branch decision and half the paper's evidence need no GPU at all.

## 9. Paper frames

- **Frame 1 (Branch A / B-with-diversity):** *Grounded adaptive curricula for generalist humanoid motion tracking* — measured collapse, coverage grounding, compute reduction in ×, diversity and band-occupancy as moderators, atlas as the physics layer.
- **Frame 2 (Branch B-null / C):** *Why adaptive curricula fail in humanoid motion tracking* — collapse mechanism with upstream reach, the non-floor result, admission gates (headroom, band occupancy), the granularity result, atlas transfer, SIM-M3 reinterpreted. Positions directly alongside the reliability identity of GALA-FM-Bench, and hands Paper 2 a testbed with known failure modes for LLM-proposed interventions.

Either frame keeps the dissertation arc intact: GACL → RTW → CLIMB → GALA-FM-Bench, with "verify the realized exposure" as the connective methodological tissue running through LUCID and CLIMB both.
