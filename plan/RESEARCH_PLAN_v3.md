# Physics-Grounded Humanoid Tracking — Story, Status, and Plan v3 (Fragility Program)

**Date:** 2026-08-17 · supersedes RESEARCH_PLAN_v2.md as the thesis document; v2's pre-registered sampler queue survives as the application track (§10).
**Decision this document encodes:** re-center the thesis on Newton's distinctive capabilities — multi-solver physics under one model, batched dynamics, differentiability — with the curriculum work as supporting evidence and first application. Fund spikes S1–S5 this week.

> Received from the advisor 2026-08-17, stored verbatim. Amendments go in dated
> addendum files, never inline.

---

## 1. The research story, told as one arc

The goal was always: use Newton to make humanoid research better — more stable policies, better sim2real, deeper understanding of RL training and of the physics of motion. The path there ran through three phases that looked like detours and were not:

**LUCID** established the lab's methodological signature: *verify the realized exposure before believing any number*. Six measured exposure defects, a conformance-gated evaluation harness, severity sweeps showing latency is the binding axis for this robot (degradation onset 70–80 ms) while mass and friction barely register, and a corrected G1 model (hip-roll 88 N·m).

**CLIMB Phase 0 + Exp-1/2** built the assets: a validated 10,822-clip / 43.6 h G1 motion bank (three silent corruptions caught), a physics-feature atlas predicting per-clip difficulty at ρ ≈ 0.74 out-of-fold, a multi-clip training capability, and a measured sampler-collapse mechanism now filed upstream (mjlab #1153, BeyondMimic #73). Exp-2 landed Branch B: grounding repairs the collapse, matches uniform on AULC, edges it on endpoint.

**The drift and its yield.** All of that was answered inside mjlab; Newton ran as substrate. But the detour produced exactly two findings that only a physics program can explain, and they are the pivot:

- **F1 — difficulty is a motion property the reference does not capture.** Independently trained policies agree on per-clip difficulty at ρ = 0.832; the reference-only atlas transfers at 0.567. One-third of the signal is missing, and clip #44 shows where it lives: survival 0.31 against a bank mean of 0.89, atlas profile benign (μ = 0.18, peak GRF 1.42×). What makes it hard is the motion × robot × contact interaction — observable only by simulating it.
- **F2 — the frontier is temporal and forgetting is measurable.** 69% of clips transit the band, ~16% mean dwell, re-loss rates ordered by sampler (5.6 / 7.7 / 10.3 per 1k iters). The ledger tooling that measured learning dynamics over *clips* transfers directly to measuring them over *physics parameters*.

## 2. Goal traceability — where each original goal now lives

| Original goal | Where it lives in v3 |
|---|---|
| Improve stability | Fragility maps (T1) locate where a policy's behavior depends on modeling choices; fragility-aware motion admission (§9.4) and fragility-weighted training (T2) act on it |
| Improve sim2real | H-F1 validation ladder: held-out solver → LUCID's existing Isaac→MuJoCo degradation data → pre-registered real-G1 set (§7) |
| Analyze deep into RL training | F2 machinery: per-clip and per-parameter learning/forgetting dynamics via the exposure ledger; sensitivity-over-training (T3) |
| Motion understanding, especially physics | Atlas v2 with measured interaction features; target = close 0.567 → 0.832 (H-F2) |
| Leverage Newton specifically | Nine solvers under one Model, ArticulationView batched dynamics, ONNX policy path, differentiability — each mapped to a thrust in §4 |
| Integrate SONIC WBC | Conformance → fragility map of a foundation controller → CLIMB-vs-SONIC comparison (§9) |

## 3. Central thesis

A humanoid tracking policy's stability and its sim2real transfer are governed by **where in a motion the physics is fragile** — segments whose outcome changes under small changes to contact model, actuation model, solver, or parameters. Newton makes fragility measurable per segment and per axis, before deployment. Measured fragility then (a) diagnoses why controllers — including SONIC — fail on specific motions, (b) supplies a physics-grounded prior that repairs the atlas's transfer gap, and (c) defines where robustness training should spend its budget.

## 4. Newton capability → role (delta to retrospective §02)

The retrospective's capability table stands. Role assignments: multi-solver = the physics ensemble (T1); ArticulationView = batched probe rollouts and the atlas's inverse dynamics (replacing raw MuJoCo); warp_nn ONNX = frozen-policy evaluation incl. SONIC; differentiability = T3, spike-gated, with mjlab's `enable_backward=False` noted as the reason this must run Newton-side. Honest limits, restated so no plan builds on them: no PhysX backend (LUCID's Isaac data covers that engine), no trainer (mjlab remains the training stack), Isaac Lab 3.0 not installed and not required.

## 5. Measurement methodology — the core of the program

