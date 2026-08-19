# PhysFrag: Motion-Conditioned Physics Fragility Maps for Robust Humanoid Tracking — Plan v4

> Received from the advisor 2026-08-17 (Chinese guidance + English proposal),
> stored verbatim below. Supersedes v3 as the thesis document. v3's spike
> table survives where consistent; v2's sampler queue is FROZEN (E3/E4/E10 not
> launched) per §"最后三个动作".

---

我把你上传的 **Physics-Grounded Humanoid Tracking**、目前 Newton 的官方文档与最新 release、Newton 的 G1/ONNX 路径、SONIC 当前的三个 checkpoint 和训练配置，以及 PolySim、ASAP、SPI-Active 这些相邻工作重新放在一起看了一遍。

我很理解你为什么会有一点 lost。不是因为这个项目没有进展，而是因为你们已经同时积累了三条"看起来都能成为论文"的线：

1. motion curriculum / adaptive sampling；
2. Newton 的 multi-solver、contact、actuator 和 differentiability；
3. SONIC 的 whole-body tracking 与 sim-to-real。

每条都是真的，但三条混在一起时，研究问题就会不断扩大。你们现在最需要的不是再增加 idea，而是**删掉两层野心，把所有已有结果压缩到一个可以迅速证伪的核心问题上。**

# 我的核心判断

## **PhysFrag: Motion-Conditioned Physics Fragility Maps for Robust Humanoid Tracking**

核心 thesis：

> 一段 humanoid motion 的难度，不仅由 reference motion 的速度、加速度、接触数量等运动学特征决定，还取决于 closed-loop controller 在这段 motion 的哪些 phase 上，对 actuator、contact、timing 和 morphology mismatch 特别敏感。Newton 可以大规模测量这种 phase-local physics fragility；这种 fragility 应当比 reference-only difficulty 更能解释真实 tracking failure，并能够指导更有效的 curriculum。

> **哪些 motion、哪些 phase、因为什么物理机制而脆弱？这种脆弱性能否预测失败，并指导训练？**

# 一、当前状态比你感觉的更接近完整故事

1. 基础设施已不是主要风险（Newton 6142 tests；mjlab 对齐同版 MuJoCo Warp；10,822 clips / 43.6h 验证；三类 silent corruption；10,705-clip reference atlas）。错误数据同样能训练出"看起来合理的 reward curve"——motion pipeline 的 correctness 只能靠独立 conformance tests 和 data contracts 验证。
2. Curriculum 线已有真实发现（3/3 seeds collapse；87–89% mass 单 clip；"10% floor" 非 lower bound；grounded 修复 collapse；已反馈上游）。failure-driven curriculum 观察到"哪里失败"却不知道"为什么失败"。这条线变成新方向的训练端基础设施和 baseline。
3. **真正最宝贵的结果是 clip #44**：两 policy difficulty ρ=0.832；reference atlas 跨 policy 只有 0.567；#44 survival 0.31 vs bank 0.89；reference atlas 看似 benign。→ reference atlas 缺少的是 motion × controller × robot physics 的 closed-loop interaction。clip #44 是最好的 natural experiment，也是第一个必须通过的 feasibility gate。
4. 目前真正缺失的是 Newton-specific scientific result。

# 二、Newton 真正适合的新能力

1. **最重要的不是 solver 数量，而是可控拆分 physics stack。** MuJoCo CPU / Warp 是同一 `SolverMuJoCo` 的执行路径。MuJoCo/Featherstone 用 generalized coordinates，XPBD/SemiImplicit/Kamino 用 maximal coordinates；对 contact material、joint target、limit、control semantics 支持不同。**Raw solver disagreement 是混杂变量，不应直接称为 physics uncertainty。** multi-solver 保留但降级为 normalization 后的 model-form intervention axis。
2. **Newton 的 actuator stack 比换 solver 更值得研究**：Delay → Controller → Clamping → joint_f；PD/PID、control delay、max-effort clamp、DC-motor velocity-dependent saturation、position-dependent clamp；vectorized。`joint_target_mode` 非所有 solver 一致支持，但 `joint_f` 主要 solver 都可用。公平 cross-solver：tracker 输出 joint target → 同一 external Delay–PD–MotorClamp → effort → `joint_f` → 不同 solver。
3. **第一条最干净的 physics axis 是换 contact generation**：MuJoCo native contact；`use_mujoco_contacts=False` 用 Newton pipeline；Newton SDF；Newton hydroelastic（面接触，适合 flat foot patch、force distribution、flat-on-flat friction）。实验：(1) MuJoCo dyn + MuJoCo native contact；(2) MuJoCo dyn + Newton point/SDF；(3) MuJoCo dyn + Newton hydroelastic。
4. **Batched worlds 和 inverse dynamics 是 atlas 生产工具**（ArticulationView：M(q)、gravity、Coriolis、required effort；experimental）。Newton = batched counterfactual physics laboratory，不必成为 PPO trainer。
5. **Differentiability 现在不应成为主线。** SolverMuJoCo 不标记 differentiable；Featherstone/SemiImplicit 只有 basic。**finite-difference / paired counterfactual sensitivity 是主方法；differentiable 只是 optional spike。** batched worlds 让 ±δ 并行。

