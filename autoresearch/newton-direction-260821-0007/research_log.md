# Newton direction + website publication log

## Objective

Explain the segment-native implementation and exploratory training result on the
public project site, then revisit the design so the next experiment tests a real
benefit from Newton-grounded physics information rather than merely rerunning a
weak failure curriculum.

## Baseline

- Public site: GitHub Pages from `master/docs`.
- Segment pilot: 42 exact feasible units, 4,679 legal starts, two 512-env ×
  200-iteration arms, 2,457,600 transitions per arm.
- Mechanics: 24/24 vectorized lifecycle trials; zero invalid starts, invalid
  frames, or censored resets in training.
- Paired evaluation: 504 worlds/policy; adaptive−uniform success +0.0079
  [−0.0536,+0.0714], survival +0.0115 s [−0.0100,+0.0346].
- Quality signal: common-survivor body-position error −4.20 mm and
  anchor-orientation error −0.0280 rad, both intervals below zero.
- Manipulation failure: final curriculum TV from control 0.0140; correlation
  0.998. Do not spend more seeds on this configuration.

## Iteration record

| Stage | Hypothesis / action | Result | Decision |
|---|---|---|---|
| D0 | Healthy entropy implied a meaningful adaptive treatment | falsified: final TV was only 0.014 | add explicit adaptation-TV telemetry and a minimum manipulation gate |
| D1 | Conditional failure probability alone is an adequate rank | falsified on this panel: rates saturated near one | replace sole failure rank with learning progress/uncertainty; test physics information incrementally |
| N0 | Existing Newton 1.0-oriented plan is current | falsified: official latest is Newton 1.5.0 (2026-08-11) | recertify in an isolated v1.5 environment; do not mutate pinned MJLab |
| N1 | Newton should host the trainer | rejected as unnecessary | keep MJLab PPO; use Newton as a paired short-horizon measurement teacher |
| N2 | Solver disagreement itself is a useful fragility label | rejected | require same-config deterministic floor and held-out-axis/policy prediction |
| N3 | Differentiable MuJoCo can anchor the first experiment | rejected by current solver matrix | start with deterministic finite swaps; keep differentiability as a later solver-specific spike |
| W0 | A short index-page card can explain deployment and evaluation | insufficient for the requested training narrative | add a dedicated method page with a five-stage lifecycle, telemetry table, paired endpoints, and claim boundary |
| W1 | Scoped publication might depend on unrelated dirty tracked files | falsified in a clean HEAD archive | 30 focused tests pass with only the segment-native code/tool/test set added |
| W2 | The publication is ready to leave the worktree | passed: local HTTP 200, links/claims checked, 30 tests, Ruff, diff check, and both research seals pass | publish only the explicit allowlist through review; leave unrelated changes untouched |

## Validation so far

- Local HTTP responses: `index.html` and `segment-native.html` both return 200.
- Internal links resolve; the index has 9 sections and the training note has 7.
- Displayed success, survival, quality, frame-count, and lifecycle claims match
  `result.json` and `timeline_trace.json` programmatically.
- Clean-scope check: 30 focused tests pass against repository `HEAD` plus only
  the proposed segment-native implementation files.
- Canonical environment check: 30/30 focused tests and Ruff pass under
  `mjlab-1.6.0/.venv`; FGAS and N7 SHA-256 seals both verify.

## Current keep / discard

**Keep:** exact feasible segments, stable unit IDs, fixed trial horizon, explicit
truncation, probability caps, paired startup state/DR, terminal-safe reads, and
common-survivor quality.

**Discard:** raw failure flux, saturated conditional failure as the only rank,
entropy-only treatment checks, long-horizon solver divergence, and any claim that
one-seed quality deltas already prove a training benefit.

## Publication scope

Only the website, concise evidence artifacts, design/result addenda, and this
log will be staged. The pre-existing dirty worktree and sealed files remain
outside the publication commit.

## Next falsifiable step

Build an isolated Newton v1.5 conformance harness, then measure deterministic
0.25–0.50 s canonical-state probes. Advance a Newton fragility vector into G3
only if it predicts held-out physics degradation beyond reference kinematics and
the feasibility screen. Otherwise retain Newton as a diagnostic instrument and
do not spend a training arm on it.
