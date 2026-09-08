# fable.md — Research guidance for CLIMB / feasibility-first (rev 5, updated 2026-09-08)

**Author:** Claude Fable 5.1. **Status:** unsealed guidance. Not a preregistration; authorizes
nothing by itself.
**Supersedes** rev 4 (same day, morning; kept in git history). Rev 4 was written to get a
complete, honest eight-page ICRA submission out of an inconclusive result. That has happened.
Rev 5 records the finished state, the one open loop, and the thing this project has never had:
**a route to a physical robot.**

---

## 0. One-paragraph verdict

The paper is done at simulation scale and it is honest. Twenty verified repairs closed every
disagreement found between the manuscript and its own code, the build passes every gate at eight
pages, and the claim set no longer depends on a positive result anywhere. The scientific position
is: **reference–physics misalignment is real, measurable at bank scale, and transfers difficulty
information across policies; and on exact admissible support, no allocation rule we tested beat
uniform at this budget.** That is a publishable contribution and a genuinely useful negative
result. One loop was open and is now closed by decision rather than by
evidence: H1, the admission on/off test, finished all ten training runs and then stopped before
its first evaluation cell on a harness bug. It has no result, and it will not be revived for this
submission, because integrating it would cost roughly 45 lines of content that adversarial
verification just established as necessary. Rung 2 of the deployment ladder *was* run on 8
September, and it refuted its own registered prediction. Everything beyond that is the next
programme, and the honest name for it is not "more allocation experiments" — it is **the
deployment gap**, because this project has never run a physical experiment of any kind.

---

## 1. State at the end of 7 September

### 1.1 The manuscript

| item | state |
|---|---|
| Title | "When Failure Is Not Difficulty: Screening Reference–Physics Misalignment and Testing Adaptive Allocation on Exact Support for Humanoid Motion Tracking" |
| Contributions | two, as rev 4 §3.2 specified. The third (admission) was deleted, not left pending, because H1 has no result |
| Build | 8 pages, US Letter, zero overfull boxes, no undefined citation or reference, no Type 3 fonts, no anonymity leak in the PDF |
| Repairs | 20 applied across two passes, all fail-closed and artifact-verified (`reports/fable_independent_verification_2026-09-07/`) |
| Ledgers | `paper/RESULTS_LOG.md` and `plan/STATUS.md` carry dated entries for the H1 stop and both repair passes |

The three corrections that most changed what a reviewer concludes:

1. **The E1 campaign ran three arms and the paper reported two.** The omitted grounded sampler
   peaked at top-1 mass 0.568/0.649/0.696 rather than 0.87–0.89 and beat uniform in 3/3 paired
   seeds (+0.0088/+0.0238/+0.0125). It is the direct evidence for the paper's own claim that the
   collapse came from the additive-floor construction rather than from outcome-driven allocation
   as such. Reporting it is both more honest and better for the argument.
2. **A survival sentence was contradicted by its own artifact.** "Zero survival from frame zero"
   holds only under a 10-second whole-clip horizon. Under three-second stratified windows the
   same reference survives from frame zero in 0.25–1.00 of episodes across seven policies. The
   sentence compared two protocols without naming either.
3. **The 0.05 exposure gate sits below its own noise floor.** A learning-free reference for the
   sampler's functional form yields total variation 0.0605 at 1,184 units and exceeds 0.05 in
   every one of 2,000 replicates. Passing that gate shows allocation moved, not that it tracked
   learning progress.

### 1.2 H1: ten training runs, no result

All ten 4,000-iteration runs completed and passed their gates at a mean 28.2 minutes each. The
campaign then failed on `evaluate_on_s1041_i1000` because `paper/h1/job.py` calls the evaluator
directly instead of through `tools/eval_relative_confirmation.py`, whose `load_sealed_conditions`
adds the two provenance keys (`classification`, `panel_txt_sha256`) that the stored Phase-G
condition manifest carries and the builder does not emit. Every scientific parameter, all 2,800
conditions and all 100 motion records match exactly.

The failure is **provably pre-endpoint** — before any checkpoint load or CSV write — so nothing
about the comparison has been observed. Continuation in place is blocked by design: sentinels use
exclusive create, the terminal record already exists, and the campaign path is contract-bound.
Finishing H1 needs a contract revision. **Decided on 8 September: not for this submission.**
Page 8 carries 78 of roughly 120 lines after the audit repairs and the new limitations, while an
integrated H1 section needs about 119 line-equivalents including its figure. H1 is also rung 3,
behind two desk rungs that cost no compute. The ten training runs remain intact and hash-bound, so
the cost of waiting is time, not evidence. Options and costs stay recorded in
`plan/H1_EVALUATION_FAILURE_2026-09-07.md` for whenever the revision is made.

