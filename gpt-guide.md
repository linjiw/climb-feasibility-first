我把你上传的 **Physics-Grounded Humanoid Tracking**、目前 Newton 的官方文档与最新 release、Newton 的 G1/ONNX 路径、SONIC 当前的三个 checkpoint 和训练配置，以及 PolySim、ASAP、SPI-Active 这些相邻工作重新放在一起看了一遍。

我很理解你为什么会有一点 lost。不是因为这个项目没有进展，而是因为你们已经同时积累了三条“看起来都能成为论文”的线：

1. motion curriculum / adaptive sampling；
2. Newton 的 multi-solver、contact、actuator 和 differentiability；
3. SONIC 的 whole-body tracking 与 sim-to-real。

每条都是真的，但三条混在一起时，研究问题就会不断扩大：一会儿像 curriculum paper，一会儿像 simulator paper，一会儿又像 system identification 或 policy adaptation paper。你们现在最需要的不是再增加 idea，而是**删掉两层野心，把所有已有结果压缩到一个可以迅速证伪的核心问题上。**

# 我的核心判断

**我最推荐的方向是：**

## **PhysFrag: Motion-Conditioned Physics Fragility Maps for Robust Humanoid Tracking**

它的核心 thesis 是：

> 一段 humanoid motion 的难度，不仅由 reference motion 的速度、加速度、接触数量等运动学特征决定，还取决于 closed-loop controller 在这段 motion 的哪些 phase 上，对 actuator、contact、timing 和 morphology mismatch 特别敏感。Newton 可以大规模测量这种 phase-local physics fragility；这种 fragility 应当比 reference-only difficulty 更能解释真实 tracking failure，并能够指导更有效的 curriculum。

这不是简单的“把 SONIC 放进 Newton”，也不是“多随机几个参数”，更不是“换几个 solver 看谁更好”。它是一个比较清楚的科学问题：

> **哪些 motion、哪些 phase、因为什么物理机制而脆弱？这种脆弱性能否预测失败，并指导训练？**

---

# 一、你们目前的研究状态，其实比你感觉的更接近一个完整故事

## 1. 基础设施已经不是主要风险

你们已经完成了相当扎实、而且很容易被低估的 enabling work：

* Newton 安装并通过了 6142 个测试；
* mjlab 被重新构建并和 Newton 对齐到同一版 MuJoCo Warp；
* 10,822 个 G1 motion、43.6 小时数据完成验证；
* 发现并修复了 breadth-first body order、混合帧率和 root-height representation 三类 silent corruption；
* 10,705 个 clip 已经有 reference-based physics atlas。

这些并不是“前期杂活”。尤其是你们发现错误数据同样能训练出“看起来合理的 reward curve”，这件事对 humanoid motion learning 很重要：它证明 motion pipeline 的 correctness 不能靠 training convergence 验证，只能靠独立的 conformance tests 和 data contracts 验证。

换句话说，你们已经具备做严谨 benchmark 和 controlled experiment 的基础，而不是从零开始。

## 2. Curriculum 线已经有真实研究发现

目前 sampler 相关结果并不失败：

* error-adaptive sampler 在 3/3 seeds 中失败；
* 87–89% 的 sampling mass 集中在一个 clip 上；
* 所谓“10% uniform floor”在数学上并不是真正的 lower bound；
* grounded arm 修复了 collapse，AULC 接近 uniform，endpoint 略优；
* 相同或相近的问题已经反馈给上游项目。

这是一条可以独立存在的 sampling/curriculum 研究线。它说明：

> 当前 failure-driven curriculum 观察到的是“哪里失败”，却不知道“为什么失败”，所以容易把所有资源投入一个不可学、不可辨识或因建模缺陷而失败的 attractor。

你们过去的工作不是要丢掉，而是应该变成新方向的**训练端基础设施和重要 baseline**。

## 3. 真正最宝贵的结果是 clip #44

你们的文档里最重要的并不是某个 sampler 最终高了几个点，而是这一组矛盾：

* 两个独立 policy 对 motion difficulty 的排序相关性达到 ( \rho=0.832 )，说明“这段 motion 对 G1 有多难”具有相当稳定的内在结构；
* reference-only atlas 跨 policy 的相关性只有 ( \rho=0.567 )；
* clip #44 的 survival 只有 0.31，bank mean 是 0.89；
* 但它的 reference atlas 看起来非常 benign：低动态指标、低 peak GRF。

这意味着 reference kinematics 和 reference-frame inverse dynamics 没有捕捉到真正使它困难的东西。

这就是整篇论文最自然的入口：

> **reference atlas 缺少的不是更多 motion features，而是 motion × controller × robot physics 的 closed-loop interaction。**

clip #44 不是一个令人烦恼的异常点。它是你们最好的 natural experiment，也是第一个必须通过的 feasibility gate。

## 4. 目前真正缺失的是 Newton-specific scientific result

你们自己的 retrospective 对这一点判断得非常诚实：此前 Newton 主要只是安装好了、跑了 G1 example，并作为底层 substrate 或 raw MuJoCo inverse-dynamics 路径存在；真正的研究问题仍然都在 mjlab 内完成，因此 sampler 结果并不依赖 Newton。

这种承认其实是进步。很多项目会因为不愿意承认 drift，继续堆实验，最后既不是 Newton paper，也不是 curriculum paper。你们现在已经能够准确看到问题，所以接下来只需要完成一次明确 redirect。

