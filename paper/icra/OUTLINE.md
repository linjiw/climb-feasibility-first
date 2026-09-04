# Feasibility First — ICRA 2027 manuscript outline

**Status:** unsealed writing scaffold, 2026-09-04. This file contains no new result and does
not authorize endpoint access. Phase-G cells remain conditional on the calibration,
independent-validation, seal, manipulation, and provenance gates.

## Paper contract

**Working title:** *Feasibility First: Auditing Reference Dynamics Before Adaptive Humanoid
Motion Tracking*

**Operational bottleneck.** A failure-adaptive sampler can assign increasing training exposure
to a motion that the robot cannot realize under the modeled contacts and actuator limits. In
that case, policy error is not evidence of controllable difficulty, and sampling it more often
does not isolate the allocation problem.

**Narrow claim.** On the tested AMASS-to-`whole_body_tracking`-to-Unitree-G1 pipeline, an
analytic robot-space screen identifies dynamically infeasible reference intervals before
policy training; an exact-support trial contract then separates reference feasibility from the
still-open effect of adaptive allocation.

The claim is deliberately about one retargeting pipeline and one modeled embodiment. It is not
a generic prevalence claim, a hardware-safety guarantee, or evidence that filtering improves
policy performance.

**Contribution list.** Keep these three noun-phrase contributions and use the same comparison
classes in the result tables.

1. **A measured failure diagnosis and policy-independent screen:** the collapse trace is tied
   to an unsupported reference interval, and the screen reports 2,442 of 10,705 clips above the
   fixed infeasible-frame threshold on the primary pipeline.
2. **An exact-support trial contract:** feasible intervals, full-horizon legal starts, stable
   attribution units, fixed terminals, paired conditions, and content hashes produce 1,184
   training units with 368,951 legal starts plus a name- and hash-disjoint 100-clip evaluation
   panel.
3. **A controlled allocation test:** calibrated learning-progress allocation versus
   deployment-uniform allocation on identical support, reported only if every predeclared gate
   passes; otherwise the paper reports `not_tested` rather than an endpoint estimate.

Contribution 3 becomes an empirical result only after Phase G is complete. If Phase G cannot
be completed, rename it “a preregistered controlled allocation protocol” in the abstract,
introduction, and conclusion.

## Abstract skeleton — seven sentences, about 175 words

1. **Ground:** Failure-adaptive sampling is intended to concentrate humanoid tracking updates
   on motions the policy has not mastered.
2. **Gap:** Policy error, however, can conflate controllable difficulty with a reference that
   demands unsupported or over-limit robot dynamics.
3. **Observed consequence:** In one three-seed training campaign, this conflation coincided
   with concentrated exposure and a shared attractor, motivating an audit that does not require
   a trained policy.
4. **Method:** Introduce the contact-capacity and actuator-limit screen, then state its inputs,
   outputs, and assumptions in one sentence.
5. **Interface:** Explain that feasible intervals are converted into exact full-horizon starts
   and stable attribution units so allocation rules consume identical support.
6. **Measured setup/result:** Report the primary 10,705-clip count together with the separate
   4,950-clip production-bank result, explicitly stating that the prevalence difference is a
   corpus-and-pipeline measurement.
7. **Controlled outcome:** Replace this sentence with exactly one Phase-G branch—`positive`,
   `null`, `inconclusive`, or `not_tested`—and include the comparator, independent unit, primary
   metric, estimate, interval, and scope.

Do not use “first,” “novel,” “safe,” “general,” “significantly,” or “outperforms” unless the
final evidence licenses the word under `paper/PHASE_G_RESULT_TABLE_SHELL.md`.

## Page and argument map

### 1. Introduction — 1.0 page

**Paragraph 1: concede the capability.** Large retargeted motion banks and adaptive curricula
expand humanoid tracking coverage. Credit policy-based filtering, physics-aware curation, and
adaptive allocation before naming their different information requirements.

**Paragraph 2: turn to the physical gap.** State three limitations as an auditable list:

- **L1 — error ambiguity:** tracking error mixes policy competence with reference infeasibility;
- **L2 — support ambiguity:** clip-level selection changes legal-start exposure and can include
  invalid full-horizon starts;
- **L3 — evaluation ambiguity:** resets, wraparound, and unstable attribution can turn terminal
  failures into mislabeled observations.

**Paragraph 3: reproduce the consequence.** Use the shared three-seed attractor and the traced
unsupported interval as the hook. Present the causal explanation as a diagnosis for this
pipeline, not a universal theory of sampler collapse.

**Paragraph 4: hinge at Fig. 1.** Introduce the robot-space screen and exact-support interface.
The figure must show the failure situation and the changed experimental interface, not a module
inventory.

**Paragraph 5: contributions.** Use the three-item list above. End with the decisive question:
after feasibility and exposure are held exact, does learning-progress allocation improve
feasible-hard tracking?

### 2. Related work — 0.6 page

Organize by the three ingredients rather than by chronology.

