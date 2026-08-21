# Pre-registration — FGAS: feasibility-grounded adaptive sampling

**Registered:** 2026-08-20, before any FGAS training run.  The only prior
quantities used here are completed grounded-baseline outcomes, the policy-independent
feasibility sidecars, and CPU sampler calculations.  `reports/FGAS/COMPLETED` does
not exist at registration.

## Question and intervention

Does multiplying the grounded mixture sampler by a policy-independent motion
eligibility weight improve tracking per fixed training budget?  The comparator is
the completed `grounded-mixed100-s{1,2,3}` arm: a genuine 0.1 uniform mixture with
no eligibility mask.  The intervention changes only clip and start-frame exposure.
Reward, PPO, network, motion bank, environment count, iterations, and seeds remain
fixed.

The primary method is the continuous (`soft`) guard-0 sidecar.  A chosen clip is
weighted by its mean eligible mass and its local start is drawn in proportion to
`bin_score`.  The hard mask is an apparatus ablation after the primary comparison;
it is not pooled with the soft arm.

## Frozen configuration

| field | value |
|---|---|
| task | `Climb-Tracking-Flat-Unitree-G1-Grounded` |
| training bank | `bank/tiers/tier_mixed100.txt` |
| eligibility | `reports/eligibility/tier_mixed100_guard0_bin50/` |
| sidecar set hash | `bd742558d72bad2e37a65953cb7ec028e23092df7d9699b33549848aa72519e3` |
| method | mixture floor 0.1 + soft eligibility |
| budget | 4,000 iterations, 4,096 envs |
| seeds | 1, 2, 3 |
| final heldout eval | `heldout100`, 8 random-start episodes per motion |
| mechanism eval | `fgas_feasible_hard20.txt`, offsets 0/1/2/3/4/6/8 s, 8 episodes, 3 s window |

`fgas_feasible_hard20.txt` is fixed from the pre-existing grounded final results:
heldout motions with `infeasible_frac <= 0.10` and three-seed mean survival strictly
between 0.2 and 0.8.  It contains 20 motions and has SHA-256
`ba0dc06c2110bd1688443f4f458b3a85d1c51adb7553b05114cf9243036454a7`.

## Outcomes and decision rules

1. **Primary performance:** seed-matched survival delta on feasible-hard20.
   FGAS is beneficial only if mean delta is at least +0.05 and the fixed
   seed-by-motion bootstrap 95% lower bound is above zero.
2. **No regression:** final heldout survival over the 71 feasible motions may fall
   by no more than 0.03.
3. **FGAS-2 attractor:** over iterations 2,000–3,999, predict
   `P(top-1 clip flagged) < 0.40` while mean top-1 mass remains 0.30–0.38.  The
   grounded baseline is 0.737 and 0.339.  If selection remains near 0.74, FGAS is
   frame hygiene rather than a moved curriculum attractor.
4. **Implementation gate:** mean late `sampling_ineligible_mass < 0.15` for soft
   FGAS.  CPU projection before training gives 0.28984 in measure-only mode,
   exactly 0 under the hard mask, and 0.10269 under the soft mask with a flat
   clip distribution.

The implementation gate amends the earlier shorthand “approximately zero.”  A
continuous score is nonzero on some hard-rejected boundary bins by design, so
zero is a valid invariant only for the hard ablation.  This clarification is made
before outcomes and preserves the primary soft method.

The frozen analyzer is `tools/analyze_fgas.py` (20,000 bootstrap draws, seed
20260820).  Analyze only after all three method seeds and matched evaluations are
complete.  A partial arm is an operational diagnostic, not a result.

## Execution and stopping

`tools/run_fgas_campaign.sh` freezes its resolved config and code hashes, refuses
to run alongside another CLIMB trainer, and requires at least 14 GiB free GPU
memory.  Do not change code or thresholds after launch.  Hardware failure permits
an exact-config resume; scientific underperformance does not.  No external filing,
submission, or publication is authorized by this registration.
