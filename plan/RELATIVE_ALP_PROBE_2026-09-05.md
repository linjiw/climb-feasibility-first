# Relative-progress ALP: a separate long-run manipulation probe

Status: exploratory design, before this probe's training. The user requested
continued simulation experiments and evidence on 2026-09-05. This is not a
continuation, replacement, or relabeling of failed frozen E4 confirmation.

## Observation and mechanism

E4 seed 1 completed both 4,000-iteration arms. Exact ALP mean post-warm-up TV is
0.0296587, below the frozen 0.05 minimum, so E4 ends `not_tested` with policy
endpoints unopened. The saved sampler distributions reproduce exactly. No
probability cap affects those eight snapshots. With deployment prior b, progress
g, mean μ=Σbᵢgᵢ, exploration ρ, and absolute floor λ, the uncapped mixture obeys

    TV(p,b) = (1−ρ) Σbᵢ|gᵢ−μ| / [2(μ+λ)].

The fixed λ=0.05 supplies 64.3% of the focus normalizer at iteration 500 and
93.6% at iteration 3999. Thus unchanged relative progress can lose allocation
contrast as its absolute scale shrinks. This is a measured replay explanation,
not an inference from hidden policy endpoints.

## One changed component

Replace g+λ by g/μ+κ, with κ=2; if μ=0 use the deployment prior. Keep the G1 robot,
PPO, exact support, event statistics, 10-tick history, ρ=0.40, failure penalty −10,
unit/clip caps 0.05/0.25, and verified bank unchanged. This is equivalent to a
relative floor λₜ=κμₜ and is invariant to positive common rescaling of g.

Frozen-history counterfactuals at κ=2 yield TV 0.0560–0.1087 (mean 0.0854), but
the learning history is endogenous: those numbers are not live-training results.
The new implementation lives in separate files and a separately named task;
no sealed runtime or analysis source is edited.

## Execution and pre-outcome decision

1. Run an 8-environment, 20-iteration lifecycle smoke, seed 11, on task
   `Climb-Tracking-Flat-Unitree-G1-RelativeALP-Probe`. Check actual allocation
   protocol/factor, exact support, checkpoint/source binding, and zero invalid or
   censored events. A missing ledger is a failure, not a warning to ignore.
2. Only after the smoke passes, run a fresh 512-environment, 4,000-iteration
   instance, seed 11, saving every 100 iterations. Use the shared 14,000-MiB gate.
3. Assess all saved ledgers at iterations ≥400: mean TV in [0.05,0.15], every
   entropy-effective count ≥12 and top-1 unit mass ≤0.05, zero invalid/censored
   events, final saturation <0.90. Record every iteration, including failures.
4. This probe has no policy evaluator. A pass warrants an independent seed-12
   manipulation replication and a new confirmatory design, not a policy-benefit
   claim. A fail ends this candidate; do not adjust κ within the running study.

Unit of replication: one new training seed. Counterfactuals use eight snapshots
of one old seed and cannot supply independent training replications. A nonzero
progress signal may be noise; amplitude invariance does not establish learnability
ranking or efficient policy learning. That requires the later matched-policy
benchmark, after independent manipulation validation.

## Provisional contribution and next evidence

- A sampler-scale diagnosis that separates exact support preservation from
  sustained adaptive allocation contrast.
- A scale-relative ranking floor retaining the existing support and cap contracts.
- A long-horizon manipulation test; downstream policy merit remains untested.

The independent DFRP fixed-policy test is reported separately. Its initial
26-clip result does not show aggregate tracking improvement, and unchanged
controls differ slightly between cells. A post-outcome same-reference repeat
is being run to measure numerical repeatability before interpreting small gaps.