---

# 二、Newton 到底有哪些真正适合这个项目的新能力

Newton 的官方定位是基于 NVIDIA Warp 的 GPU physics engine，以 MuJoCo Warp 为主要 backend，强调 GPU scaling、OpenUSD、differentiability 和 extensibility。

但对你们而言，并不是每一个 feature 都同等有价值。

## 1. 最重要的不是“solver 数量”，而是可控地拆分 physics stack

你们当前文档写了“nine solvers under one Model”。更准确的说法是，当前官方文档列出八类 solver implementation；MuJoCo CPU 和 MuJoCo Warp 是同一个 `SolverMuJoCo` 下的不同执行路径，而不是两个完全独立的物理模型。更重要的是，不同 solver 并不只是在“同一问题上换了算法”：MuJoCo 和 Featherstone 使用 generalized coordinates，而 XPBD、SemiImplicit 和 Kamino 使用 maximal coordinates；它们对 contact material、joint target、limit 和 control semantics 的支持也不完全相同。([牛顿物理][1])

因此，下面这个推理是不够严谨的：

> solver A 和 solver B 轨迹不同
> → 这段 motion 存在 real-world physics uncertainty。

轨迹差异可能同时来自：

* coordinate representation；
* actuator semantics；
* contact generation；
* contact stiffness interpretation；
* joint limits 是否被 enforce；
* integrator；
* solver convergence；
* timestep 和 substep。

**Raw solver disagreement 是混杂变量，不应该直接被称为 physics uncertainty。**

这也是我对当前 PDF 里 Thrust 1 最重要的修改：保留 multi-solver，但把它从“主定义”降级为经过 normalization 后的 **model-form intervention axis**。

## 2. Newton 新的 actuator stack 比单纯换 solver 更值得研究

Newton 的 actuator API 提供可组合的：

[
\text{Delay}
\rightarrow
\text{Controller}
\rightarrow
\text{Clamping}
\rightarrow
\texttt{joint_f}.
]

其中包括 PD/PID、control delay、maximum-effort clamp、DC-motor velocity-dependent saturation 和 position-dependent clamp，并且是 vectorized、适合 batched RL world 的。([牛顿物理][2])

这对 G1 sim-to-real 非常关键，因为实际 tracking gap 往往不是“质量差了 10%”那么简单，而是：

* command latency；
* variable latency / jitter；
* PD gain mismatch；
* torque saturation；
* torque-speed envelope；
* joint-specific motor weakness；
* dead zone；
* unmodeled friction；
* asynchronous state and action timing。

Newton 目前的 actuator API 还没有完整 transmission、thermal dynamics 和 motor friction model，所以不能把它宣传成完整 real motor digital twin；但它给了你们一个清晰、可扩展的 actuator intervention layer。([牛顿物理][2])

更重要的是，Newton 的 solver feature matrix 显示 `joint_target_mode` 并不是所有 solver 都一致支持，但 `joint_f` 在主要 articulated/rigid solvers 中都可以使用。([牛顿物理][1])

所以公平的 cross-solver 实验应该是：

> SONIC 或 tracker 输出 joint target
> → 统一经过同一个 external Delay–PD–MotorClamp
> → 统一生成 effort
> → 写入 `joint_f`
> → 再交给不同 solver。

这样 solver difference 才不会被不同 native servo implementation 污染。这可以成为你们 harness 中一个很有价值的方法学贡献。

## 3. 第一条最干净的 physics axis 不是换 solver，而是换 contact generation

`SolverMuJoCo` 可以：

* 使用 MuJoCo 自己的 native contact；
* 或保持 MuJoCo integrator 不变，把 `use_mujoco_contacts=False`，改用 Newton collision pipeline；
* Newton pipeline 进一步支持 SDF 和 hydroelastic contact。

Hydroelastic contact 不是单个 contact point，而是带面积和分布的 contact representation，更适合表达 large flat contact patch、force distribution 和 flat-on-flat friction。([牛顿物理][3])

这提供了一个比“MuJoCo 对 XPBD”更干净的第一组实验：

1. MuJoCo dynamics + MuJoCo native contacts；
2. MuJoCo dynamics + Newton point/SDF contacts；
3. MuJoCo dynamics + Newton hydroelastic contacts。

这里 integrator 和 generalized-coordinate dynamics 保持相对一致，主要改变 contact representation。对 G1 的 stance foot、pivot、heel-to-toe transition、foot yaw 和 slip，这是更可解释的实验。

## 4. Batched worlds 和 inverse dynamics 是 atlas 生产工具

Newton 1.5 的相关更新包括 vectorized joint-space impedance control、更好的 multi-world reset/initialization、contact correctness 与 persistence，以及更可靠的 USD/MJCF import；G1 和 humanoid replicated workloads 的初始化也得到改进。([GitHub][4])

同时，`ArticulationView` 和 inverse-dynamics API 可以批量得到：

* mass matrix (M(q))；
* gravity force；
* Coriolis/centrifugal force；
* required joint effort。

这些 API 仍然被标为 experimental，但非常适合生成解释性 features，而不应当作为训练稳定性的单点依赖。([牛顿物理][5])

换句话说，Newton 很适合成为：

> **batched counterfactual physics laboratory**

而不必立刻成为你们完整的 PPO trainer。

## 5. Differentiability 现在不应该成为主线