# 三、为什么不是 multi-solver training / 更多 DR / residual adaptation

- PolySim 已做 heterogeneous simulators 联合训练（G1 sim2sim + real）。novelty 不能是"train across engines"，而是"identify which motion phase is sensitive to which physical mechanism, show it predicts failure, use it to allocate training"。
- ASAP（delta action model）、SPI-Active（active SysID）已拥挤 → 后续 PhysAdapt。
- SONIC 已广泛 DR（friction/restitution/mass/CoM/joint offset/push）→ 问题不是"randomization 要不要更宽"，而是"哪个 motion phase 需要哪种 uncertainty，训练预算如何分配"。

# 四、完整研究问题

**主问题**：Can closed-loop, phase-local physics fragility explain and predict humanoid motion-tracking failures beyond reference-only motion features, and can it guide more effective robust training?

**H1**：reference features + closed-loop fragility 显著优于 reference-only（0.832 是 empirical reference 非严格 ceiling）。首要预测：**clip #44 应在 actuator/contact/timing fragility 中出现异常**。
**H2**：fragility 一部分属于 motion，一部分属于 policy。对比 Exp-1/2 trackers、grounded/uniform/adaptive checkpoints、frozen SONIC default/low-latency/v1.1（64-D token、50 Hz；default/v1.1 ~200ms lookahead，low-latency ~80ms；v1.1 加 heading normalization + wrist-pose augmentation）。
**H3**：fragility-aware curriculum 优于 failure-count curriculum。sampler unit x=(m,p,k,ℓ)；capped simplex：q_i ≥ q_min, q_i ≤ q_max, Σq_i=1（真正的 floor 和 cap）；score s_i = αF_i + βLP_i + γU_i − λE_i。

# 五、Physics fragility 定义

frozen π 跟踪 m，phase t，第 k 类干预，paired counterfactual τ^{+δ_k}, τ^{-δ_k}：

F_{m,t,k} = d(φ(τ^{+δ_k}_{m,π,t}), φ(τ^{-δ_k}_{m,π,t})) / (2δ_k + ε)

φ 是可解释指标向量（root pos/ori error；local/global body error；foot pos/ori error；stance-foot slip；foot-yaw drift；contact onset/offset；support loss；joint target–state phase lag；effort saturation；recovery time；termination risk），不是 scalar reward。

Model-form disagreement D_{m,t} = Var_{s∈S}[φ(τ^{(s)})] 是 secondary，只有统一 actuator/timestep/contact semantics 后才可解释。

**第一版 intervention family**：Actuator（command delay；variable delay/jitter；Kp/Kd scaling；torque-strength scaling；DC-motor torque-speed saturation；selected weak joint；later dead zone/motor friction）；Contact（static/dynamic/torsional friction；stiffness/damping；foot geometry；MuJoCo native vs Newton SDF；hydroelastic；small slope/height error）；Morphology/load（torso mass/CoM；limb inertia；payload；arm-position load）；Timing/sensing（obs delay；action delay；IMU bias；encoder noise；dropped/repeated obs；async timing）。

# 六、按 gate 推进

