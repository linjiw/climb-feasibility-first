# Paper completion checkpoint — ICRA-sized claim, RSS-scale source

**Date:** 2026-09-04
**Status:** unsealed writing and execution plan. This file changes no sealed result and authorizes
no confirmatory run before the Phase-G seal.

## Decision and goal

The immediate paper goal is an **eight-page, result-complete ICRA 2027 manuscript** whose central
claim is narrow enough for the existing tables to hold:

> Failure-adaptive humanoid motion tracking can spend training on reference defects rather than
> controllable difficulty; a policy-independent dynamic-feasibility audit and exact-support trial
> contract separate that failure class from the remaining allocation question.

The 11.5k-word flagship remains the RSS-scale source of record. It is not the ICRA draft. The
[official ICRA 2027 call](https://2027.ieee-icra.org/contribute/call-for-icra-2027-papers-now-accepting-submissions/)
sets the paper deadline at **2026-09-15 11:59 PST**, limits the complete paper to **eight pages
including references**, uses double-anonymous review, and permits no paper supplement beyond an
optional video. This creates a hard scope constraint, not permission to write pending outcomes as
results.

## Operational bottleneck

The scientific design is ready; the exact motion payload is not. Phase-G calibration requires the
800 hash-bound training motions, and full confirmation requires those 800 plus the 100 disjoint
evaluation motions. No aggregate or sidecar in this checkout reconstructs the missing trajectories.
Substituting a different retarget would change the experimental substrate and confound the only
intended variable, G2 versus G1 allocation.

The writing bottleneck is equally concrete: the flagship currently carries too many experiments,
four broad contributions, and an outdated nearest-neighbour claim. Recent work already establishes
policy-based feasibility filtering, physics-aware curation, adaptive sampling, and dynamically
constrained retargeting. CLIMB must claim its narrower delta rather than priority over those classes.

## Provisional contribution statement

1. **A failure diagnosis and screen.** A traced sampler-collapse case links a non-floor exposure
   rule to an embodiment-specific reference whose demanded wrench has no admissible contact source;
   the policy-independent screen is then measured at bank scale, with cross-bank and
   cross-implementation boundaries reported.
2. **An exact-support trial contract.** Feasible frame intervals, full-horizon legal starts, fixed
   terminals, stable attribution units, paired seeds/initial states, and hash-complete provenance
   turn the screen into a reproducible sampler/evaluator interface.
3. **A controlled allocation result.** G2 ALP versus G1 deployment-uniform on identical support,
   included only if calibration, independent validation, sealing, manipulation, and provenance
   gates all pass. A positive, bounded null, inconclusive, and not-tested result are equally
   reportable.

These are contribution types—diagnosis, instrument, controlled test—not three names for one
pipeline. If Phase G is unavailable, contribution 3 remains a protocol and cannot be advertised as
an empirical allocation result.

## Nearest alternatives and the exact delta

The updated primary-source ledger is `paper/CITATION_CHECK_2026-09-04.md`.

- H2O and ExBody2 curate with an initial tracker; CLIMB's screen does not require a trained policy.
- KungfuBot filters human motion with a CoM–CoP heuristic before robot retargeting; CLIMB audits the
  final robot-space trajectory against embodiment-specific contacts and actuator limits.
- LIMMT defines feasibility, diversity, and complexity and calibrates a heuristic physical score
  through repeated training; CLIMB's feasibility gate is analytic and precedes outcome-based
  weighting.
- Kinodynamic and direct dynamic retargeting optimize viable references; CLIMB diagnoses and routes
  existing banks without claiming that exclusion is preferable to repair.
- BeyondMimic, GMT, and EGM motivate adaptive allocation but do not answer whether this ALP rule
  beats uniform allocation after exact support is fixed.
- HumanTracker motivates contact- and support-aware evaluation; it does not validate CLIMB's
  contact-timing proxy, which stays exploratory until the blinded held-out gate passes.

## Phase-G experiment card

| field | frozen direction |
|---|---|
| scientific question | Does calibrated ALP allocation help after feasibility/support are held exact? |
| changed variable | G2 ALP allocation versus G1 deployment-uniform allocation |
| held fixed | Unitree G1, task, PPO, reward, exact 50-step support, legal-start prior, caps, compute, seeds, and paired evaluator |
| support | 1,184 attribution units and 368,951 legal starts; identical between arms |
| evaluation | 100 name- and hash-disjoint clips / 2,800 paired conditions; primary reference-hard stratum fixed without policy outcomes |
| independent unit | clip within training seed, resampled by a seed-then-clip hierarchical bootstrap |
| primary endpoint | feasible-hard liveness-weighted TrackingScore, G2−G1, SESOI +0.02 |
| manipulation | mean TV `[0.05, 0.15]`, effective units ≥12, top-1 ≤0.05, zero invalid/censored mass, saturation <0.90 |
| interpretation | this calibrated ALP treatment only; not ALP generally and not the benefit of support hygiene |

Before sealing, retain the **exploratory-only** sampler diagnostic now added to the ledgers:
Spearman rank agreement among ALP, conditional failure, and `p(1-p)` competence-frontier scores at
the declared checkpoints. It receives no decision threshold, adds no training arm, and cannot alter
the confirmatory verdict. The diagnostic tests whether G2 reallocates toward changing competence or
merely reconstructs a failure rank.

## Results table before results

Keep `paper/PHASE_G_RESULT_TABLE_SHELL.md` unchanged in topology after the 2026-09-04
rank-agreement row was added. It now forces:

- every calibration candidate and the independent validation row;
- seed identity and full evaluation provenance before endpoint parsing;
- primary, survival, all-panel, and AULC contrasts;
- common-survivor denominators and non-harm margins;
- contact-timing validation separate from policy results; and
- exactly one exhaustive Phase-G status; and
- checkpoint-level ALP/failure/competence-frontier agreement with no decision role.

Do not add another comparison after reading endpoints.

## Internal schedule and stop rules

| date | deliverable | stop rule |
|---|---|---|
| Sep 4–5 | publish corrected project page; update related work and eight-page outline | no “first feasibility filter” or generic “data quality matters” claim remains |
| Sep 5–6 | exact payload intake and hash verification | if 800 files fail identity, calibration does not run |
| Sep 6–7 | 12-setting endpoint-blind calibration plus independent validation | failed validation returns Phase G to design; do not choose the next row using endpoints |
| Sep 7–8 | contact-proxy disposition, 512-env footprint, rank diagnostic, final contract review, seal | any unresolved must be frozen as exploratory/omitted; no endpoint access |
| Sep 8–10 | three-seed G1/G2 confirmation, paired evaluation, frozen analysis | manipulation/provenance failure produces `not_tested` |
| Sep 10 | internal result and figure freeze | no new confirmatory hypothesis after this point |
| Sep 10–14 | compress to eight pages, render, arithmetic/citation/anonymity audit | every abstract/conclusion number must trace to one printed cell |
| Sep 15 | author submission decision and upload | no submission claim without a verified PDF and author approval |

If the payload is still absent at the Sep 6 intake gate, stop treating ICRA Phase G as the critical
path. Finish the screen/benchmark manuscript from measured evidence or carry the full integrated
paper to RSS 2027. Do not replace the exact bank, waive the seal, reduce the manipulation gate, or
write a proposed outcome in past tense to preserve a deadline.

## Eight-page manuscript allocation

| section | target pages | job |
|---|---:|---|
| Abstract + Introduction | 1.0 | operational failure, exact delta, three bounded contributions |
| Related work | 0.6 | credit policy filters, physics filters/retargeting, adaptive allocation, evaluation |
| Screen and exact-support interface | 1.5 | inputs/outputs, assumptions, contact-capacity test, segment/trial contract |
| Experimental design | 1.0 | banks, splits, units, comparators, gates, provenance |
| Results | 2.4 | collapse/anatomy, bank-scale screen, harness/pilot, Phase G if complete |
| Limitations + Conclusion | 0.7 | corpus/pipeline confounds, simulation scope, policy-seed uncertainty, next discriminating test |
| References | 0.8 | complete within the eight-page cap |

Figure 1 should show the failure scenario and the changed interface, not the full software
architecture. The main result table must include raw denominators and a losing/null subgroup. The
full seal ledger and historical probes belong in the public repository/long-form source, not in the
eight-page causal spine.

## Strongest-sentence audit

Allowed now:

> On this AMASS→whole_body_tracking→Unitree G1 flat-ground pairing, the analytic screen flags
> 2,442 of 10,705 retargeted clips above the fixed infeasible-frame threshold; an independently
> implemented screen on a different 4,950-clip production pairing flags 7 clips, so prevalence is
> a corpus-and-pipeline measurement rather than a generic rate for retargeted data.

Not allowed now:

- “CLIMB is the first physics feasibility filter.”
- “Feasibility filtering improves policy performance” from E-HYG's sealed null.
- “ALP improves robust tracking” before Phase G.
- “The contact proxy measures true contact timing” before held-out validation.
- “The references are unsafe/destructive” without validated electrical/thermal hardware evidence.

The observation that settles the allocation question is the sealed, passed-manipulation G2−G1
TrackingScore interval. The observation that settles the contact-metric question is the held-out
proxy-versus-consensus event score. Everything else is motivation or limitation, not a substitute.
