# CLIMB workspace

Working area for the grounded-adaptive-motion-curricula project
(`/home/robotixx/newton/fable.md`). Lives on `/data` because `/` is at 91%.

```
mjlab-1.6.0/   git worktree of mjlab @ v1.6.0 + .venv   <- the training stack
climb/         the mjlab extension — multi-clip motion bank + clip samplers
tools/         validator, bank builder, GMR shim, ground aligner,
               throughput bench, difficulty featurizer, plausibility screen,
               train launcher, per-clip evaluator, RQ1 analysis
bank/          converted, validated motion .npz (mjlab tracking schema)
  lafan1/          40 clips,  2.45 h  (whole_body_tracking retarget, 30 fps)
  lafan1_gmr/      77 clips,  4.60 h  (GMR retarget, 30 fps — 14 extra families)
  amass/       10,705 clips, 36.56 h  (AMASS retarget, mixed fps, ground-aligned)
  tiers/           clean.txt + tier_{50,200,800}.txt from screen_bank.py
  csv/lafan1_gmr/  intermediate CSVs produced by the GMR shim
runs/ logs/ reports/

reports/       SETUP_AND_FINDINGS.md, climb_phase_zero.html (published artifact),
               features_{lafan1,lafan1_gmr,amass}.csv, throughput_*.csv
```

`mjlab-1.6.0` is a **git worktree** of `/home/robotixx/mjlab`, checked out at
`origin/main` (v1.6.0). The user's own checkout, branch, uncommitted changes and
stash are untouched. Remove with
`git -C /home/robotixx/mjlab worktree remove /data/robotixx/climb/mjlab-1.6.0`.

## Read this before adding motions

Two ways to silently corrupt this bank, both of which produce files that load
cleanly and train to plausible-looking reward curves:

1. **Body order.** Every G1 `.npz` that predates this workspace is in Isaac Lab /
   PhysX breadth-first order; mjlab requires MuJoCo depth-first. Both are
   30 bodies × 29 joints, so nothing errors and every tracking target binds to
   the wrong link. mjlab has no assertion anywhere.
2. **Frame rate.** The AMASS retarget directory mixes 120/100/60/250/59/150 fps,
   encoded per filename. Converting it at one `--input-fps` retimes 59% of the
   bank, and every velocity is finite-differenced from that timing. Use
   `--infer-fps`.
3. **Root height.** Those same AMASS CSVs store root z *relative* (mean
   −0.004 m) while the LAFAN1 CSVs store it absolutely (+0.767 m). Converted
   as-is the robot is buried 0.75 m into the floor. Run `ground_align_bank.py`
   after building an AMASS-derived bank.

Always run: 

```bash
mjlab-1.6.0/.venv/bin/python tools/validate_motion_npz.py --dir bank/SOMEBANK --quiet
```

`build_motion_bank.py` runs this on every output and discards failures, so
anything already in `bank/` has passed.

## The CLIMB extension

`climb/` adds what mjlab lacks: a **multi-clip** motion bank. mjlab's
`MotionLoader` holds one clip and `MotionCommand` indexes it with a flat
`time_steps`; `MotionBank` concatenates all clips and keeps a per-clip offset
table, so `time_steps` becomes a global index and all ~20 accessors work
untouched. Only the clip axis is new — mjlab already samples the start frame
*within* a clip.

Registered tasks (importing `climb` registers them):

| task id | sampler |
|---|---|
| `Climb-Tracking-Flat-Unitree-G1` | uniform clip, uniform frame — the control arm |
| `Climb-Tracking-Flat-Unitree-G1-Adaptive` | clip ∝ failure EMA + ε/N — error-adaptive arm |

Uniform means uniform over *clips*, not frames: the bank spans 3.7 s to 264 s,
so frame-uniform would weight by duration and quietly make the control arm a
length-weighted curriculum.

The grounded sampler is deliberately not implemented — it needs a deployment
distribution to be grounded against, and that belongs in an experiment config.