这是我对当前 proposal 最明确的一处纠偏。

你们 PDF 里的 Thrust 3 希望通过 `wp.Tape` 对 MuJoCo/Featherstone 的 G1 tracking 求 friction、contact stiffness 等梯度，并把它作为主要方向之一。

但当前官方 solver matrix 中：

* `SolverMuJoCo` 不标记为 differentiable；
* Featherstone 和 SemiImplicit 只有 basic differentiability；
* 官方示例主要是较简单的 DiffSim workflow，而不是 29-DoF、长时域、密集接触的 G1 tracking。([牛顿物理][1])

因此：

> **finite-difference / paired counterfactual sensitivity 应当是主方法，differentiable sensitivity 应当只是 optional spike。**

这并不削弱项目。Newton 的 batched worlds 恰好让有限差分不再那么昂贵：同一 motion 的 (+\delta)、(-\delta) 参数世界可以并行运行。

---

# 三、为什么不是直接做 multi-solver training、更多 DR 或 residual adaptation

## Generic multi-simulator training 已经有很近的工作

PolySim 已经把 multiple heterogeneous simulators 放在同一个 training run 中，将 simulator engine 本身作为 dynamics-level randomization，并在 Unitree G1 上做了 sim-to-sim 和 real deployment。单纯的“randomly switch Newton solver during training”会很接近这条已有路线。([arXiv][6])

所以你们不能把主要 novelty 写成：

> We train across multiple physics engines.

你们更清楚的差异应该是：

> We identify which motion phase is sensitive to which physical mechanism, show that this predicts failure, and use that structured fragility to allocate training.

## Global SysID 和 black-box residual 也已经很拥挤

ASAP 已经通过 real-world data 学习 delta action model，再用它对模拟器和 policy 做 alignment；SPI-Active 则通过大规模 sampling 与 active exploration 识别物理参数。([arXiv][7])

所以第一篇论文不应当直接变成：

* 又一个 global physical parameter estimator；
* 又一个 residual action MLP；
* 又一个 online adaptation latent。

这些可以是后续 **PhysAdapt** 工作，但不适合现在就放进第一篇论文。

## SONIC 本身已经做了广泛的 domain randomization

公开配置里已经包含：

* static/dynamic friction 和 restitution randomization；
* all-body mass scaling；
* torso CoM shift；
* default joint position perturbation；
* wrist/torso mass scaling；
* periodic external pushes。

因此“把 friction range 再扩大一点”既难以解释，也不够新。你们真正的价值应该是：

> 不再问 randomization 要不要更宽，而是问哪个 motion phase 需要哪一种 uncertainty，以及训练预算应该如何分配。

---

# 四、我推荐的完整研究问题

## 论文主问题

> **Can closed-loop, phase-local physics fragility explain and predict humanoid motion-tracking failures beyond reference-only motion features, and can it guide more effective robust training?**

## 三个核心假设

### H1：Physics fragility 能解释 reference atlas 的 missing signal

现有 reference atlas 对跨 policy difficulty 的相关性是 (0.567)，而两 policy 的 difficulty consistency 是 (0.832)。这里的 (0.832) 应当称为一个 empirical reference，而不是严格数学 ceiling。

假设：

[
\text{reference features}
+
\text{closed-loop fragility}
]

对 unseen motion difficulty 的预测显著优于 reference-only atlas。

最重要的第一项预测是：

> clip #44 应当在 actuator、contact 或 timing fragility 中出现异常，即使它的 reference atlas 很 benign。

### H2：Fragility 一部分属于 motion，一部分属于 policy

在相同 motion、相同 physics interventions 下，对比：

* 你们 Exp-1/Exp-2 tracker；
* grounded/uniform/adaptive checkpoints；
* frozen SONIC；
* SONIC default、low-latency、v1.1。

SONIC 目前三个公开 checkpoint 都使用 64-D universal token 和 50 Hz controller；default 与 v1.1 使用约 200 ms reference lookahead，low-latency 使用约 80 ms；v1.1 还加入了 heading normalization 和 wrist-pose augmentation。([NV Labs][8])

这提供了很漂亮的自然实验：

* 如果不同 policy 在同一 phase 都对 friction 敏感，fragility 更可能是 motion-intrinsic；
* 如果只有某个 policy 敏感，它更可能来自 training recipe；
* default vs low-latency 可以测试 temporal horizon 对 delay fragility 的影响；
* default vs v1.1 可以测试 augmentation 是否改变 upper-body / heading fragility。

### H3：Fragility-aware curriculum 优于 failure-count curriculum

当前 adaptive sampler 只知道 clip #44 一直失败，于是不断采它，最后造成 87–89% exposure collapse。

新 sampler 的 unit 不再只是 clip (m)，而是：

[
x=(m,p,k,\ell),
]

其中：

* (m)：motion；
* (p)：phase/segment；
* (k)：physics mechanism；
* (\ell)：perturbation severity。

Sampler 应在 capped simplex 上投影，显式满足：

[
q_i \ge q_{\min}, \qquad
q_i \le q_{\max}, \qquad
\sum_i q_i=1.
]

也就是说，真正实现 lower bound 和 cap，而不是把一个 uniform term 加入未经约束的 score 后再错误地称为 floor。

Sampling score 可以结合：

[
s_i
===

\alpha F_i
+
\beta LP_i
+
\gamma U_i
----------

\lambda E_i,
]

