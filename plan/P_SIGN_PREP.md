# P-SIGN prep (TASK psign-prep, v6 P2) — frozen 2026-08-20, no P-SIGN outcome exists

*Status labels used: exploratory (mechanism hypothesis), pending 🕐 (all P-SIGN outcomes),
measured (the two supporting cases). Artifact paths touched: `tools/analyze_p_sign.py`,
`tools/p_sign_gate.py`, `plan/P_SIGN_clips_*.txt`. UNVERIFIED: none. Verified at prep time:
`reports/P_SIGN/` does not exist — no outcome files for the sealed experiment.*

## 1. Frozen analysis harness

`tools/analyze_p_sign.py` — sha256
**`db538a9bba7233706fc699f7b358ad29585add35d8328fb1624beefc47406464`** — implements the three
sealed criteria of `PREREGISTRATION_P_SIGN.md` (`c7916e8c`) exactly: (i) ≥ 8/12 family clips with
airborne-window S ≥ +5 mm and 95 % bootstrap CI > 0; (ii) ≥ 8/12 controls with whole-clip
|S| < 2 mm; (iii) ≥ 3× airborne/standing localisation among the clips passing (i). Windows are
computed from the *reference only* (screen at gap 6 cm; airborne = no contact ∧ torque-limited
unsupported > ½ weight, ±0.1 s dilation) — before and independently of any rollout. The per-run
identical-physics floor (arm-A base vs arm-C base, per clip) is computed and stored in the same
summary. Synthetic dry-run (3 branches: PASS / generality-fail 5-12 / control-contamination)
decides as sealed — run 2026-08-20, no real data touched. **This file must not change once
`reports/P_SIGN/run0` exists.** Runner: `tools/p_sign_gate.py` + gap watcher (fires only at
≥ 7 GB free ∧ < 60 % util for 3 consecutive minutes; writes sentinel).

## 2. Mechanistic hypothesis (exploratory — one paragraph, as directed)

**Hypothesis: stronger motors track an infeasible reference more faithfully, and fidelity to an
impossible plan is a liability.** During an airborne-reference window the PD targets encode a pose
trajectory whose execution requires support that does not exist. A weaker robot (−15 %) lags the
targets; its state drifts toward what the *dynamics* permit — earlier, softer contact, a lower
root — which happens to be closer to a recoverable configuration. A stronger robot (+15 %) closes
the tracking loop harder, holds the commanded (floating) pose longer, converts the tracking error
into ballistic root error instead of joint error, and arrives at the eventual contact event
faster, in a worse configuration, with more momentum. This predicts precisely the observed
structure (measured, two cases: `reports/G1/run0`, `run1_seed1`): no effect while the reference is
supportable (+0.3 / −1.4 mm), a positive body-pos-error effect inside the airborne window
(+15.0 / +16.0 mm), persistence into the aftermath (+26.8 / +20.4 mm), and *benefit* from strength
on every feasible clip (−2.6 to −14.2 mm). It also predicts the P-SIGN control criterion (ii):
feasible ground-family clips, same category and posture class, should show no airborne-class
effect because there is no airborne window to be faithful to.

**Falsification via N7 (written before either runs):** the repair operator restores contact under
the descent without changing the commanded poses' intent. If the mechanism above is right, the
sign reversal must **vanish on the repaired clip** (airborne-window S within ±2 mm of the
per-run floor, N5 instrument), because fidelity is no longer a liability once the plan is
executable. If the reversal *persists* on the repaired clip, the mechanism is wrong — the effect
would then be a property of the posture class or the policy's out-of-distribution behaviour, not
of infeasibility — and the "rollout-only infeasibility detector" reading dies even if P-SIGN
passed. This falsifier is written into `plan/N7_DRAFT_repair.md`'s prediction list and will be
carried verbatim into the N7 seal.
