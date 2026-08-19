# 3. Failure-adaptive sampling collapses, and its uniform floor is not a floor

**Claim class: sealed-confirmatory** (campaign design pre-registered in Plan v2; adjudication `plan/BRANCH_DECISION.md`; artifacts `reports/campaign_summary_3arm.json`, `reports/A5_coverage_dose.json`, `reports/A7_attractor.json`).

**Setup.** Unitree G1 motion tracking in mjlab (MuJoCo-Warp), 4096 environments, 4000 PPO iterations,
tier_mixed100 (100 clips, 1260 s) from a validated 10,822-clip AMASS/LAFAN1 bank; held-out evaluation
on 100 disjoint clips, 8 episodes per clip, 3 seeds per arm. Three samplers: uniform over clips;
failure-adaptive (BeyondMimic-style bin sampling, probability ∝ failure EMA + ε/N); grounded
(normalise-then-mix: (1−ρ)·softmax-normalised failure weights + ρ·uniform, ρ = 0.10).

**Collapse.** The adaptive arm concentrates 87–89 % of its sampling mass on a single clip
(top-1 mass max 0.884 / 0.870 / 0.893, mean entropy 0.38–0.40) in all three seeds — and it is the same
clip in all three (BMLmovi_Subject_64_9, "#44"). Uniform holds entropy 1.0 by construction; grounded
holds 0.60–0.62 with top-1 ≤ 0.57–0.70. Held-out survival at 4000 iterations: adaptive 0.780 ± 0.006,
grounded 0.825 ± 0.009, uniform 0.810 ± 0.005; area under the learning curve 0.640 / 0.696 / 0.698.
Uniform beats adaptive in 3/3 seeds — per-seed Δ(uniform − adaptive) at iteration 3999: +0.0300 / +0.0275 / +0.0300 (mean +0.0292; recomputed from `reports/campaign/*_it3999.csv`); the standardized d_z = 20.2 (`reports/campaign_summary_3arm.json`) merely reflects the 0.0014 seed s.d. and is footnoted, not headlined — at n = 3 the permutation floor is p = 0.125 and the sign test is 3/3. Grounded matches uniform on the primary
(AULC −0.002) and edges it on the endpoint (+0.015, 3/3 seeds) — Branch B, pre-registered.

**The non-floor.** The upstream sampler mixes an ε/N term *additively into counts*, so the effective
uniform share is ε/(Σq + ε): with N = 100 clips and realistic failure rates the floor is below 1 %,
and it shrinks with num_envs because Σq scales with the number of environments contributing failures.
The parameter is documented as a floor; it is not one. Filed as mjlab #1153 and
whole_body_tracking #73 with the derivation and a minimal reproduction; the grounded sampler is the
one-line repair.

**What the attractor is.** #44 is a kneel/crawl clip (non-foot ground contact 61 % of frames, 99.7th
percentile of the bank; the training bank has 3.2 % of its duration in that category). Its measured
survival was 0.31 under random start offsets and 0.00 from frame 0 — the first is an artefact of
start-offset averaging (episodes that begin after its ground segment survive), which is why every
difficulty label in this paper uses stratified starts. Under the frame-0 protocol it is unlearnable
for every policy we trained; the sampler that weights by failure therefore never lets go of it.
Section 5 establishes that this is neither physics fragility nor merely coverage: the reference is physically impossible on its descent. Under the D1 evaluation policy (`plan/GLOBAL_EVAL_ADDENDUM.md`), the survival numbers above are the sealed all-clips secondaries; the feasible-only primaries are in §4.