其中：

* (F_i)：physics fragility；
* (LP_i)：近期 learning progress；
* (U_i)：policy/model uncertainty；
* (E_i)：realized exposure 或 staleness correction。

这样 curriculum 采样的是“有物理意义、仍有学习价值的 frontier”，而不是纯粹失败最多的 clip。

---

# 五、Physics fragility 应该怎么定义

设 frozen policy (\pi) 跟踪 motion (m)，在 phase (t) 受到第 (k) 类物理干预。

运行一组 paired counterfactual rollouts：

[
\tau^{+\delta_k}*{m,\pi},
\qquad
\tau^{-\delta_k}*{m,\pi}.
]

定义 frame-local fragility：

[
F_{m,t,k}
=========

\frac{
d!\left(
\phi(\tau^{+\delta_k}*{m,\pi,t}),
\phi(\tau^{-\delta_k}*{m,\pi,t})
\right)
}{
2\delta_k+\epsilon
}.
]

其中 (\phi) 不是一个 scalar reward，而是一组可解释指标：

* root position/orientation error；
* local/global body tracking error；
* foot position/orientation error；
* stance-foot slip；
* foot-yaw drift；
* contact onset/offset；
* support loss；
* joint target–state phase lag；
* effort saturation；
* recovery time；
* termination risk。

再定义经过 conformance 的 model-form disagreement：

[
D_{m,t}
=======

\operatorname{Var}*{s\in\mathcal S}
\left[
\phi(\tau^{(s)}*{m,\pi,t})
\right],
]

但 (D) 是 secondary signal；只有在统一 actuator、timestep、contact semantics 后，才可以解释。

## 第一版 intervention family

### Actuator

* command delay；
* variable delay / jitter；
* (K_p/K_d) scaling；
* torque-strength scaling；
* DC-motor torque-speed saturation；
* selected weak joint；
* later：dead zone / motor friction。

### Contact

* static/dynamic/torsional friction；
* contact stiffness/damping；
* foot collision geometry；
* MuJoCo native vs Newton SDF contact；
* Newton hydroelastic contact；
* small ground slope/height error。

### Morphology and load

* torso mass/CoM；
* limb inertia；
* backpack or payload；
* arm-position-dependent load。

### Timing and sensing

* observation delay；
* action delay；
* IMU bias；
* encoder noise；
* dropped/repeated observation；
* asynchronous timing。

---

# 六、具体 research plan：按 gate 推进，而不是按 idea 推进

## Phase 0：Newton conformance harness

**时间：5–7 天**

先不要直接做 full SONIC integration。先用你们自己的一个已知 checkpoint，完成 same-solver conformance：

1. pin exact Newton commit、MuJoCo Warp version 和 asset hash；
2. 确认 joint/body ordering、quaternion、root frame、default pose；
3. 相同 initial state、dt、substep、action decimation；
4. external effort-level PD；
5. 相同 termination 和 metric；
6. mjlab/MuJoCo 与 Newton/`SolverMuJoCo` 跟踪同一 clip。

Newton 的现有 `robot_policy` example 已经证明 G1 ONNX inference 路径存在，但它的 observation 是 locomotion-style observation，并不是 SONIC 的 encoder/history/future-reference contract，因此不能直接替换模型文件。

SONIC integration 必须读取匹配 checkpoint 的 `observation_config.yaml`，准确复现 history、reference frames、joint order、encoder 和 decoder；官方也明确要求 encoder、decoder 与 observation config 配套使用。([NV Labs][8])

**Gate G0：**
同一 solver 下，如果 survival、短时 trajectory、contact sequence 和主要 tracking metric 不能在预注册 tolerance 内一致，后面看到的任何 solver difference 都只能算 integration error。

## Phase 1：clip #44 decisive spike

**时间：3–4 天**

只跑：

* clip #44；
* 2 个 matched easy clips；
* 2 个普通 hard clips；
* 1 个高动态但 reference atlas 已判定困难的 clip。

只做五个 intervention：

1. action delay；
2. motor strength；
3. contact friction；
4. contact stiffness/model；
5. torso CoM。

使用 paired worlds 和 common initial conditions。

**Gate G1：**

clip #44 是否在某个物理 mechanism 上出现：

* 明显更高 fragility；
* failure 前可以定位的 phase-local spike；
* 与 matched controls 不同的 signature。

如果答案是否定的，就不要立即扩展到 800 或 10,000 clips。先检查：

* tracking reward/termination artifact；
* reference corruption；
* initialization；
* impossible reference；
* policy representation failure。

这个 gate 会保护你们不再花一个月构建一个没有 signal 的 atlas。

## Phase 2：200-clip PhysFrag atlas

**时间：2–3 周**

从 10,822 clips 中按以下轴 stratified sampling：

* low/high kinematic intensity；
* single/multi-contact；
* locomotion/non-locomotion；
* upper-body-dominant/lower-body-dominant；
* easy/hard；
* clip family 与 mirrored pair。

先做 200 clips，不要直接全库。

训练一个简单预测模型，比较：

1. clip length；
2. reference kinematics；
3. reference inverse dynamics；
4. model-form disagreement only；
5. structured physics fragility；
6. reference + fragility。

Cross-validation 必须按 source motion、subject、mirror pair 或 motion family 分组，不能随机拆 frame，否则高度相似的 motion 会造成 leakage。

**Gate G2：**

