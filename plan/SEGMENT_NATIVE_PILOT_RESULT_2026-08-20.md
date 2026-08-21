# Segment-native v2 exploratory pilot result — 2026-08-20

**Status:** unsealed exploratory wiring result. This does not amend FGAS or N7
and is not evidence of a confirmed training benefit.

## What passed

The isolated segment command now samples only exact horizon-safe starts, assigns
outcomes to stable units, updates conditional statistics on a fixed clock, caps
unit/clip mass, and explicitly truncates every 50-step trial. An 8-env GPU trace
completed 24/24 trials without a wrap, invalid reference, or censored reset.

Both 512-env PPO arms completed 200 iterations (2,457,600 steps each) on the same
10 clips and 42 units. The initial objective strongly rewarded early failure; a
shared failure-only event cost of −10 passed the predeclared anti-collapse gate.
Final checkpoint ledgers contain zero invalid starts, invalid frames, or censored
resets. The adaptive arm retained 31.51 entropy-effective units with exact 0.05
unit and 0.25 clip caps.

## Paired result

The evaluator replayed 504 identical worlds per policy (42 units × 3 phases × 4
replicates). Environment seed, starts, initial state, and startup domain-randomization
hashes match across arms. Unit-clustered 10,000-resample intervals give:

| Endpoint (adaptive − uniform) | Estimate | 95% interval |
|---|---:|---:|
| Success | +0.0079 | [−0.0536, +0.0714] |
| Survival | +0.0115 s | [−0.0100, +0.0346] |
| Common-frame body position error | −0.00420 m | [−0.00663, −0.00190] |
| Common-frame anchor orientation error | −0.02795 rad | [−0.03966, −0.01628] |

Anchor position, joint error, and work intervals cross zero. Quality uses 22,321
paired common-survivor frames, so early failures cannot improve the comparison.

## Decision and next gate

Keep the runtime/evaluator implementation; hold the benefit claim. The treatment
was weak: its final distribution was only 0.0279 L1 (0.0140 total variation) from
the capped deployment control, with correlation 0.998. Entropy alone did not
expose this near-null manipulation, so adaptation total variation is now explicit
telemetry.

Do not spend two additional seeds on this configuration. First freeze a separate
development panel, a minimum curriculum-separation gate, and the missing
unmasked-grounded arm. An outcome-blind sensitivity calculation finds that
difficulty power 4 would yield 0.0550 TV while preserving both caps and 31.74
effective units; this is a candidate to preregister, not a result. Only after the
manipulation gate passes should the planned three-seed, three-arm study proceed.

Artifacts: `reports/segment_v2_pilot/result.json` and
`autoresearch/segment-native-260820-2259/research_log.md`.
