# Pre-registration — N3: coverage causality (augment tier_mixed100 with kneel/crawl neighbours)

**Written:** 2026-08-18, after N1 (reference of #44 is dynamically infeasible in its descent
0.75–1.75 s and rise 8.0–8.5 s; feasible in the kneel/crawl 1.75–7.25 s) and N2 (atlas misses
concentrate on low-support clips, ρ ≈ 0.55–0.60), before any augmented training run exists.
Conditions on N1 as the advisor's guidance requires.

## Claim under test

The uniform-mixed100 policies cannot track ground-support motion because the training bank has
almost none of it (2 clips, 3.2 % of duration; N2), not because the physics is fragile there (G1)
and not only because #44's own descent is infeasible (N1). Adding a small set of *feasible*
kneel/crawl neighbours to the bank should make the feasible ground-support phases trackable —
and specifically ground-support neighbours, not just any 16 clips.

## Design

| item | value |
|---|---|
| base bank | `bank/tiers/tier_mixed100.txt` (100 clips, 1260 s) |
| **ground16** | `bank/tiers/aug_ground16.txt` (sha `e489f1b8…`, 197 s): the 16 nearest ground-category clean-bank clips to #44 in the atlas's z-space (A3 `FEATURES`), *excluding* mixed100/heldout100, and **passing the N1 feasibility screen** (≤ 10 % of frames with unsupported wrench > 0.5·weight under torque limits, gap 6 cm; `reports/N3_candidate_feasibility.json`). Note: 12 of the 40 nearest candidates failed the screen (17–37 % infeasible frames) — the airborne-descent artefact is a family trait of BMLmovi sit/kneel retargets, not unique to #44 |
| **random16** | `bank/tiers/aug_random16.txt` (sha `17aa3f5a…`, 114 s): 16 clean clips, `nonfoot_ground_frac ≤ 0.02`, 4–15 s, seed 0, excluding mixed100/heldout100 |
| training | identical to the campaign (`run_campaign_frozen.sh` config: 4096 envs, 4000 iterations, mjlab `Climb-Tracking-Flat-Unitree-G1[-Adaptive]`), frozen launch copy |
| arms (priority order) | A1 uniform on mixed100+ground16, seeds 1 and 2 (**keystone**); A2 adaptive on mixed100+ground16, seed 1; A3 uniform on mixed100+random16, seed 1 (specificity control) |
| comparators (exist) | uniform-mixed100 s1/s2/s3, adaptive-mixed100 s1/s2/s3 (`reports/campaign/`, `logs/rsl_rl/g1_tracking/`) |
| evaluation | **stratified-start protocol** (`tools/eval_stratified.py`): offsets {0,1,2,3,4,6,8} s, 3 s window (or to clip end), 8 episodes per offset, joint-IC noise 0.05 rad, training-distribution DR on, no pushes; plus the campaign's heldout100 evaluation for regression |
| probe clips | `plan/N3_probe_clips.txt`: #44, matched-easy CMU_76_02 and BMLhandball_S07, and three ground16 members (KIT_3 kneel_down_to_crawl02, BMLmovi_36_2, Eyes_Japan hamada bended_knees) — the last three are *in* the augmented bank, so their improvement is training-set improvement, reported as such; #44 is not in any bank |

Baseline, uniform-mixed100-s1 (`reports/N3_baseline_uniform-s1_strat.csv`), survival per start offset:

| clip | 0 s | 1 s | 2 s | 3 s | 4 s | 6 s | 8 s |
|---|---:|---:|---:|---:|---:|---:|---:|
| #44 | 0.25 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| CMU_76_02 (easy) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| BMLhandball (easy) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| KIT_3 kneel_down_to_crawl02 | 0.00 | 0.00 | 0.00 | 0.00 | 0.50 | 1.00 | 1.00 |
| BMLmovi_36_2 | 0.88 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| Eyes hamada bended_knees | 1.00 | 1.00 | 1.00 | 0.88 | 0.25 | 0.00 | 0.00 |

The whole ground family fails in its ground segments under the base policy, not just #44.

## Pre-registered endpoints

- **E1 (primary, keystone).** #44 kneel/crawl-phase survival = mean over start offsets {2, 3, 4, 6} s
  (the feasible segment per N1) rises from **0.000** (baseline s1; s2/s3 to be measured with the
  same protocol before unblinding A1) to **≥ 0.25 in both A1 seeds**. The descent-phase offsets
  {0, 1} s are reported separately and predicted to stay ≤ 0.25 (infeasible reference).
- **E2.** Matched-easy clips unchanged: CMU_76_02 and BMLhandball offset-mean survival ≥ 0.95 in
  every arm; heldout100 mean survival within ±0.03 of the uniform-mixed100 mean (no regression).
- **E3 (interaction).** A2 (adaptive on augmented): the sampler's top-1 mass (`sampling_top1_prob`
  telemetry) at iteration 2000+ is < 0.5 (versus 0.87–0.89 in adaptive-mixed100 s1–s3) and the
  top-1 clip's failure EMA falls below the bank median by the end — the attractor releases because
  the family is now learnable.
- **E4 (specificity).** A3 (random16): #44 kneel/crawl-phase survival stays < 0.10, i.e. the
  effect in E1 is not "any 16 extra clips".
- **E5.** Ground16 members' own ground-segment survival rises (training-set effect, reported, not
  a claim).

## Decision rule

Coverage is **causal for the feasible kneel/crawl phase** iff E1 holds in both keystone seeds and
E4 holds. E3 is the interaction claim (sampler collapse costs less when the attractor is
learnable) and is reported on its own. If E1 fails while E5 holds, the family is learnable but does
not generalise to #44 in 16 clips (coverage necessary, insufficient at this dose); if E1 and E5 both
fail, the family is not learnable at 4000 iterations for this policy class — either way no bank
expansion follows from N3 (v4 line).

## Frozen while N3 runs

E3 (800 bank), E10, ledger, SONIC, Featherstone/XPBD, differentiable contacts. The G1/N5 fragility
instrument work proceeds on CPU / gap capacity and does not touch training.