* combined atlas 对 held-out difficulty 的 Spearman 提升至少达到一个预注册的 meaningful effect，例如 (\Delta\rho \ge 0.10)；
* bootstrap confidence interval 不跨零；
* clip #44 不再是 unexplained outlier；
* fragility peak 在失败之前出现，而不是失败之后才增大。

通过后再扩到 800 clips，并最终考虑全库。

## Phase 3：Cross-policy 与 SONIC study

**时间：1–2 周**

对同一个 200/800-clip bank：

* 运行你们的 trackers；
* 运行 frozen SONIC；
* 对比 SONIC default、low-latency、v1.1。

SONIC 从 released checkpoint 重新训练并不适合作为第一步：官方训练指南使用 4096 environments，并建议 64+ GPUs 才能在合理时间内收敛。更现实的策略是把 SONIC 当作强 external benchmark，随后只做小规模 continued training、decoder fine-tuning 或 bounded adapter。([NV Labs][9])

这里要回答：

* fragility ranking 跨 policy 是否稳定；
* SONIC 是否消除了小 tracker 的某些 actuator/contact weakness；
* SONIC 是否出现新的 latency/reference-horizon weakness；
* 大规模 motion pretraining 是否真正减少 model sensitivity，而不只是提升 nominal success。

## Phase 4：Fragility-aware curriculum

**时间：3–4 周**

训练仍然留在 mjlab/Isaac Lab，不急着把 PPO 全部迁到 Newton。你们自己的文档也正确指出 Newton 当前不是完整 RL trainer。

比较：

* uniform；
* original error-adaptive；
* grounded；
* reference-atlas curriculum；
* fragility-only；
* fragility + learning-progress；
* full capped/floored mechanism-aware curriculum。

所有实验：

* matched environment steps；
* matched physics rollout budget；
* 3–5 seeds；
* 记录 realized exposure；
* 报告 mean 和 worst decile；
* 报告 forgetting/downward crossings；
* 报告 held-out physics，而不只是 nominal simulator。

**Gate G3：**

新 curriculum 必须同时做到：

* 不发生 exposure collapse；
* worst-decile motion success 提升；
* held-out actuator/contact perturbation 提升；
* nominal tracking 不显著退化。

如果只提高 nominal endpoint，而没有 robustness 或 worst-case gain，就不支持 paper thesis。

## Phase 5：Real G1 validation

**时间：约 2 周，取决于硬件排期**

选择 10–20 个安全 motion：

* fragility high/low；
* actuator-sensitive/contact-sensitive；
* matched kinematics；
* 其中部分完全不参与 atlas fitting。

记录：

* target and measured joint states；
* IMU；
* command/state timestamps；
* policy action；
* onboard error flags；
* 外部 mocap 或 calibrated video，如果可用。

硬件问题分两层：

1. predicted fragility 能否 rank 真实误差最大的 motion；
2. fragility-aware policy 是否降低这些 motion 的 error 或 failure。

没有硬件时，论文可以诚实地声称 **cross-physics robustness**；有硬件并得到正结果后，才正式声称 sim-to-real improvement。

---

# 七、第一篇论文应该保留和舍弃什么

## 第一篇保留

* Newton–tracker/SONIC conformance harness；
* structured counterfactual physics fragility；
* clip #44 case study；
* reference atlas transfer gap；
* cross-policy analysis；
* fragility-aware curriculum；
* 小规模 real G1 validation。

## 第一篇暂时不做主贡献

* full solver-ensemble PPO training；
* full SONIC training from scratch；
* long-horizon differentiable G1 contact optimization；
* online physics-context estimator；
* residual action adapter；
* deformable terrain / MPM；
* VLA high-level task integration。

这些不是坏 idea，而是第二篇论文的自然延伸：

> **PhysAdapt:** infer a motion-conditioned physics context from proprioceptive history, then use a bounded adapter downstream of SONIC’s motion token.

第一篇先回答“哪里脆弱、为什么脆弱、能否指导训练”；第二篇才回答“机器人在线如何适应这种脆弱性”。

---

# 八、可以直接拿去和导师讨论的 research proposal

# PhysFrag: Motion-Conditioned Physics Fragility Maps for Robust Humanoid Whole-Body Tracking

## 1. Project Summary

Modern humanoid motion-tracking policies can reproduce large libraries of human motion in simulation, yet their failures remain highly motion-dependent and difficult to explain. Existing motion-difficulty models primarily describe the reference trajectory using kinematic quantities, contact schedules, or reference-frame inverse dynamics. These descriptors do not capture the closed-loop interaction among the reference motion, the controller, the robot, and imperfect physics.

We propose **PhysFrag**, a framework for measuring **motion-conditioned physics fragility**: the frame- and body-level sensitivity of a closed-loop humanoid tracker to structured changes in actuator behavior, contact mechanics, timing, and morphology. Newton provides the required experimental substrate through batched GPU worlds, composable actuator models, alternative contact-generation pipelines, multiple solver formulations, ONNX inference, and articulated-dynamics analysis.

PhysFrag will first diagnose why specific motions fail, then test whether fragility features predict held-out motion difficulty beyond reference-only descriptors, and finally use the resulting maps to construct a fragility-aware curriculum. The project will be evaluated on existing G1 tracking policies and released SONIC controllers, followed by a targeted Unitree G1 validation.

## 2. Current Evidence and Motivation