### 1.3 What this project has never done

No hardware experiment. No physical G1. No tethered bench test. No sim-to-real transfer of any
kind. Every number in the paper, on the public site, and in this file is simulation. Section 4 is
about closing that, and it must never be written as though any of it has happened.

---

## 2. The deployment gap, stated plainly

The paper's result is about *which references a trainer should admit and where it should spend
practice*. None of that is a controller you can put on a robot. Six things stand between the
current artifact and a physical G1, and they are not equally hard.

### 2.1 The model is not the robot

`reports/icra_evidence_2026-09-06/physics_audit.json` reproduced all twelve frozen configuration
hashes and compiled the unchanged robot, exposing every actuator limit. What it found:

| axis | configured | gap |
|---|---|---|
| Knee effort | ±139 N·m, force limiting on, unit gear | Our audit *records* vendor figures of 90 N·m (G1) and 120 N·m (G1 EDU) with no archived source, and does not establish that they describe the same point in the drivetrain as the compiled limit. Re-screening at those levels moved 12 of 900 clips (§3 rung 2) |
| Command delay | 0/0 min-max on all six actuator groups | Physics steps 5 ms, control 20 ms. Command delay, motor response lag and observation latency are three different perturbations, none modeled |
| Contact | full collision config, feet condim 3, nominal foot friction 0.6, startup sampling 0.3–1.2 | Configured friction is not measured contact fidelity |
| Terrain | plane | Uneven terrain untested; the screen would need its terrain in the scene |
| Evaluation | sealed `nominal=false`, startup COM/friction/encoder randomization retained, pushes and observation corruption removed | Not a factorial robustness study |

The screen itself declares electrical, thermal, compliance, latency and structural limits out of
scope. **Model-relative admissibility is not physical feasibility, and the paper says so.**

### 2.2 Execution is short and segmented

A training trial is capped at one second of simulated time (50 control steps at 50 Hz), though
failure terminations end many sooner. Evaluation windows are three seconds. The longest genuinely
continuous execution ever demonstrated is **8.58 seconds**, on one development policy
(R11, checkpoint 2000), on two fully admitted training references, with zero active resets. That
is a pipeline smoke, not a comparison and not a generalization result. A deployment needs whole
references, transitions between them, and recovery after disturbance — none of which exists.

### 2.3 The physical-sensitivity study is blocked

The eight-condition frozen-policy sensitivity design (delays 5/10/20 ms, knee caps 120/90 N·m,
foot friction 0.3/1.2) is implemented and CPU-verified, but its CUDA queue completed all nine
development cells and then failed the aggregate original-versus-unchanged exact CSV parity gate.
The cause is unresolved, so no perturbation number may be reported.

### 2.4 The observation interface is privileged

The policy consumes simulator state and a time-indexed reference. On hardware that requires state
estimation, reference synchronization, on-robot compute at the control rate, and a safety
envelope. None of it is built here.

### 2.5 The scientific claim would have to be re-earned

Even a perfect port would not transfer the paper's finding. The allocation comparison is
inconclusive *in simulation at three seeds*; it says nothing about hardware. A hardware claim
needs its own preregistration, its own independent unit, and its own power statement.

### 2.6 The honest summary

CLIMB is a **data-and-training-interface contribution with a bank-scale measurement result**. It
is not a controller, and it is two or three programmes away from being one.

---

## 3. The deployment ladder

Ordered. Each rung answers one question, and several may return nulls. Simulation rungs are cheap
and should be finished first because they are the ones that can still change the paper's claims.

Ordered by what can invalidate what, not by what is exciting. Two verified facts reordered this
table after rev 5's first draft, and both came from reading the code rather than the plans.

| # | rung | tier | question | cost | kill rule |
|---|---|---|---|---|---|
| 1 | **Observation-interface audit** | desk | What does the policy consume that a G1 cannot measure? | days, no compute | If the actor's observations cannot be reconstructed on-robot, redesign before spending any hardware time |
| 2 | **Re-screen under tighter limits** — **DONE 8 Sep** | desk | Does the flagged set survive replacing ±139 N·m with 120 and 90 N·m? | CPU only, ~5 min | *Ran. 888/900 clips unchanged, flagged 99 → 98. Registered monotonicity prediction refuted; lower-bound claim withdrawn.* |
| 3 | **Finish H1** | sim | Does excluding model-inadmissible practice protect learning under a common allocator? | ~1–6 GPU-h | If the revised contract is not sealed, H1 stays a named next test |
| 4 | **S1 parity, then sensitivity** | sim | Do frozen policies degrade under declared delay, torque and friction perturbations? | ~1 GPU-day after the parity bug | If parity cannot be restored, report no perturbation number |
| 5 | **C1 continuous execution** | sim | Do learned differences survive whole admitted references rather than 3 s windows? | ~1 GPU-day | Blocked on missing frame-level screen provenance, not compute |
| 6 | **Tethered bench, then identification** | hardware | Does the exported policy behave as the simulator predicts, and what are the robot's real delay and torque envelope? | operator sessions | Any uncommanded actuator behaviour stops the rung |
| 7 | **Screen validity on hardware** | hardware | Do flagged references fail earlier than matched unflagged ones on a real G1? | a study of its own | Stop on any safety event; report every attempt |