Raw long-horizon divergence between solvers is not a fragility signal: closed-loop humanoid rollouts are chaotic, so trajectories separate exponentially after the first contact event under *any* perturbation, and endpoint distance saturates everywhere. The protocol that avoids this:

1. **Canonical trajectory.** Roll the frozen policy once per clip in the reference config (MJWarp, default contact, nominal actuation); record states.
2. **Resynchronized probes.** At probe times every 0.25–0.5 s (plus at contact events): initialize every physics config at the canonical state; roll closed-loop for a short horizon k (0.3–1.0 s, tuned by a divergence-growth pilot).
3. **Outcome measures at t+k:** base pose/velocity error, CoM deviation, contact-set Hamming distance, and local failure probability under a small within-config noise ensemble (n ≈ 8).
4. **Variance decomposition — the definition of fragility.** Within-config ensemble variance = the chaos/aleatoric baseline; between-config variance in excess of it = model-dependence. Fragility(segment, axis) = between-config component normalized by within-config component. A segment can be chaotic-but-model-agnostic (all configs agree it is a coin flip) or model-dependent (outcome flips deterministically with the config); only the second is fragility.
5. **Per-axis normalization.** Z-score/rank per axis against its own global median so tier offsets (e.g., XPBD globally softer) do not masquerade as per-segment signal. Timestep and iteration settings matched across solvers or the axis confounds with integration error.

**Axes:** solver {MJWarp, MuJoCo-CPU, Featherstone, XPBD — pending S2}; contact model {default, hydroelastic, SDF if stable}; actuation {nominal PD, latency 20/40/60 ms, armature/damping variants, corrected torque caps} — mandatory, because LUCID showed latency is this robot's binding axis; parameters {friction, mass} as the classical-DR control axis, predicted near-flat per LUCID.

## 6. Thrust 1 — fragility maps

**H-F1:** per-segment fragility predicts transfer failure better than any reference-only feature. **H-F2:** adding fragility features lifts atlas cross-policy transfer from 0.567 toward the 0.832 ceiling.

**Validation ladder (cheapest first):**
1. *Held-out solver:* does fragility measured on axes A predict degradation on a solver left out of the map?
2. *LUCID cross-engine data — already on disk:* correlate per-motion fragility with the measured Isaac(PhysX)→MuJoCo degradation from LUCID's 324/165-rollout sweeps. This is H-F1's first real test and costs CPU. A null here is a serious warning (see kill criteria).
3. *Real G1:* a pre-registered 10–20 motion set spanning predicted fragility, deployed through the SONIC/LUCID path post-ICRA; correlate predicted fragility with real tracking failure.

**Clip #44 — three explanations, discriminated in order:** (a) *data artifact* — the hygiene history earns this check first: interpenetration, foot-skate, retarget residual audit; (b) *estimator artifact* — A7's attractor analysis; (c) *genuine interaction* — S3's fragility probe. Signatures differ: bad data fails identically across all configs with anomalous contacts; interaction shows high between-config variance. Pre-registered before S3 runs.

**Caveat carried openly:** solver agreement ≠ physical truth — rigid-body solvers share blind spots (foot compliance, transmission dynamics). Disagreement lower-bounds model uncertainty; the hydroelastic and actuation axes plus ladder rung 3 anchor the map to reality.

## 7. Thrust 2 — robustness where it matters (staged, riskiest last)