**Phase 0 — Newton conformance harness（5–7天）**：pin Newton commit/MuJoCo Warp/asset hash；joint/body ordering、quaternion、root frame、default pose；相同 initial state/dt/substep/decimation；external effort-level PD；相同 termination/metric；mjlab/MuJoCo 与 Newton/SolverMuJoCo 同一 clip。Newton `robot_policy` 的 obs 是 locomotion-style，不是 SONIC 的 encoder/history/future-reference contract；SONIC integration 必须读匹配 checkpoint 的 `observation_config.yaml`。**Gate G0**：同一 solver 下 survival、短时 trajectory、contact sequence、主要 tracking metric 在预注册 tolerance 内一致；否则后面任何 solver difference 只能算 integration error。

**Phase 1 — clip #44 decisive spike（3–4天）**：只跑 #44、2 matched easy、2 普通 hard、1 高动态但 atlas 已判定困难；只做五个 intervention：action delay、motor strength、contact friction、contact stiffness/model、torso CoM；paired worlds、common initial conditions。**Gate G1**：#44 是否在某个 mechanism 上出现明显更高 fragility、failure 前可定位的 phase-local spike、与 matched controls 不同的 signature。否定则先查 tracking reward/termination artifact、reference corruption、initialization、impossible reference、policy representation failure，不扩到 800/10,000 clips。

**Phase 2 — 200-clip PhysFrag atlas（2–3周）**：stratified（kinematic intensity；single/multi-contact；locomotion/非；upper/lower-body；easy/hard；family + mirrored pair）。预测模型对比：clip length；reference kinematics；reference ID；model-form disagreement only；structured fragility；reference+fragility。CV 按 source motion/subject/mirror pair/family 分组。**Gate G2**：Δρ ≥ 0.10 预注册；bootstrap CI 不跨零；#44 不再 unexplained；fragility peak 在失败前。通过再扩 800，最后全库。

**Phase 3 — Cross-policy 与 SONIC（1–2周）**：同一 200/800 bank：自家 trackers、frozen SONIC default/low-latency/v1.1。SONIC 重训不适合第一步（4096 envs，建议 64+ GPUs）；SONIC 作强 external benchmark，之后只做小规模 continued training/decoder fine-tuning/bounded adapter。

**Phase 4 — Fragility-aware curriculum（3–4周）**：训练留在 mjlab/Isaac Lab。对比 uniform；error-adaptive；grounded；reference-atlas curriculum；fragility-only；fragility+LP；full capped/floored mechanism-aware。matched env steps；matched physics rollout budget；3–5 seeds；realized exposure；mean + worst decile；forgetting/downward crossings；held-out physics。**Gate G3**：不 collapse；worst-decile 提升；held-out actuator/contact perturbation 提升；nominal 不显著退化。

**Phase 5 — Real G1（~2周）**：10–20 safe motions（fragility high/low；actuator/contact-sensitive；matched kinematics；部分不参与 atlas fitting）。记录 target/measured joint、IMU、timestamps、action、error flags、mocap/video。两层：predicted fragility 能否 rank 真实误差最大 motion；fragility-aware policy 是否降低 error/failure。无硬件只声称 cross-physics robustness。

# 七、第一篇保留 / 舍弃

保留：Newton–tracker/SONIC conformance harness；structured counterfactual fragility；clip #44 case study；reference atlas transfer gap；cross-policy；fragility-aware curriculum；小规模 real G1。
暂不做主贡献：full solver-ensemble PPO；full SONIC training；long-horizon differentiable G1 contact；online physics-context estimator；residual action adapter；deformable terrain/MPM；VLA。→ 第二篇 **PhysAdapt**。

# 八、Research proposal（English）

# PhysFrag: Motion-Conditioned Physics Fragility Maps for Robust Humanoid Whole-Body Tracking

## 1. Project Summary
Modern humanoid motion-tracking policies can reproduce large libraries of human motion in simulation, yet their failures remain highly motion-dependent and difficult to explain. Existing motion-difficulty models primarily describe the reference trajectory using kinematic quantities, contact schedules, or reference-frame inverse dynamics. These descriptors do not capture the closed-loop interaction among the reference motion, the controller, the robot, and imperfect physics.

We propose **PhysFrag**, a framework for measuring **motion-conditioned physics fragility**: the frame- and body-level sensitivity of a closed-loop humanoid tracker to structured changes in actuator behavior, contact mechanics, timing, and morphology. Newton provides the required experimental substrate through batched GPU worlds, composable actuator models, alternative contact-generation pipelines, multiple solver formulations, ONNX inference, and articulated-dynamics analysis.