**Rung 1 is first because it can invalidate everything above it.** The upstream hardware-oriented
G1 tracking configuration registers with `has_state_estimation=False`, which strips
`motion_anchor_pos_b` and `base_lin_vel` from the actor group precisely because a robot cannot
measure them. `climb/` never sets that flag, so it inherits `True` and every policy in this project
consumes both terms. That is four lines of code and it is the sharpest deployment fact we have.

**Rung 2 has been run, and it refuted its own registered prediction.** `refeas`'s own
`g1_flat.xml` carries `forcerange="-139 139"` on both knees and hip rolls, the same limits as the
training model, so we re-screened all 900 Phase-G clips at 139, 120 and 90 N·m. The baseline
reproduced the published screen exactly (max delta 0.0 across 900 clips), and tightening left
**888 of 900 clips unchanged**, moving the flagged count from 99 to 98 with no clip newly flagged.
The design had predicted the flagged fraction could only rise; four clips fell, by up to 0.0236,
because the screen thresholds the *translational component* of a residual whose total the program
minimizes, so tightening redistributes slack between components. The lower-bound sentence was
withdrawn from the manuscript and the public page and replaced by this measurement.
Design `plan/ACTUATOR_SENSITIVITY_2026-09-08.md`; result
`reports/actuator_sensitivity_2026-09-08/result.json`.

**Rung 7 is screen validity, not the curriculum claim.** The project's positive asset is the
measurement line, so the reachable physical question is whether the instrument predicts failure on
a real robot. The allocation comparison is inconclusive, so there is no simulation result for a
hardware version of that question to confirm.

**The allocation claim is not reachable on hardware at all**, and the reason is worth stating: the
independent unit is the training seed pair, and robot time does not manufacture training seeds. At
the observed seed spread, resolving the +0.02 target would take roughly a dozen paired seeds *in
simulation* first.

**The trap to avoid:** doing rung 7 first because it is the exciting one. A hardware demonstration
of a policy whose simulation comparison is inconclusive would produce a video, not a result.

---

## 4. Standing rules (unchanged; they are why the evidence is trustworthy)

1. Seal before run; frozen analyzer dry-run on synthetic data before outcomes exist.
2. Every arm carries a manipulation check; a failed check is "not tested", never a null.
3. One status label per number; pending numbers do no load-bearing work, including in the
   abstract, the title, and on the public site.
4. Prevalence is per corpus-and-pipeline pairing.
5. Repair changes the target; any repaired-reference contrast reports the 2×2 decomposition.
6. Every background job writes a sentinel; every paper number has a path in `RESULTS_LOG.md`.
7. Simulation results are never written in hardware language.
8. **New:** an experiment that fails before its endpoint is a harness event, not a scientific
   one. Preserve it, diagnose it, and let a human decide whether the seal is revised.

---

## 5. Immediate actions

| # | action | owner | state |
|---|---|---|---|
| 1 | H1 contract revision | agent, delegated | **decided: not for this submission.** Page 8 holds 78 of ~120 lines; an integrated H1 needs ~119 including its figure, so it would cost ~45 lines that verification just established as necessary. H1 is rung 3, behind two free desk rungs. The ten training runs stay intact and hash-bound. |
| 2 | Publish the project page with the paper and the deployment ladder | done in this revision | — |
| 3 | Public links to the anonymized draft | agent, delegated | **decided: removed.** Five links across two archive pages replaced with inert "withheld during review" text. No `paper/icra/` path is reachable from any published page. |
| 4 | Apply the remaining lower-priority manuscript polish | agent | staged in `reports/fable_independent_verification_2026-09-07/audit_repair_plan.md` §2 |
| 5 | Commit and tag when the user asks | Linji | uncommitted by policy |

---

## 6. One line for the advisor

*The simulation paper is finished and honest: reference–physics misalignment is measurable at bank
scale and transfers across policies, and no allocation rule beat uniform on exact support at three
seeds. The one open loop is a harness bug that stopped H1 after its training completed. Everything
after that is the deployment gap, and this project has not yet run a single physical experiment.*