The project already contains a validated bank of 10,822 G1 motion clips totaling 43.6 hours. Data auditing identified and corrected three silent failure modes involving body ordering, mixed frame rates, and relative root-height storage. A reference-based physics atlas has been computed for 10,705 clips and predicts within-policy motion difficulty out of fold, while clip duration is not a useful difficulty proxy.

Curriculum experiments produced a second key result. A failure-adaptive sampler collapsed 87–89% of its realized exposure onto a single clip in all three seeds and underperformed uniform sampling. A grounded sampler corrected the collapse and recovered competitive learning behavior.

The strongest scientific clue is a gap between reference-based and closed-loop difficulty. Two independently trained policies rank clip difficulty with Spearman correlation ( \rho=0.832 ), suggesting that difficulty has a stable motion-dependent component. However, the existing reference-only atlas transfers at only ( \rho=0.567 ). The most prominent unexplained clip has survival 0.31 compared with a bank mean of 0.89, despite benign reference-based dynamic features.

These findings motivate the central hypothesis:

> The missing difficulty signal lies in the closed-loop interaction among motion phase, controller behavior, actuator dynamics, and contact physics, rather than in the reference trajectory alone.

## 3. Research Gap

Three adjacent research directions do not fully answer this question.

First, multi-simulator training methods such as PolySim reduce simulator-specific inductive bias by jointly training across heterogeneous engines, but they do not primarily seek a phase-local, mechanism-specific explanation of why a particular motion fails. ([arXiv][6])

Second, real-to-sim alignment methods such as ASAP learn residual action corrections from real trajectories, while sampling-based system-identification methods such as SPI-Active estimate global physical parameters through active exploration. These approaches improve transfer, but they do not construct a motion-conditioned map of which physical mechanisms are excited at each phase of a diverse motion library. ([arXiv][7])

Third, standard domain randomization treats physical parameters as globally sampled nuisance variables. Released SONIC configurations already randomize friction, restitution, mass, center of mass, joint offsets, and external disturbances. The remaining question is therefore not simply whether randomization should be broader, but which uncertainty matters for which motion and when.

## 4. Research Questions

### RQ1: Prediction

Does closed-loop physics fragility predict held-out humanoid tracking difficulty better than reference-only kinematic and inverse-dynamics features?

### RQ2: Attribution

Can phase-local fragility distinguish actuator-, contact-, timing-, and morphology-driven failure modes?

### RQ3: Motion versus Policy

Which fragility patterns are consistent across tracking policies and therefore likely motion-intrinsic, and which depend on a specific training recipe or controller architecture?

### RQ4: Training

Can a fragility-aware curriculum improve worst-case motion tracking and held-out-physics robustness at matched rollout and training compute?

### RQ5: Sim-to-Real Relevance

Do simulated fragility maps predict the motions and phases that exhibit the largest tracking errors on a physical Unitree G1?

## 5. Hypotheses

**H1.** Adding closed-loop fragility features to the reference atlas will produce a statistically significant improvement in grouped out-of-fold motion-difficulty prediction.

**H2.** The currently unexplained hard clip will exhibit elevated actuator, contact, or timing fragility at a localized phase despite its benign reference-only profile.

**H3.** Fragility rankings will contain both a cross-policy component and a policy-specific component. The cross-policy component will identify motion-intrinsic physical requirements, while policy-specific residuals will expose weaknesses in training or architecture.

**H4.** A capped and coverage-preserving fragility curriculum will improve worst-decile success and held-out-physics robustness without the exposure collapse observed in failure-only adaptive sampling.

**H5.** Motion-level and phase-level fragility will positively correlate with real G1 tracking error, particularly foot slip, contact-timing error, body-orientation error, and target-to-state phase lag.

## 6. Technical Approach

### 6.1 Newton Conformance Harness

We will first build a solver-neutral tracking harness that reproduces an existing mjlab tracker inside Newton under the same MuJoCo dynamics. The harness will standardize:

* G1 joint and body ordering;
* asset version and inertial parameters;
* coordinate and quaternion conventions;
* initial state and reference phase;
* physics timestep and substeps;
* policy rate and action decimation;
* observation normalization and temporal history;
* action scale;
* termination rules;
* tracking and contact metrics.

A second adapter will reproduce the matching observation configuration for released SONIC checkpoints. SONIC currently provides default, low-latency, and v1.1 G1 checkpoints. All use a 64-dimensional universal motion token and a 50 Hz controller, while differing in reference horizon and augmentation. ([NV Labs][8])

Same-solver conformance is a hard prerequisite. Any discrepancy observed before this gate will be treated as an integration error rather than a scientific physics result.

### 6.2 Solver-Neutral Actuation

Native joint-target implementations are not directly comparable across Newton solvers. We will therefore externalize actuation using a shared pipeline:

[
q_t^{\mathrm{target}}
\rightarrow
\text{Delay}
\rightarrow
\text{PD Controller}
\rightarrow
\text{Motor Clamping}
\rightarrow
\tau_t.
]

The resulting effort will be supplied through the common `joint_f` interface. Newton’s actuator API provides vectorized delay, PD/PID control, maximum-effort clamping, and DC-motor effort-speed saturation. ([牛顿物理][2])

This design separates controller and motor assumptions from the downstream dynamics solver and enables controlled actuator interventions.

### 6.3 Structured Physics Interventions

