# N7 — repair the impossible (SEALED 2026-08-20)

**Status:** sealed before any N7 training run.  The filename is retained because
earlier plans link to it.  `reports/N7/COMPLETED` does not exist at sealing.

## Question

Does contact-projection repair improve tracking relative to keeping contaminated
references, without paying the distribution-coverage cost of deleting them?
N7 tests the deployed repair policy, not whether an unrepaired motion can ever be
learned.

That distinction changed after the draft was written.  N3's augmented-uniform
arms reached descent-phase survival 1.000 and 0.688 on clip #44, falsifying the
draft prediction that unrepaired descent would remain at or below 0.25.  P-SIGN
also failed its family and control gates (7/12 and 4/12, each requiring 8/12), so
motor-strength sign disappearance is no longer a load-bearing endpoint.  Finally,
E-HYG found no one-seed benefit from blunt pruning: feasible heldout delta -0.0101
(one-sided permutation p=0.951) and feasible-ground delta -0.0354.  N7 therefore
focuses on matched-reference repair and coverage preservation.

## Frozen banks and arms

The repair operator lowers root z on airborne, unsupported frames, preserves the
joint trajectory, and recomputes linear velocity.  The built option-C bank replaces
all 99 flagged files and keeps all 800 clip names and their order.  It reduces
duration-weighted infeasibility from 3.923% to 0.903%; it is not called clean:
10 clips retain more than 5% infeasible frames and 12 require 0.15–0.44 m root
offsets.  These strata remain explicit in `reports/repaired800/manifest.json`.

| arm | bank | N | status |
|---|---|---:|---|
| K — keep | `tier_800.txt` + `bank/amass` | 800 | completed E-HYG seed 1 comparator |
| P — prune | `tier_800_pruned.txt` + `bank/amass` | 701 | completed E-HYG seed 1 operational comparator |
| R — repair | `tier_800_repaired.txt` + `bank/amass_repaired800` | 800 | one new seed-1 run |

K and R have byte-identical clip lists (SHA-256 `87cbeb8e…`), so they isolate
reference repair at fixed N, names, ordering, sampler, and compute.  R versus P is
an operational comparison, not a pure repair effect: the prune arm has 99 fewer
clips.  K versus P, already measured by E-HYG, exposes that combined deletion/N
effect rather than removing the confound by assertion.

All arms use uniform clip sampling, 4,096 environments, 4,000 iterations, seed 1,
and unchanged reward, PPO, network, and randomization.  The N7 run starts only
after the primary FGAS campaign completes and after the 14 GiB GPU headroom gate.

## Evaluation design

The 99 repaired names are frozen in `bank/tiers/tier_800_flagged99.txt`.  Final K
and R policies are crossed with both raw and repaired versions of those references:

| policy | raw references | repaired references |
|---|---|---|
| keep K | K/raw | K/repaired |
| repair R | R/raw | R/repaired |

Each cell uses offsets 0/1/2/3/4/6/8 s, eight episodes per offset, and a 3 s
window.  This separates the deployed contrast (R/repaired minus K/raw), training
transfer on unchanged references (R/raw minus K/raw), the reference-only effect
(K/repaired minus K/raw), and their policy-by-reference interaction.

Secondary evaluations use the same stratified protocol on heldout100 and
`zs_ground_feasible`.  The existing K/P CSVs remain frozen comparators; only R is
newly evaluated.

## Predictions and decision rules

1. **Primary repair benefit:** on flagged99, R/repaired minus K/raw is at least
   +0.05 survival and the fixed motion-bootstrap 95% lower bound is above zero.
2. **Training transfer (reported):** R/raw minus K/raw separates learning a better
   policy from merely evaluating an easier reference.  No threshold is imposed.
3. **No general regression:** R minus K on heldout100 is at least -0.03.
4. **Coverage preservation:** on feasible-ground zero-shot motions, R minus K is
   at least -0.03 and R minus P is at least +0.03.  This is the pre-declared place
   where repair is predicted to beat deletion.
5. **Mechanism probe only:** motor-strength perturbation may be reported on repaired
   clips, but P-SIGN's failed detector forbids using its sign as a confirmatory gate.

Overall pass requires rules 1, 3, and 4.  `tools/analyze_n7.py` freezes 20,000
motion-bootstrap draws at seed 20260820.  Because training has one seed, the
bootstrap quantifies motion uncertainty only; N7 cannot support a population-level
training claim without replication.

## Integrity and stopping

`tools/run_n7_campaign.sh` freezes its resolved config and artifact hashes, refuses
to pre-empt FGAS or another trainer, and resumes only an exact matching run.  Do not
inspect partial outcomes, retune the operator, or change thresholds after launch.
Hardware interruption permits exact-config resume; scientific underperformance
does not.  No external filing, submission, or publication is authorized.
