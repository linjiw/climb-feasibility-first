# Citation check addendum — feasibility, curation, allocation, and evaluation

**Checked:** 2026-09-04. **Scope:** primary papers and official project/conference pages
needed to update the paper's nearest-neighbour positioning. This addendum extends, rather than
replaces, `paper/CITATION_CHECK_2026-08-26.md`. It is a literature audit, not a novelty guarantee.

| source | primary record checked | claim this record supports | boundary for CLIMB |
|---|---|---|---|
| H2O | [arXiv:2403.04436](https://arxiv.org/abs/2403.04436) | a privileged policy filters retargeted AMASS candidates before deployable-policy training | rules out claiming that pre-training filtering itself is new; the filter is policy-dependent |
| ExBody2 | [arXiv:2412.13196](https://arxiv.org/abs/2412.13196) | an initial policy's per-sequence tracking errors curate a feasible/diverse training subset | rules out claiming automated clip curation is new; the score mixes reference quality and policy capability |
| GMT | [arXiv:2506.14770](https://arxiv.org/abs/2506.14770) | adaptive sampling reweights motions by completion/tracking performance after rule- and policy-based curation | motivates a controlled allocation ablation after support is fixed |
| KungfuBot / PBHC | [NeurIPS 2025 paper](https://proceedings.neurips.cc/paper_files/paper/2025/file/5a0e51901cff2b42d379ec7869603e91-Paper-Conference.pdf) | a CoM–CoP stability heuristic filters human motion before robot retargeting | closest pre-training physics filter; it is applied before embodiment-specific retargeting and validated on a small selected set |
| Retargeting Matters / GMR | [arXiv:2510.02252](https://arxiv.org/abs/2510.02252) | retargeting artifacts reduce tracking robustness, especially on dynamic or long motions | supports auditing the retargeted artifact; its reported criteria are primarily kinematic |
| LIMMT | [arXiv:2606.06953](https://arxiv.org/abs/2606.06953) | motion quality includes physical feasibility, diversity, and complexity; filtering and subset selection are ablated | defeats a generic “data quality/feasibility matters” novelty claim; its score uses heuristic terms whose weights are calibrated through repeated policy training |
| Kinodynamic Motion Retargeting | [arXiv:2603.09956](https://arxiv.org/abs/2603.09956) | trajectory optimization with rigid-body and contact constraints produces dynamically viable references | shows that repair/optimization can be preferable to rejection; current scope is locomotion with synchronized force data |
| Direct Dynamic Retargeting | [arXiv:2605.23762](https://arxiv.org/abs/2605.23762) | simulator-in-the-loop MPC can bypass an infeasible geometric intermediate | prevents equating “physics-aware retargeting” with CLIMB's contribution; it addresses selected skills rather than bank-scale audit |
| YAHMP empirical study | [arXiv:2607.19903](https://arxiv.org/abs/2607.19903) | controlled Unitree G1 ablations change one training or modeling factor at a time on a fixed motion set | supports the Phase-G one-variable G2−G1 contract |
| Athena-WBC | [arXiv:2607.04837](https://arxiv.org/abs/2607.04837) | targeted exposure does not solve every feasible long-tail clip in a strong baseline; capability mismatch can remain | a null allocation result would not imply that the residual motions are intrinsically unlearnable |
| HumanTracker | [arXiv:2608.13555](https://arxiv.org/abs/2608.13555) | conventional kinematic errors can miss support/contact failures; the benchmark adds contact diagnostics and preference-aligned scoring | supports contact-aware evaluation, not the validity of CLIMB's still-unvalidated contact-timing proxy |
| ICRA 2027 call | [official call for technical papers](https://2027.ieee-icra.org/contribute/call-for-icra-2027-papers-now-accepting-submissions/) | deadline 2026-09-15 11:59 PST; eight pages total including references; double anonymous; no supplement beyond the paper and optional video | the 11.5k-word flagship source cannot be treated as an ICRA-ready manuscript |
| PaperCept manuscript support | [official LaTeX support](https://ras.papercept.net/conferences/support/tex.php) and [PDF overview](https://ras.papercept.net/conferences/support/support.php) | official `ieeeconf.cls`; US-Letter, two-column output; embedded fonts; no Type 3 fonts; pre-submission PDF test | `paper/icra/build.sh` pins the class/compiler digests and enforces page, paper-size, font, overfull-box, and citation gates locally |

## Positioning consequence

Do not claim that CLIMB is the first feasibility filter, the first physics-aware curation method,
or the first evidence that retargeting quality affects tracking. The defensible delta is narrower:
CLIMB is a low-cost, policy-independent, embodiment-specific audit of the **final retargeted robot
trajectory**. It tests whether demanded motion can be supported by admissible contacts and actuator
limits, then binds exact feasible segments to the sampler and evaluator. Its evidence contribution
is the combination of bank-scale prevalence, cross-implementation agreement, evaluation-set
contamination, segment-level routing, and a one-variable allocation experiment on identical
support.

## Remaining literature gap

The search was bounded, not exhaustive. Before submission, inspect accepted ICRA/IROS/RSS/CoRL
2025–2026 proceedings for another method that applies an analytic, policy-independent contact-force
feasibility test to already-retargeted humanoid banks at corpus scale. Absence from this scan must
not be promoted to a priority claim.