PhysFrag will first diagnose why specific motions fail, then test whether fragility features predict held-out motion difficulty beyond reference-only descriptors, and finally use the resulting maps to construct a fragility-aware curriculum. The project will be evaluated on existing G1 tracking policies and released SONIC controllers, followed by a targeted Unitree G1 validation.

## 2. Current Evidence and Motivation
Validated bank of 10,822 G1 clips / 43.6 h; three silent failure modes corrected; reference atlas for 10,705 clips predicts within-policy difficulty out of fold; clip duration is not a useful proxy. Failure-adaptive sampler collapsed 87–89% of exposure onto one clip in 3/3 seeds and underperformed uniform; grounded sampler corrected it. Two policies rank difficulty at ρ=0.832; reference-only atlas transfers at ρ=0.567; the most prominent unexplained clip has survival 0.31 vs bank mean 0.89 despite benign reference-based dynamic features.

> The missing difficulty signal lies in the closed-loop interaction among motion phase, controller behavior, actuator dynamics, and contact physics, rather than in the reference trajectory alone.

## 3. Research Gap
PolySim (multi-simulator training) does not seek phase-local mechanism-specific explanation. ASAP (residual action correction) and SPI-Active (global SysID) do not construct a motion-conditioned map of which mechanisms are excited at each phase. Standard DR treats parameters as globally sampled nuisance; SONIC already randomizes friction, restitution, mass, CoM, joint offsets, pushes. The question is which uncertainty matters for which motion and when.

## 4. Research Questions
RQ1 Prediction: does closed-loop fragility predict held-out difficulty better than reference-only features?
RQ2 Attribution: can phase-local fragility distinguish actuator-, contact-, timing-, morphology-driven failure modes?
RQ3 Motion vs Policy: which patterns are cross-policy (motion-intrinsic) vs recipe/architecture-specific?
RQ4 Training: can a fragility-aware curriculum improve worst-case tracking and held-out-physics robustness at matched compute?
RQ5 Sim-to-Real: do simulated fragility maps predict the motions/phases with largest real G1 tracking error?

## 5. Hypotheses
H1 fragility features → significant improvement in grouped out-of-fold difficulty prediction. H2 the unexplained clip shows elevated actuator/contact/timing fragility at a localized phase. H3 rankings contain cross-policy + policy-specific components. H4 capped, coverage-preserving fragility curriculum improves worst-decile and held-out-physics without exposure collapse. H5 fragility correlates with real G1 error (foot slip, contact-timing, orientation, phase lag).

## 6. Technical Approach
6.1 Newton Conformance Harness (joint/body ordering; asset & inertials; coordinate/quaternion conventions; initial state & phase; dt & substeps; policy rate & decimation; obs normalization & history; action scale; terminations; metrics). SONIC adapter reads matching observation config (default / low-latency / v1.1; 64-D token; 50 Hz). Same-solver conformance is a hard prerequisite.
6.2 Solver-Neutral Actuation: q_target → Delay → PD → Motor Clamping → τ → `joint_f`.
6.3 Structured Interventions: actuation (delay, jitter, PD scaling, strength, effort-speed saturation, weak joints); contact (friction, stiffness/damping, foot geometry, MuJoCo native / Newton SDF / hydroelastic); morphology (mass, inertia, torso CoM, payload); timing/sensing (obs delay, IMU bias, encoder noise, packet repetition, async).
6.4 Physics Fragility Map: F_{m,t,k} = d(φ(τ^{+δ}), φ(τ^{-δ}))/(2δ+ε); φ = root pos/ori, local/global body pos, joint pos/vel, foot slip & yaw drift, contact onset/offset, support loss, target-to-state lag, effort saturation, action rate/energy, recovery time, termination probability; kept at frame/body/segment/clip level. Secondary D_{m,t} = Var_s[φ(τ^{(s)})] after actuator+contact normalization; raw solver disagreement not interpreted as real-world uncertainty without calibration.
6.5 Cross-Policy Decomposition: project checkpoints; ≥1 independent tracker; SONIC default/low-latency/v1.1. default vs low-latency → reference horizon & delay; default vs v1.1 → heading/upper-body fragility.
6.6 Fragility-Aware Curriculum: x=(m,p,k,ℓ); score combines fragility, learning progress, uncertainty, coverage, freshness, realized exposure; projected onto constrained simplex (true floor + cap). Training stays in mjlab/Isaac Lab; Newton generates priors, counterfactual evals, held-out physics. Solver-mixed training deferred.
6.7 Real-Robot Validation: 10–20 safe stratified motions; record targets, states, IMU, actions, timestamps, flags, external pose. Test: rank real error; localize phases; distinguish contact vs actuator/timing; identify motions improved. Without hardware → cross-physics robustness only.

