# 2. Related work

*Citation status: all 20 externally verifiable entries were checked against primary
arXiv, publisher, or project pages on 2026-08-26 (ledger: `paper/CITATION_CHECK_2026-08-26.md`).
LUCID is internal and is flagged inline rather than counted as externally verified.*

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
quantity rather than a property of the practice. All of these inherit the assumption our audit
targets: that per-clip failure rates measure difficulty. Our results are complementary to this line, not competitive with it —
the screen, the strata, and the sampler repair apply to any of these training stacks. ASAP ✓
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
target foot sliding, penetration, and self-intersection. Our feasibility screen is the missing
*dynamic* complement to these kinematic criteria: it asks not whether the pose sequence looks
clean but whether the wrench it demands can be supplied by any admissible contact forces within
actuator limits — the failure class that produced the 22.8 % prevalence we measure on one such
pipeline (and 0.14 % on another, §6) and that none of the above checks detect (a clip can have
perfect clearance and zero self-intersection while airborne at 1 g). The two systematic artifacts we document (airborne transitions from unreachable
postures; hand–hip interpenetration taxing self-collision rewards) are actionable inside any of
these retargeting pipelines.

**Exposure auditing and evaluation methodology.** Our sealed-prediction ledger and the
stratified-start protocol follow the pre-registration norm from empirical sciences rather than a
specific robotics lineage; within robot learning, the closest practice is the reporting-hygiene
line in RL evaluation ✓ [e.g., Agarwal et al., NeurIPS 2021 "statistical precipice",
arXiv:2108.13264]. The companion exposure-audit methodology (LUCID — *internal companion project,
unpublished; flagged: not externally verifiable*) studies training-exposure accounting for
sim-to-real prediction; the LUCID-correlation is this paper's one forward bridge to hardware and
carries a small-N caveat wherever cited.