```bash
cd /data/robotixx/climb

# train an arm (bank comes from CLIMB_CLIPS, so mjlab's whole CLI still works)
CLIMB_CLIPS=$PWD/bank/tiers/tier_50.txt CLIMB_BANK=$PWD/bank/amass \
MUJOCO_GL=egl WANDB_MODE=offline mjlab-1.6.0/.venv/bin/python tools/climb_train.py \
  Climb-Tracking-Flat-Unitree-G1 --env.scene.num-envs 4096 \
  --agent.max-iterations 4000 --agent.logger tensorboard

# measure per-clip difficulty from a checkpoint (also prints the SIM-D1 gate)
MUJOCO_GL=egl mjlab-1.6.0/.venv/bin/python tools/climb_eval.py \
  --checkpoint logs/.../model_4000.pt --clips bank/tiers/tier_50.txt \
  --bank bank/amass --episodes-per-clip 8 --out reports/eval_tier50.csv

# test H1: dynamic features vs kinematic magnitude vs clip length
mjlab-1.6.0/.venv/bin/python tools/analyze_rq1.py \
  --features reports/features_amass.csv --eval reports/eval_tier50.csv
```

## Common commands

```bash
cd /data/robotixx/climb/mjlab-1.6.0

# train
MUJOCO_GL=egl WANDB_MODE=offline .venv/bin/train Mjlab-Tracking-Flat-Unitree-G1 \
  --env.commands.motion.motion-file /data/robotixx/climb/bank/lafan1/walk1_subject1.npz \
  --env.scene.num-envs 4096 --agent.logger tensorboard

# build a bank -- LAFAN1 retargets are uniformly 30 fps
MUJOCO_GL=egl .venv/bin/python ../tools/build_motion_bank.py \
  --input-dir CSV_DIR --output-dir ../bank/NAME --input-fps 30

# ...but the AMASS retargets mix 120/100/60/250/59/150 fps in one directory,
# encoded per filename. ALWAYS pass --infer-fps there; a single rate silently
# retimes 59% of the bank. --input-fps is then only the fallback (GRAB = 120).
MUJOCO_GL=egl .venv/bin/python ../tools/build_motion_bank.py \
  --input-dir /data/robotixx/wbt/train_converted_complete \
  --output-dir ../bank/amass --input-fps 120 --infer-fps

# GMR .npz(qpos) -> mjlab CSV
.venv/bin/python ../tools/gmr_npz_to_csv.py --input-dir /data/robotixx/pairs/unitree_g1 \
  --output-dir ../bank/csv/lafan1_gmr

# ground-align an AMASS-derived bank (idempotent; skip for LAFAN1, which is
# already grounded and bit-equivalent to mjlab's published reference)
MUJOCO_GL=egl .venv/bin/python ../tools/ground_align_bank.py --bank ../bank/amass --dry-run
MUJOCO_GL=egl .venv/bin/python ../tools/ground_align_bank.py --bank ../bank/amass

# difficulty features (RQ1 atlas, offline half)
MUJOCO_GL=egl .venv/bin/python ../tools/featurize_motions.py \
  --bank ../bank/lafan1 --out ../reports/features_lafan1.csv

# screen for physical plausibility and emit difficulty-stratified tiers.
# 20.4% of the raw AMASS bank is geometrically valid but physically untrackable.
.venv/bin/python ../tools/screen_bank.py \
  --features ../reports/features_amass.csv --out-dir ../bank/tiers

# throughput / VRAM curve
../tools/bench_throughput.sh MOTION.npz 30 1024 2048 4096 8192 16384
```

Measured on this box: **4096 envs → 0.45 s/iter, 218k steps/s, 5.6 GiB peak,
≈3.8 h for a 30k-iteration run.** Full curve in `reports/`.

## Caveats

* `bank/lafan1` and `bank/lafan1_gmr` are two *different retargetings* of the
  same source motions and overlap on 40 names. Never mix them inside one
  experimental condition.
* `manifest.jsonl` in each bank dir records per-clip frames, duration, fps and
  the body-order statistics used to validate it.
* mjlab's own `csv_to_npz` writes to a hard-coded `/tmp/motion.npz` and uploads
  to W&B; `build_motion_bank.py` exists to avoid both while reusing mjlab's
  `MotionLoader` so the numerics stay identical (verified bit-equivalent to
  mjlab's published reference export).
