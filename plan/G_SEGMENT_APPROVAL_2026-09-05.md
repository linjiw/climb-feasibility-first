# Phase-G seal and seed-1 launch approval

**Status:** explicit researcher approval, recorded before the Phase-G seal and
before confirmatory training.

On 2026-09-05, Linji issued the instruction:

> Approve the Phase-G seal and seed-1 G1/G2 launch.

This authorizes exactly:

1. finalize and write `plan/G_SEGMENT_FREEZE.sha256` after every pre-seal check
   passes;
2. launch the 4,000-iteration, 512-environment G1 deployment-uniform arm for
   seed 1; and
3. launch the matched G2 absolute-learning-progress arm for seed 1 with the
   calibrated `rho = 0.40`, `lambda = 0.05` contract.

The approval does not authorize seeds 2--3 yet. It does not authorize opening
reward, survival, MPKPE, orientation, work, TrackingScore, or any evaluator
output before the seed-1 ledger-only manipulation gate passes. A failed seed-1
gate stops Phase G as `not_tested`, exactly as preregistered.