## 7. Gates
G0 same-solver conformance (survival, short-horizon trajectory, contact sequence, metrics within pre-registered tolerance). G1 unexplained-clip test (distinct, temporally localized signature, or a concrete alternative source). G2 predictive value (200-clip; pre-registered Δρ; positive bootstrap CI). G3 cross-policy structure (stable cross-policy component generalizing to SONIC, or reproducible policy-specific component). G4 curriculum benefit (worst-decile + held-out-physics at matched compute; no collapse; nominal preserved).

## 8. Baselines
clip length; reference kinematics; reference ID; scalar failure-rate sampling; uniform; grounded; reference-atlas curriculum; uniform parameter DR; solver disagreement without structured interventions; fragility-only; fragility + LP + coverage.

## 9. Metrics
Tracking (success/survival; local/global MPJPE; root trans/ori; joint pos/vel). Contact (stance slip; foot-yaw drift; contact-state P/R; onset/offset; support loss; impact/force stats). Actuation/Timing (target-to-state lag; effort saturation; action rate/jerk; command-to-state delay; recovery). Learning (AULC; endpoint; worst-decile; held-out-physics degradation; exposure concentration; frontier crossings/forgetting). Sim-to-Real (fragility↔real error correlation; worst-motion ranking; phase-local prediction; improvement after training).

## 10. Contributions
Newton–G1 conformance harness (project trackers + SONIC); motion-conditioned fragility representation (frame/body/mechanism); motion-intrinsic vs policy-specific evidence; fragility-aware curriculum with coverage/concentration constraints; benchmark & dataset of G1 interventions + fragility maps (+ real validation); account of when solver/contact disagreement is informative.

## 11. Scope Discipline
Not depended on: end-to-end differentiable MuJoCo tracking; full SONIC training; online residual adaptation; full multi-solver PPO; MPM; VLA. Differentiable = optional spike; FD paired rollouts primary. Context estimation / bounded adaptation → follow-up.

## 12. Timeline
W1 pinning + same-solver harness + conformance. W2 unexplained-clip gate + external actuator validation. W3–5 200-clip atlas + prediction + ablations. W6–7 800-clip + cross-policy/SONIC. W8–10 curriculum. W11–12 held-out-physics + figures. W13–14 real G1 + revision.

## 13. Paper Thesis
A humanoid motion is not only a trajectory to imitate; it is also a physical experiment that excites specific aspects of the robot and its environment. By measuring how closed-loop tracking changes under structured physical interventions, PhysFrag aims to explain which motion phases are physically fragile and use that knowledge to train humanoid controllers where robustness is actually needed.

# 最后，现在只做三个动作

第一，**冻结当前扩张**：不继续铺开 E3、E4、E10，不启动 full SONIC training。
第二，**先完成 same-solver conformance**：项目 checkpoint 在 mjlab MuJoCo 与 Newton MuJoCo 中必须先一致。
第三，**立刻跑 clip #44 gate**：同一 policy、同一 initial state，只改变 delay、motor strength、friction、contact model 和 torso CoM。

> **Newton 揭示了 reference motion 看不见、但真实 controller 必须承受的 physics fragility；我们再用它改变 humanoid 的训练方式。**

References: [1] newton-physics.github.io/newton/stable/solvers/index.html · [2] .../concepts/actuators.html · [3] .../concepts/collisions.html · [4] github.com/newton-physics/newton/releases/tag/v1.5.0 · [5] .../concepts/articulations.html · [6] arXiv:2510.01708 (PolySim) · [7] arXiv:2502.01143 (ASAP) · [8] nvlabs.github.io/GR00T-WholeBodyControl/model_card.html · [9] .../user_guide/training.html