1. **Motion curation and feasibility.** Credit H2O/ExBody2 policy filters, KungfuBot's human-space
   heuristic, LIMMT's training-calibrated score, and kinodynamic/dynamic retargeting. Delta:
   this paper audits the final robot-space reference analytically and routes existing data; it
   does not claim that exclusion is preferable to repair.
2. **Adaptive motion allocation.** Credit BeyondMimic, GMT, and EGM. Delta: their results do not
   isolate this learning-progress rule after the legal-start prior and feasible support are
   fixed.
3. **Support-aware evaluation.** Credit contact- and support-aware tracking evaluation. Delta:
   this paper fixes full-horizon starts, terminal semantics, attribution units, and provenance;
   its contact-timing measure remains explicitly exploratory unless separately validated.

Every nearest-neighbor sentence must follow credit → required information → physical boundary →
this paper's changed interface. Use `paper/CITATION_CHECK_2026-09-04.md` as the citation ledger.

### 3. Screen and exact-support interface — 1.5 pages

#### 3.1 Problem and assumptions

Define the reference state, modeled contacts, actuator limits, horizon, and output label. List
the validity conditions beside the method: the MuJoCo G1 model, flat ground, fixed friction and
contact geometry, prescribed reference kinematics, and no claim about unmodeled electrical or
thermal limits.

#### 3.2 Dynamic-feasibility screen

Specify inputs and outputs before equations. Present the contact-capacity residual, support
test, actuator-limit test, gap/weight thresholds, aggregation into `infeasible_frac`, and the
strict clip threshold. Separate ballistic flight from unsupported hovering. State CPU cost in
the paragraph that claims bank-scale applicability.

#### 3.3 Exact-support trial contract

Map L1–L3 to the corresponding intervention: feasible frame intervals, exact 50-step windows,
legal-start mass, stable segment units, fixed non-wrapping terminals, paired evaluator
conditions, and SHA-256-bound inputs. State what stays identical between G1 and G2: embodiment,
task, PPO, reward, support, legal-start prior, caps, compute, seeds, and evaluator.

### 4. Experimental design — 1.0 page

Organize the section by questions, not implementation chronology.

- **RQ1 — Does the motivating failure occur?** Three training seeds; exposure concentration,
  shared attractor, and the traced motion's physical demand.
- **RQ2 — What does the screen measure at bank scale?** Primary 10,705-clip pipeline, separate
  4,950-clip production bank, and the 40-clip cross-implementation agreement panel. Never pool
  their prevalence estimates.
- **RQ3 — Does screening alone imply a training benefit?** Report the E-HYG null and failed
  FGAS manipulation gate as counterevidence; they motivate, but do not substitute for, the
  controlled allocation test.
- **RQ4 — Does ALP help on identical feasible support?** G2 versus G1, three seeds if budget
  permits, 100 disjoint evaluation clips, 2,800 paired conditions, and the exact gates in the
  frozen table shell.

Name the independent unit with every inferential claim. Frames are measurements, not independent
replicates. For Phase G the primary unit is clip within training seed under a seed-then-clip
hierarchical bootstrap.

### 5. Results — 2.4 pages

#### 5.1 Failure-adaptive exposure can lock onto a reference defect

Use one compact figure and one paragraph: peak/mean top-1 exposure, the shared-attractor count,
and the unsupported-demand anatomy. Include the strongest alternative explanation still open.

#### 5.2 Infeasibility prevalence is pipeline-dependent

Print raw counts and denominators: 2,442/10,705 on the primary pipeline and 7/4,950 on the
separate production pairing. Add the cross-implementation agreement row (39/40 strict decisions,
with the single disagreement named in the text). The result licenses a screen and a pipeline
measurement, not a generic rate for retargeted motion.

#### 5.3 Obvious interventions do not establish the allocation claim

Lead with counterevidence: E-HYG's held-out effect is −0.0101 with its predeclared test, the
soft-FGAS allocation gate fails, and the segment-native pilot reaches only 0.014 total
variation. These results rule out using prior filtering or weak-treatment runs as evidence that
allocation helps.

#### 5.4 Controlled Phase-G result

Copy topology, definitions, and decision language from
`paper/PHASE_G_RESULT_TABLE_SHELL.md`. Do not compress a manipulation or provenance failure into
a performance result. If the gate passes, report the feasible-hard TrackingScore estimate and
95% interval first, then survival and common-survivor non-harm. Print the losing subgroup or
null secondary beside any positive aggregate.

### 6. Limitations and conclusion — 0.7 page

Use a headed limitations paragraph. At minimum retain:

- one robot and simulator model, with no hardware closed-loop validation;
- one primary retargeting pipeline, with the cross-bank result treated as a boundary rather than
  a causal retargeter comparison;
- modeled contact and actuator limits rather than an electrical, thermal, or safety certificate;
- training-seed uncertainty and any budget-triggered seed-3 omission;
- analytic routing does not establish that exclusion beats repair;
- contact timing stays a kinematic proxy unless its held-out instrument gate passes.

