# Pre-registration — atlas v2.1: feasibility features (2026-08-18, before the screen values are looked at)

New per-clip features from `tools/n1_knee_id.py --brief` (gap 6 cm, torque-limited LP, real μ):
`airborne_frac` (frames with no collision geom within 6 cm of the plane), `infeasible_frac` (frames
whose torque-limited unsupported wrench exceeds half the robot's weight), `unsupported_impulse_per_weight_s`
(∫ unsupported force / weight dt, seconds), `torque_infeasible_frac`, `max_tau_ratio_p95`,
`sim_infeasible_frac` (frictionless non-foot geoms). Intrinsic-but-dynamic; invisible to kinematics;
distinct from N2's bank-relative support.

Predictions (same protocols as N2, `tools/analyze_atlas_support.py` extended with the feasibility block):
- **F1 within-bank fit** (training tier, LOO ridge, uniform-s1 labels): intrinsic + feasibility lifts LOO ρ
  by ≥ +0.05 over intrinsic alone under both start protocols (fixed 0.471, random 0.508), beyond a
  200-draw random-3-feature baseline; #44's LOO residual rank falls out of the top half (43 → > 60).
- **F2 cross-policy transfer** (held-out, A3 protocol): intrinsic + feasibility lifts adaptive→uniform
  from 0.567 by ≥ +0.03 with permutation p < 0.05, and the same direction on the other five pairs.
- **F3 residual anatomy**: after adding feasibility, ρ(|resid|, infeasible_frac) → within ±0.15 of 0
  while ρ(|resid|, kNN distance) stays ≥ +0.45 — the remaining misses are support, not feasibility.
- **Prevalence** (full 10,822 bank, background): reported per category with the caveat that genuine
  flight (jumps/skips) registers as airborne but not as unsupported (free fall needs no support), and
  that stance frames with feet floating > 6 cm (retarget clearance offset) can register as unsupported;
  the citable number is `infeasible_frac > 0.10` share by category.