For policy (\pi), motion (m), phase (t), and physical mechanism (k), we will generate paired counterfactual rollouts:

[
\tau^{+\delta_k}*{m,\pi},
\qquad
\tau^{-\delta_k}*{m,\pi}.
]

The primary intervention families are:

1. **Actuation:** command delay, variable delay, PD gain scaling, motor-strength scaling, effort-speed saturation, and selected weak joints.
2. **Contact:** friction, contact stiffness and damping, foot geometry, native MuJoCo contacts, Newton SDF contacts, and Newton hydroelastic contacts.
3. **Morphology:** link mass, inertia, torso center of mass, and external payload.
4. **Timing and sensing:** observation delay, IMU bias, encoder noise, packet repetition, and asynchronous update timing.

Newton allows its collision pipeline to replace MuJoCo contact generation while retaining the MuJoCo dynamics backend. This provides a relatively controlled contact-model axis before broader solver comparisons are introduced. ([牛顿物理][3])

### 6.4 Physics Fragility Map

Let (\phi(\tau_t)) denote a vector of frame-level behavior metrics. We define mechanism-specific fragility as:

[
F_{m,t,k}
=========

\frac{
d\left(
\phi(\tau^{+\delta_k}*{m,\pi,t}),
\phi(\tau^{-\delta_k}*{m,\pi,t})
\right)
}{
2\delta_k+\epsilon
}.
]

The metric vector will include:

* root position and orientation error;
* local and global body-position error;
* joint-position and joint-velocity error;
* stance-foot slip and yaw drift;
* contact onset and offset error;
* support loss;
* target-to-state phase lag;
* effort saturation;
* action rate and energy;
* recovery time;
* termination probability.

Fragility will be retained at frame, body, segment, and clip levels.

A secondary model-form disagreement score will be computed after actuator and contact normalization:

[
D_{m,t}
=======

\operatorname{Var}*{s\in\mathcal S}
\left[
\phi(\tau^{(s)}*{m,\pi,t})
\right].
]

Because Newton solvers differ in coordinate representation and feature support, raw solver disagreement will not be interpreted as real-world uncertainty without calibration.

### 6.5 Cross-Policy Fragility Decomposition

We will evaluate the same intervention bank with:

* existing uniform, adaptive, and grounded project checkpoints;
* at least one independently trained tracking policy;
* released SONIC default;
* SONIC low-latency;
* SONIC v1.1.

A shared fragility component across policies will be interpreted as evidence of a motion-intrinsic physical requirement. A policy-specific residual will identify controller or training-recipe weaknesses.

The SONIC checkpoint variants provide two useful natural ablations:

* default versus low-latency tests sensitivity to reference horizon and system delay;
* default versus v1.1 tests whether heading normalization and wrist-pose augmentation alter heading and upper-body fragility.

### 6.6 Fragility-Aware Curriculum

The curriculum state will be indexed by motion, phase, physical mechanism, and severity:

[
x=(m,p,k,\ell).
]

The sampling score will combine physics fragility, recent learning progress, uncertainty, coverage, freshness, and realized exposure. The final distribution will be projected onto a constrained simplex:

[
q_i \ge q_{\min},
\qquad
q_i \le q_{\max},
\qquad
\sum_i q_i=1.
]

This provides a genuine uniform floor and explicit concentration cap.

The initial training experiments will remain in mjlab or Isaac Lab. Newton will generate fragility priors, counterfactual evaluations, and held-out-physics tests. Full solver-mixed training is intentionally deferred because it carries higher engineering risk and overlaps more closely with existing multi-simulator training work.

### 6.7 Real-Robot Validation

A safe, stratified set of 10–20 motions will be selected from predicted high- and low-fragility groups. Motions will be matched where possible on reference kinematics while differing in predicted physical mechanism.

We will record joint targets, measured joint states, IMU signals, policy actions, timestamps, deployment error flags, and external pose measurements when available.

The primary hardware analysis will test whether simulated fragility:

1. ranks motions by real tracking error;
2. localizes the phases preceding real deviation;
3. distinguishes contact-dominated and actuator/timing-dominated errors;
4. identifies the motions improved by fragility-aware training.

Without physical-robot validation, conclusions will be restricted to cross-physics robustness rather than sim-to-real transfer.

## 7. Experimental Sequence and Decision Gates

### Gate G0: Same-Solver Conformance

Track one known motion with the same checkpoint in the original MuJoCo harness and Newton `SolverMuJoCo`.

Proceed only if survival, short-horizon trajectory, contact sequence, and tracking metrics agree within a pre-registered tolerance.

### Gate G1: Unexplained-Clip Test

Evaluate the known unexplained hard clip and matched controls under five structured interventions.

Proceed to atlas construction only if the hard clip exhibits a distinct and temporally localized fragility signature, or if the experiment identifies a different concrete source of its difficulty.

### Gate G2: Predictive Value

Construct a 200-clip stratified atlas.

Proceed to 800 clips only if combined reference-plus-fragility features improve grouped out-of-fold difficulty prediction by a pre-registered meaningful amount, with a positive bootstrap confidence interval.

### Gate G3: Cross-Policy Structure

Proceed to curriculum training only if fragility contains either:

* a stable cross-policy component that generalizes to SONIC; or
* a reproducible policy-specific component that predicts differential robustness.

### Gate G4: Curriculum Benefit

The proposed curriculum must improve worst-decile tracking and held-out-physics robustness at matched compute, while avoiding concentration collapse and preserving nominal performance.