Close with the narrow measured contribution. The generative limitation sentence should be:
“The observation that would settle whether screening should exclude or repair a reference is a
same-support, same-policy comparison of certified repaired and excluded intervals with actuator
and contact consequences measured under the same trial contract.”

### References — 0.8 page

Retain only citations that perform one of four jobs: establish the adaptive-sampling assumption,
define the nearest filtering/retargeting alternative, support the task/evaluator contract, or
identify the underlying dataset/platform. Do not spend reference space documenting experiments
that are omitted from the short paper.

## Figures and tables

| object | job | source | non-claim |
|---|---|---|---|
| Fig. 1 | hook-scenario plus mechanism contrast: concentrated exposure on an unsupported interval → analytic screen → identical-support allocation test | `paper/figures/f1_feasibility_first.py` → `.png/.pdf`; measured panel from `reports/N1_clip44_knee_id.json` | not a full software architecture and not evidence that G2 wins |
| Fig. 2 | bank-scale count with the primary and production pipelines visually separated; include 40-clip implementation agreement | `reports/feasibility_all/`, `reports/feasibility_sonic/`, `reports/feasibility_xcheck/` | not a causal comparison of retargeters |
| Fig. 3 | Phase-G primary estimate and declared secondaries, or a gate-failure diagram if `not_tested` | `paper/PHASE_G_RESULT_TABLE_SHELL.md` and future sealed result | no endpoint panel if manipulation/provenance fails |
| Table 1 | screen definition, assumptions, thresholds, cost, and raw denominators | `reports/feasibility_all/`, `reports/feasibility_sonic/` | thresholds are design choices, not discovered constants |
| Table 2 | Phase-G manipulation, primary contrast, survival, and common-survivor safeguards | frozen G tables | exactly one exhaustive status |

The captions must state the denominator, setting, conditioning subset, and what the object does
not establish. No visual should mix simulation, offline kinematic screening, and hardware tiers
in one unqualified axis.

## Claim–evidence map

| claim | evidence and unit | exact source | strongest allowed wording |
|---|---|---|---|
| Adaptive exposure concentrated around a shared attractor in the motivating campaign | three seeds per arm; sampler ledgers | `reports/A5_coverage_dose.json`, `reports/A7_attractor.json` | “coincided with” unless the non-floor mechanism is isolated in the cited comparison |
| The traced attractor contains unsupported reference demand | hash-bound clip anatomy; frames are measurements | `reports/N1_clip44_knee_id.json`, `plan/N1_RESULT.md` | “the modeled contacts supply no admissible source during the identified interval” |
| The primary screen flags 2,442/10,705 clips | clips in one AMASS→WBT→G1 pipeline | `reports/feasibility_all/feasibility.csv`, `paper/RESULTS_LOG.md` | a pipeline-scoped prevalence measurement |
| The production pairing flags 7/4,950 clips | clips in one BONES-SEED→SONIC pairing | `reports/feasibility_sonic/hygiene_screen.csv` | a separate pipeline measurement; never an ablation |
| Two implementations agree on 39/40 strict decisions | stratified 40-clip panel | `reports/feasibility_xcheck/summary.json` | cross-implementation agreement on the selected panel |
| Exact support contains 1,184 units and 368,951 legal starts | units and starts in the frozen table | `reports/g_segment/unit_table.json` | an apparatus/property claim, not policy benefit |
| Filtering alone improves tracking | E-HYG sealed null | `reports/E_HYG_result.json`, `plan/E_HYG_RESULT.md` | prohibited; report the −0.0101 null instead |
| Learning-progress allocation changes exposure and improves tracking | pending calibration and Phase G | future hash-bound calibration/result artifacts | only the exhaustive Phase-G branch licenses prose |

## Material to omit from the eight-page spine

Keep Newton predictive screening, DFRP qualification detail, P-SIGN, N5 instrument calibration,
the full support-atlas analysis, historical conformance forks, and repair-census strata in the
long-form source or repository. Mention one only when it closes a specific reviewer alternative
that the main result cannot close. Omission is scope control, not withdrawal of the underlying
artifact.

## Strongest-sentence audit

**Allowed before Phase G:**

> On the tested AMASS-to-`whole_body_tracking`-to-Unitree-G1 pipeline, the analytic screen flags
> 2,442 of 10,705 retargeted clips above the fixed infeasible-frame threshold; a separately
> implemented screen on a different 4,950-clip production pairing flags 7 clips, so prevalence
> remains a corpus-and-pipeline measurement rather than a generic rate for retargeted motion.

**Reserved for a passed Phase-G gate:**

> Under the exact 1,184-unit support and paired 100-clip evaluation contract, calibrated
> learning-progress allocation changed feasible-hard TrackingScore by `[estimate, 95% CI]`
> relative to deployment-uniform allocation across `[number]` training seeds.

The final abstract and conclusion must use the same Phase-G status and interval. A null, failed
manipulation, or missing seed cannot disappear at either boundary.
