# Pre-registration — E-HYG: end-to-end feasibility hygiene (prune) at bank scale

**Sealed:** 2026-08-21, before any outcome exists. **Approved by Linji 2026-08-21** ("完全批准加入
E3 实验矩阵") as a rider arm on the E3 matrix; launch order per the same directive ("立刻"),
reconciled with the standing GPU rule by running **through the gap-gated shared queue** (the
chain waits for ≥ 14 GB headroom and never preempts LUCID jobs). Analysis code frozen + dry-run
before outcomes (below).

## Question

Does removing dynamically infeasible clips from the training bank — the cheapest possible
intervention, 1 CPU-s/clip to identify — improve a generalist tracking policy at matched compute,
with the gains where the hygiene account predicts them and nowhere else?

## Arms (matched compute: 4,096 envs × 4,000 iterations, seed 1, frozen-launcher config)

| arm | bank | n clips | provenance |
|---|---|---|---|
| `uniform-800` (comparator) | `bank/tiers/tier_800.txt` | 800 | E3's own sealed arm, run early under E3's config |
| `uniform-800-pruned` | `bank/tiers/tier_800_pruned.txt` (sha `4cfb5aea…`) | **701** | tier_800 minus its **99 flagged clips (12.4 %)** under the pinned screen (`GLOBAL_EVAL_ADDENDUM` hashes) |

Note recorded now: tier_800 is *less* contaminated than the raw bank (12.4 % vs 22.8 %) because
the kinematic screen that built the tiers already removed some offenders — so E-HYG estimates a
*lower bound* on hygiene value for pipelines that ingest raw retargets.

## Evaluation (identical for both arms; stratified-start protocol per D1/N4)

`tools/eval_stratified.py`, offsets {0,1,2,3,4,6,8} s (clipped to clip length), 3 s windows,
8 episodes/offset, DR on, no pushes, at the final checkpoint:
- **heldout100** (unchanged eval set; per-clip difficulty = 1 − offset-mean survival);
- **ZS-ground**: `bank/tiers/zs_ground_feasible.txt` (sha `163571b7…`, 60 feasible ground-category
  clips outside every training/eval/augmentation set);
- **ZS-dynamic** (contrast): `bank/tiers/zs_dynamic_feasible.txt` (sha `0b809729…`, 60 clips).

## Sealed predictions (the "not just fewer clips" signature)

With Δ = pruned − comparator on survival, feasible stratum = heldout clips with
`infeasible_frac ≤ 0.10`:

- **P1 (primary):** feasible-only heldout mean survival Δ ≥ **+0.015**.
- **P2 (concentration signature):** gains concentrate where exposure was being burned —
  Δ on the comparator's worst decile of *feasible* heldout clips ≥ 2 × Δ on its best half; and
  the easy stratum (comparator survival ≥ 0.95) moves |Δ| ≤ 0.02. This is the statistical
  signature that separates hygiene from "faster convergence on fewer clips".
- **P3 (coverage-cost boundary):** ZS-ground Δ ∈ [−0.05, +0.02] — pruning must not *rescue*
  ground-category zero-shot (it removes unlearnable ground clips, adds no learnable ones); the
  arm that could improve ZS-ground is N7's *repair*, and this bracket is what repair must beat.
  ZS-dynamic Δ reported alongside (no bracket; descriptive).
- **P4 (descriptive):** infeasible-stratum heldout ≈ unchanged (nothing helps there).

**Decision rule:** hygiene-at-scale confirmed iff P1 ∧ P2. P3 outside its bracket in either
direction is reported as a miss of the coverage model, not adjudicated away.

Null follow-ups pre-listed: P1 pass with P2 fail → treat as data-volume/convergence effect,
report as such, no rescue analysis; P1 fail → hygiene value at this contamination level (12.4 %)
is below detection at n = 1 seed — report the CI, no additional seeds without a new seal.

## Frozen analysis

`tools/analyze_ehyg.py` — sha recorded in the companion file `plan/E_HYG_FREEZE.sha256` at freeze
time; synthetic dry-run over the four decision branches required to pass before the chain starts
training the pruned arm. Per-seed values reported (n = 1 seed each: per-clip paired distributions
+ permutation test over clips, not a seed-level t-test).

## Compute & order

Queued **after** the N3 causal block in the same gap-gated chain (N3 is the keystone; E-HYG is
~2 trainings + 3 stratified evals ≈ 4–6 GPU-h). Sentinels required. Realized GPU-hours recorded
for the budget re-plan.