1. **Eval-side profiling (now):** every existing checkpoint (Exp-1/2 arms, LUCID policies, SONIC) evaluated across the solver/contact/actuation grid. Free of training compute; produces the cross-policy fragility comparison of §9.3.
2. **Fragility-weighted curriculum (the CLIMB merge):** training stays in mjlab; Newton supplies the signal. The L3 prior becomes *measured* fragility instead of reference-read features — the principled answer to the attractor problem (#44 attracts mass because it is hard for reasons the sampler cannot see). Pre-registered as an added arm sharing E10's controls. **H-S2:** fragility-weighted training improves held-out-solver and real transfer at matched compute vs uniform and vs failure-weighted.
3. **True solver-ensemble training:** Newton-side rollout workers; highest engineering risk; sequenced after the RSS decision point, only if stages 1–2 justify it.

## 8. Thrust 3 — differentiable sensitivity (spike-gated)

If S5 passes, d(tracking error)/d(friction, mass, stiffness, gains) per short resynchronized horizon — the same probe protocol as T1, so gradient-based and swap-based sensitivity are directly comparable on the same segments. **H-D1:** contact-stiffness-sensitive segments are the sim2real failures; gain-only-sensitive ones are not. Long-horizon gradients through chaotic contact are known to explode (the SHAC lesson); short horizons are load-bearing, not optional. Fallback on S5 failure: finite-difference sensitivity over a ~10-parameter subset, batched via ArticulationView — stated now, not at month three.

## 9. SONIC program (evaluation-only, starts this week)

1. **Conformance (S4):** release encoder/decoder ONNX through warp_nn; match the observation contract (64D token + hands); confirm tracking on one LAFAN1 clip matches SONIC's own MuJoCo harness. Conformance-before-belief — the LUCID lesson, applied before any SONIC number is quoted.
2. **SONIC fragility map:** the release policy across the solver/contact/actuation grid over the LAFAN1 bank. "Where does a SOTA foundation WBC's behavior depend on the physics engine?" — no training, no hardware, a few GPU-hours, and a result nobody has published.
3. **CLIMB-vs-SONIC comparison:** same clips, same grid. Shared fragile segments ⇒ fragility is a motion property; disjoint ⇒ a recipe property. Both answers are papers.
4. **Application — fragility-aware motion admission:** a pre-deployment screener that flags or modifies motions whose predicted fragility exceeds threshold. Concrete stability deliverable for any G1 deployment, including SONIC's.

## 10. Relationship to the pre-registered CLIMB queue

E10 (freshness/liveness/cap 2×2), E3 (800-clip), E4 (long-horizon) stand as pre-registered — they are sound as a sampling study and their upstream findings are already banked. Changes: (a) they no longer carry the thesis; (b) a fragility-weighted arm is added to the E10/E3 window, pre-registered before the post-Sept-15 launch; (c) Branch-B's "800 clips is decisive" now decides the *sampler paper's* frame, not the program's. If T1's early results are strong, the flagship paper's spine is physics fragility with curriculum as one application — the inverse of v2's framing.

## 11. Spikes and kill criteria (this week, in order)

| # | Spike | Gate it answers | Kill/fallback | Cost |
|---|---|---|---|---|
| S1 | Exp-1 checkpoint → ONNX → Newton SolverMuJoCo on walk1_subject1; survival matches mjlab within noise | Newton↔mjlab conformance — nothing else is believable before this | Fails and unfixable in a week → escalate; whole eval path blocked | ½ day |
| S2 | Same clip/policy under Featherstone, XPBD | Can non-MuJoCo solvers run a contact-rich humanoid at all | Only MuJoCo variants survive → solver axis shrinks; program continues on contact/actuation axes | ½ day |
| S2b | Divergence-growth pilot → choose probe horizon k; verify within/between decomposition separates | Methodology (§5) is measurable | Between-config variance never exceeds within → fragility as defined is empty; rethink before any map | hours |
| S3 | Clip #44 through the grid, after the data-artifact audit | H-F1's first prediction; #44 discrimination | Nothing elevated → motivating anomaly weakens; report honestly, H-F1 rests on the LUCID correlation instead | hours |
| S4 | SONIC ONNX conformance vs its own harness | SONIC program viability | Obs contract unresolvable → SONIC deferred; T1/T2 proceed on own checkpoints | 1 day |
| S5 | wp.Tape backward, 100 steps, 68 geoms; d(err)/d(friction) finite | T3 as differentiable | FD fallback, scoped subset | 1 day |

Additional pre-registered check: **LUCID-correlation** (ladder rung 2) runs immediately after S1/S2b — a null there demotes H-F1 from *predictive* to *diagnostic* claim and the paper reframes accordingly rather than discovering it at review.

## 12. Timeline, venues, coordination

- **Now → Sept 15 (LUCID owns training GPU):** spikes S1–S5; LUCID-correlation; SONIC conformance + fragility map v0; eval-side profiling of all checkpoints. All evaluation-side, gap-capacity only.
- **Sept 15 → Oct 31:** E10 + fragility-weighted arm + E3 per pre-registration; atlas v2 (H-F2) fit and cross-policy test.
- **Nov → Dec:** T2 stage-2 results; real-G1 pre-registered set if hardware slack post-ICRA; Dec 1 results freeze.
- **Venues:** fragility program → RSS 2027 if the validation ladder holds by December, else CoRL 2027 as primary; sampler paper → RA-L/IROS or a workshop staking the collapse mechanism; SONIC fragility map is independently workshop-able early.
- **Dissertation arc:** GACL → RTW → LUCID (verify realized exposure) → CLIMB (verify realized curriculum) → Fragility (measure where physics is trustworthy) — one thesis: *grounded, verified training and evaluation for embodied RL*.

## 13. Risks, honestly

Chaos swamping the signal (S2b exists for this); solver ensemble collapsing to MuJoCo variants (axes reweight); agreement-blind-spot critique (§6 caveat + real-robot rung); SONIC obs contract (spiked); differentiability at G1 scale (spiked, fallback declared); the redirect itself costing the sampler paper momentum (it doesn't — E10/E3 run unchanged in their window, and the fragility-weighted arm gives them a second life).