## 8. Baselines

The study will compare against:

* clip length;
* reference kinematic features;
* reference inverse-dynamics features;
* scalar failure-rate sampling;
* uniform sampling;
* the existing grounded sampler;
* reference-atlas curriculum;
* uniform parameter domain randomization;
* solver disagreement without structured interventions;
* fragility-only sampling;
* fragility plus learning progress and coverage.

## 9. Evaluation Metrics

### Tracking

* success and survival;
* local and global MPJPE;
* root translation and orientation error;
* joint-position and joint-velocity error.

### Contact

* stance-foot slip;
* foot-yaw drift;
* contact-state precision and recall;
* contact onset and offset error;
* support-loss events;
* impact and contact-force statistics in simulation.

### Actuation and Timing

* target-to-state phase lag;
* effort saturation;
* action rate and jerk;
* command-to-state delay;
* recovery time.

### Learning Dynamics

* area under the learning curve;
* endpoint performance;
* worst-decile success;
* held-out-physics degradation;
* realized exposure concentration;
* frontier crossings and forgetting events.

### Sim-to-Real

* correlation between predicted fragility and real tracking error;
* ranking accuracy for the worst motions;
* phase-local error prediction;
* improvement after fragility-aware training.

## 10. Expected Contributions

1. **A Newton–G1 tracking conformance harness** supporting frozen project trackers and released SONIC checkpoints.
2. **A motion-conditioned physics fragility representation** that localizes sensitivity by frame, body, and physical mechanism.
3. **Evidence separating motion-intrinsic and policy-specific fragility** through cross-policy and cross-checkpoint analysis.
4. **A fragility-aware curriculum** that allocates training across motion–phase–physics cells while enforcing coverage and concentration constraints.
5. **A benchmark and dataset of G1 physics interventions and fragility maps**, with real-robot validation where available.
6. **A clearer account of when solver/contact disagreement is informative**, including the controls required to distinguish model-form effects from actuator and representation confounds.

## 11. Scope Discipline

The first paper will not depend on:

* end-to-end differentiable MuJoCo tracking;
* full SONIC training from scratch;
* online residual adaptation;
* full multi-solver PPO training;
* deformable terrain or MPM;
* a high-level VLA task policy.

Differentiable sensitivity will be treated as an optional spike. Finite-difference paired rollouts are the primary method. Online context estimation and bounded action adaptation are reserved for a follow-up project.

## 12. Tentative Timeline

**Week 1:** version pinning, same-solver harness, project-policy conformance.
**Week 2:** unexplained-clip intervention gate and external actuator validation.
**Weeks 3–5:** 200-clip fragility atlas, prediction, and ablations.
**Weeks 6–7:** 800-clip expansion and cross-policy/SONIC study.
**Weeks 8–10:** fragility-aware curriculum training.
**Weeks 11–12:** held-out-physics evaluation and paper figures.
**Weeks 13–14:** real G1 validation and final paper revision.

## 13. Paper Thesis

A humanoid motion is not only a trajectory to imitate; it is also a physical experiment that excites specific aspects of the robot and its environment. By measuring how closed-loop tracking changes under structured physical interventions, PhysFrag aims to explain which motion phases are physically fragile and use that knowledge to train humanoid controllers where robustness is actually needed.

# 最后，我建议你们现在只做这三个动作

第一，**冻结当前扩张**：暂时不要继续铺开 E3、E4、E10，也不要启动 full SONIC training。

第二，**先完成 same-solver conformance**：项目 checkpoint 在 mjlab MuJoCo 与 Newton MuJoCo 中必须先一致。

第三，**立刻跑 clip #44 gate**：同一 policy、同一 initial state，只改变 delay、motor strength、friction、contact model 和 torso CoM。

这两个 gate 通过之后，项目就不再是“我们能用 Newton 做什么”，而会变成一个非常明确的科学问题：

> **Newton 揭示了 reference motion 看不见、但真实 controller 必须承受的 physics fragility；我们再用它改变 humanoid 的训练方式。**

[1]: https://newton-physics.github.io/newton/stable/solvers/index.html "https://newton-physics.github.io/newton/stable/solvers/index.html"
[2]: https://newton-physics.github.io/newton/stable/concepts/actuators.html "https://newton-physics.github.io/newton/stable/concepts/actuators.html"
[3]: https://newton-physics.github.io/newton/stable/concepts/collisions.html "https://newton-physics.github.io/newton/stable/concepts/collisions.html"
[4]: https://github.com/newton-physics/newton/releases/tag/v1.5.0 "https://github.com/newton-physics/newton/releases/tag/v1.5.0"
[5]: https://newton-physics.github.io/newton/stable/concepts/articulations.html "https://newton-physics.github.io/newton/stable/concepts/articulations.html"
[6]: https://arxiv.org/abs/2510.01708 "https://arxiv.org/abs/2510.01708"
[7]: https://arxiv.org/abs/2502.01143 "https://arxiv.org/abs/2502.01143"
[8]: https://nvlabs.github.io/GR00T-WholeBodyControl/model_card.html "https://nvlabs.github.io/GR00T-WholeBodyControl/model_card.html"
[9]: https://nvlabs.github.io/GR00T-WholeBodyControl/user_guide/training.html "https://nvlabs.github.io/GR00T-WholeBodyControl/user_guide/training.html"
