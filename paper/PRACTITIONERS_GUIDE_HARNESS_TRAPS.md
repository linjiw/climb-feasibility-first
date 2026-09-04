# Five silent traps in humanoid RL tracking harnesses

**Status:** draft practitioner guide, 2026-09-03. Every numerical statement below is
**measured** unless marked as a recommendation. This guide summarizes existing artifacts; it
does not create a new experimental result.

A cross-engine rollout can look plausible, produce smooth video, and still answer the wrong
question. CLIMB encountered five such failures while bringing a Unitree G1 policy, mjlab, and
Newton/MuJoCo-Warp into same-solver conformance. The final harness agrees at
`|Δqvel| ≤ 3×10⁻⁵` through the audited impact window and has zero contact-set mismatches over
300 steps × 8 worlds. The value of that certificate is the protocol that made it possible.

| trap | plausible but wrong symptom | diagnostic | required control |
|---|---|---|---|
| **1. The first action sees the old reference** | paired arms diverge immediately even though their reset states match | hash the post-reset state *and* the observation consumed by action 0; in CLIMB, assigning a clip teleported the robot after reset but left the observation stale, with `|Δobs₀| = 3.4–4.5` while `|Δq₀| = 0` | after every reference/state write, run the required forward/update path and recompute the observation before policy inference |
| **2. Float32 geometry decides a zero-distance contact** | “solver sensitivity” appears only at a lightly loaded foot | compare exact contact pairs and signed distances from identical pre-states; differences of `4×10⁻⁷` in geometry quaternion and `4×10⁻⁸` in size changed whether a `dist < 0` frictional contact existed | mirror compiled geometry/inertial arrays exactly, then require contact-set equality before interpreting trajectory divergence |
| **3. Startup randomization exists in only one world** | one engine shows a persistent torque or balance bias although the source model files match | compare live expanded model arrays, not pristine CPU model/spec files; an unmirrored randomized torso COM produced a 3.3 N·m bias residual | bind and mirror per-environment inertial, friction, encoder, and derived model fields; hash the realized randomization |
| **4. Resets and clip wraps are external state writes** | deaths cluster at an apparent impact or motion boundary and look like physics fragility | shadow-step both solvers from the same state at every substep; CLIMB matched on 1,279/1,280 substeps while one bridge silently overwrote a clip-wrap teleport | make state ownership explicit; absorb teleports, pushes, and auto-resets before the next physics substep, and log every absorbed write |
| **5. An additive sampler “floor” is not a floor** | a nominally exploratory curriculum puts nearly all mass on one failed clip | test the limit: `ε/(Σq+ε) → 0` as one priority grows, whereas a real mixture preserves `ρ p_base`; CLIMB observed collapse before normalise-then-mix | normalize the focus distribution first, then mix `p = ρ p_base + (1−ρ) p_focus`; log TV, entropy-effective support, top-1 mass, and invalid-start counts |

## Minimal conformance protocol

1. Freeze one policy, reference, seed map, control rate, and compiled robot identity.
2. Compare one physics substep from identical `(q, q̇, ctrl, warmstart)` before any closed loop.
3. Require live-model equality for randomized fields and exact contact-set agreement at boundary
   events.
4. Hash initial state, initial observation, startup randomization, policy, reference, and
   evaluator conditions.
5. Only after those checks pass, compare survival or tracking quality. A failed conformance
   gate is an integration result, not evidence of physical fragility.

## Scope and evidence

The detailed bug ledger is `plan/S1_RESULT.md`; persistent alternative explanations are tracked
in `paper/RED_TEAM.md`. The sampler derivation and measured collapse are documented in the
flagship draft and its result artifacts. The exact numerical tolerances above are a certificate
for the pinned CLIMB stack, not universal tolerances for every engine pair.
