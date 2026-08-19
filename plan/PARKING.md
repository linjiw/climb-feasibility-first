# Parking lot — ideas that wait (one paragraph each, with why)

- **Masked-penalty ablation (P-TAX follow-on).** Gate the self-collision penalty off during frames
  where the *reference itself* interpenetrates, so the policy is not taxed for tracking accurately.
  Waits: reward changes to training arms are frozen (P-TAX seal), and it only matters if P-TAX's
  partial correlation excludes zero; post-freeze work at the earliest.
- **Rollout-only infeasibility runtime guard.** If P-SIGN passes, a deployment monitor: when a gain
  increase worsens segment tracking, flag the reference segment rather than adapting the
  controller. Waits: P-SIGN has not run; needs a deployment stack (SONIC path) that is frozen.
- **Repair operator as a general tool (beyond N7's 3–4 clips).** Contact-restoring projection over
  the whole flagged bank (2,400 clips). Waits: N7 must first show repair works on the #44 family;
  bank-scale repair is a new thread by the no-new-threads rule.
- **Feasibility-weighted sampling.** Use `infeasible_frac` to down-weight (not exclude) flagged
  clips during training. Waits: composition (N3) and grounded mixing are the sealed causal tests;
  adding a third sampler axis before they read out would confound both.
- **LP-based per-frame feasibility as a dense reward/curriculum signal.** Waits: same as above,
  plus it changes reward semantics mid-project.
- **Cross-retargeter feasibility comparison (GMR vs wbt on the 40 shared LAFAN1 clips).** One
  afternoon of CPU; strengthens the companion note's "pipeline property" claim. Waits: companion
  note deadline first; add only if the note's reviewers ask or time remains before Sept 5.
