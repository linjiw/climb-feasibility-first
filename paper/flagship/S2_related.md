# 2. Related work

*Citation status: all 20 externally verifiable entries were checked against primary
arXiv, publisher, or project pages on 2026-08-26 (ledger: `paper/CITATION_CHECK_2026-08-26.md`).
The closest 2024–2026 feasibility, curation, allocation, and evaluation papers were rechecked on
2026-09-04 (`paper/CITATION_CHECK_2026-09-04.md`). LUCID is internal and is flagged inline rather
than counted as externally verified.*

**Adaptive sampling and prioritisation.** Prioritised experience replay ✓ [Schaul et al.,
ICLR 2016, arXiv:1511.05952] introduced loss-proportional sampling with explicit α/β corrections
for the bias it creates; Prioritised Level Replay ✓ [Jiang, Grefenstette & Rocktäschel, ICML 2021,
arXiv:2010.03934] prioritises *levels* by estimated learning potential and is explicit about
staleness and replay-vs-explore mixing. The humanoid-tracking samplers we audit are descendants of
these ideas without their safeguards: BeyondMimic ✓ [Liao et al., arXiv:2508.08241] introduced the
failure-EMA bin sampler that mjlab ✓ [Zakka et al., arXiv:2601.22074; github.com/mujocolab/mjlab]
re-implements at clip level, and both carry the additive ε/N term whose non-floor we derive in §3
(filed as mjlab #1153 and whole_body_tracking #73). Our grounded repair is the PLR-style insight —
mix on the distribution simplex, not in the score — applied to this family. Unlike the UED line,
our contribution is not a new sampler but the demonstration that in this domain the priority
signal itself conflates infeasibility, missing support, and difficulty (§5–7).
GMT [Chen et al., arXiv:2506.14770] and EGM [Yang et al., arXiv:2512.19043] provide the nearest
bank-scale alternatives: both reweight motion segments by tracking outcomes, but each combines
that allocation rule with curation, clipping or staged training, and architecture changes. Syllabus
[Sullivan et al., RLJ 2025] also reports learning-progress curricula that help early but lose to
uniform sampling asymptotically in some non-robotic domains. These results motivate, rather than
answer, our remaining one-variable question: whether calibrated learning-progress allocation adds
value after exact feasible support and the deployment prior are held fixed.

**Generalist humanoid motion tracking.** Physics-based motion imitation scaled from single-clip
policies ✓ [DeepMimic; Peng et al., TOG 2018, arXiv:1804.02717] to bank-scale controllers: PHC ✓
[Luo et al., ICCV 2023] imitates ~10k AMASS clips with fail-state recovery; MaskedMimic ✓
[Tessler et al., SIGGRAPH Asia 2024, doi:10.1145/3687951] unifies control as motion inpainting.
On hardware, the current wave — H2O ✓ [He et al., arXiv:2403.04436], OmniH2O ✓ [He et al.,
CoRL 2024, arXiv:2406.08858], ExBody ✓ [Cheng et al., RSS 2024, arXiv:2402.16796],
HumanPlus ✓ [Fu et al., CoRL 2024, arXiv:2406.10454], BeyondMimic ✓ (above), and SONIC ✓
[NVIDIA GEAR; arXiv:2511.07820,
Science Robotics 2026; 700 h of mocap, 42 M parameters] — trains trackers over ever-larger
retargeted corpora. We screen SONIC's own BONES-SEED bank in §6: it returns 0.14 %, two orders of
magnitude below our 22.8 % — though not defect-free, since seven clips do flag and five are jumps
whose box is missing from the flat scene — and that contrast is what makes prevalence a per-corpus
quantity rather than a property of the practice. Several systems already filter by policy outcome:
H2O retains motions a privileged imitator can track, while ExBody2 uses an initial policy's
per-sequence errors to select a feasible and diverse subset. Those filters are useful, but their
score mixes reference quality with the capability of the policy used to judge it. Our results are
complementary to this line, not competitive with it: the analytic screen asks a different,
controller-independent question before the sampler assigns difficulty. ASAP ✓
[He et al., RSS 2025, arXiv:2502.01143] and SPI-Active ✓ [Sobanbabu et al.,
arXiv:2505.14266] address the *dynamics* gap post-training; PolySim ✓
[arXiv:2510.01708] randomises across heterogeneous simulators during training. We descoped our
own solver-ensemble program (§10) after conformance auditing showed harness error dominates
engine disagreement at the scales involved.

**Retargeting and physical plausibility.** Contact-aware retargeting ✓ [Villegas et al.,
ICCV 2021, arXiv:2109.07431] preserves self-contacts and prevents interpenetration for character
animation; PhysCap ✓ [Shimada et al., SIGGRAPH Asia 2020, arXiv:2008.08880] and successors impose
physics on captured motion (foot-sliding, floor penetration, unnatural lean). For robots,
GMR ✓ [Ze et al., ICRA 2026, github.com/YanjieZe/GMR] and *Retargeting Matters* ✓
[arXiv:2510.02252] show retargeting choices dominate downstream tracking quality and explicitly
target foot sliding, penetration, and self-intersection. Physics-aware filtering is also prior art:
KungfuBot [Xie et al., NeurIPS 2025] applies a CoM–CoP stability heuristic before retargeting, and
LIMMT [arXiv:2606.06953] combines target-robot motion heuristics with diversity and complexity
selection, calibrating its physical-score weights through repeated policy training. Kinodynamic
Motion Retargeting [arXiv:2603.09956] and Direct Dynamic Retargeting [arXiv:2605.23762] instead
optimize dynamically viable references for selected skills. CLIMB therefore does not claim the
first feasibility filter or physics-aware retargeter. Its narrower delta is a low-cost,
policy-independent audit of the **final embodiment-specific robot trajectory**: can its demanded
wrench be supplied by admissible contacts within actuator limits? We apply that test at corpus
scale, measure evaluation contamination, and bind its exact feasible segments to the sampler and
evaluator. The screen routes references to exclusion, repair, or a scene/contact-model change; it
does not assert that screening is preferable to dynamic repair.

**Exposure auditing and evaluation methodology.** Our sealed-prediction ledger and the
stratified-start protocol follow the pre-registration norm from empirical sciences rather than a
specific robotics lineage; within robot learning, the closest practice is the reporting-hygiene
line in RL evaluation ✓ [e.g., Agarwal et al., NeurIPS 2021 "statistical precipice",
arXiv:2108.13264]. YAHMP [Amadio & Hoffman, arXiv:2607.19903] supplies a nearby Unitree G1 example
of controlled one-factor ablations on a fixed retargeted motion set. HumanTracker
[arXiv:2608.13555] shows why kinematic averages alone are insufficient, adding contact diagnostics
and a preference-aligned trajectory score; this motivates our liveness-weighted primary and
contact-timing validation, but does not validate our still-exploratory contact proxy. The companion
exposure-audit methodology (LUCID — *internal companion project,
unpublished; flagged: not externally verifiable*) studies training-exposure accounting for
sim-to-real prediction; the LUCID-correlation is this paper's one forward bridge to hardware and
carries a small-N caveat wherever cited.
