#!/usr/bin/env bash
# Sealed FGAS campaign: soft guard-0 eligibility versus grounded baseline.
set -euo pipefail

R=/data/robotixx/climb
PY=$R/mjlab-1.6.0/.venv/bin/python
TRAIN_CLIPS=$R/bank/tiers/tier_mixed100.txt
EVAL_CLIPS=$R/bank/tiers/heldout100.txt
HARD_CLIPS=$R/bank/tiers/fgas_feasible_hard20.txt
BANK=$R/bank/amass
ELIGIBILITY=$R/reports/eligibility/tier_mixed100_guard0_bin50
ITERS=${ITERS:-4000}
ENVS=${ENVS:-4096}
SEEDS=${SEEDS:-"1 2 3"}
EPISODES=${EPISODES:-8}
MIN_FREE_MIB=${MIN_FREE_MIB:-14336}
RUNTAG=${RUNTAG:-$(date -u +%Y%m%dT%H%M%SZ)}
FROZEN_DIR=$R/reports/FGAS/_frozen/$RUNTAG

if [ "${CLIMB_FROZEN:-0}" != "1" ]; then
  mkdir -p "$FROZEN_DIR" "$R/reports/FGAS" "$R/logs/campaign"
  cp "$0" "$FROZEN_DIR/run_fgas_campaign.sh"
  {
    echo "RUNTAG=$RUNTAG"
    echo "ITERS=$ITERS"
    echo "ENVS=$ENVS"
    echo "SEEDS=\"$SEEDS\""
    echo "EPISODES=$EPISODES"
    echo "MIN_FREE_MIB=$MIN_FREE_MIB"
    echo "TRAIN_CLIPS=$TRAIN_CLIPS"
    echo "EVAL_CLIPS=$EVAL_CLIPS"
    echo "HARD_CLIPS=$HARD_CLIPS"
    echo "BANK=$BANK"
    echo "ELIGIBILITY=$ELIGIBILITY"
    echo "ELIGIBILITY_MODE=soft"
    echo "TASK=Climb-Tracking-Flat-Unitree-G1-Grounded"
  } > "$FROZEN_DIR/config.env"
  cp "$TRAIN_CLIPS" "$FROZEN_DIR/train_clips.txt"
  cp "$EVAL_CLIPS" "$FROZEN_DIR/eval_clips.txt"
  cp "$HARD_CLIPS" "$FROZEN_DIR/feasible_hard20.txt"
  sha256sum \
    "$FROZEN_DIR/run_fgas_campaign.sh" \
    "$FROZEN_DIR/config.env" \
    "$R/climb/commands.py" \
    "$R/climb/eligibility.py" \
    "$R/tools/analyze_fgas.py" \
    "$ELIGIBILITY/manifest.json" \
    > "$FROZEN_DIR/checksums.txt"
  echo "frozen FGAS launch: $FROZEN_DIR"
  exec env CLIMB_FROZEN=1 FROZEN_DIR="$FROZEN_DIR" \
    bash "$FROZEN_DIR/run_fgas_campaign.sh"
fi

# shellcheck disable=SC1091
. "$FROZEN_DIR/config.env"
cd "$R"

if pgrep -af 'tools/climb_train.py' | grep -v "$$" >/dev/null; then
  echo "FGAS gate: another climb_train.py process is active; leaving priority to it"
  exit 75
fi

if ! gpu_rows=$(nvidia-smi --query-gpu=index,memory.free \
  --format=csv,noheader,nounits); then
  echo "FGAS gate: NVIDIA driver is unavailable"
  exit 75
fi
gpu_row=$(echo "$gpu_rows" | sort -t, -k2 -nr | head -1)
gpu=${gpu_row%%,*}
free_mib=${gpu_row##*,}
gpu=$(echo "$gpu" | xargs)
free_mib=$(echo "$free_mib" | xargs)
if [ -z "$gpu" ] || [ "$free_mib" -lt "$MIN_FREE_MIB" ]; then
  echo "FGAS gate: best GPU has ${free_mib:-0} MiB free; need $MIN_FREE_MIB MiB"
  exit 75
fi
echo "FGAS gate: using physical GPU $gpu with $free_mib MiB free"

for seed in $SEEDS; do
  name=fgas-soft-mixed100-s${seed}
  log=$R/logs/campaign/$name.log
  run_dir=$(ls -d "$R"/logs/rsl_rl/g1_tracking/*"$name" 2>/dev/null | tail -1 || true)
  if [ -z "$run_dir" ] || [ ! -f "$run_dir/model_$((ITERS - 1)).pt" ]; then
    echo "[train] $name"
    CLIMB_CLIPS=$TRAIN_CLIPS \
      CLIMB_BANK=$BANK \
      CLIMB_ELIGIBILITY_PATH=$ELIGIBILITY \
      CLIMB_ELIGIBILITY_MODE=soft \
      CUDA_VISIBLE_DEVICES=$gpu \
      MUJOCO_GL=egl \
      WANDB_MODE=offline \
      "$PY" "$R/tools/climb_train.py" Climb-Tracking-Flat-Unitree-G1-Grounded \
        --env.scene.num-envs "$ENVS" \
        --agent.max-iterations "$ITERS" \
        --agent.logger tensorboard \
        --agent.seed "$seed" \
        --agent.run-name "$name" \
        > "$log" 2>&1
    run_dir=$(ls -d "$R"/logs/rsl_rl/g1_tracking/*"$name" 2>/dev/null | tail -1)
    test -f "$run_dir/model_$((ITERS - 1)).pt"
    echo "$name $run_dir" >> "$FROZEN_DIR/runs.txt"
  else
    echo "[skip train] $name"
  fi

  for checkpoint in "$run_dir"/model_*.pt; do
    iteration=$(basename "$checkpoint" .pt)
    iteration=${iteration#model_}
    out=$R/reports/campaign/${name}_it${iteration}.csv
    if [ ! -f "$out" ]; then
      CUDA_VISIBLE_DEVICES=$gpu MUJOCO_GL=egl "$PY" "$R/tools/climb_eval.py" \
        --checkpoint "$checkpoint" \
        --clips "$EVAL_CLIPS" \
        --bank "$BANK" \
        --episodes-per-clip "$EPISODES" \
        --max-seconds 10 \
        --start random \
        --out "$out" \
        >> "$R/logs/campaign/${name}_eval.log" 2>&1
      echo "  [eval] $name iteration $iteration"
    fi
  done

  final=$run_dir/model_$((ITERS - 1)).pt
  method_strat=$R/reports/FGAS/${name}_hard20_strat.csv
  if [ ! -f "$method_strat" ]; then
    CUDA_VISIBLE_DEVICES=$gpu MUJOCO_GL=egl "$PY" "$R/tools/eval_stratified.py" \
      --checkpoint "$final" \
      --clips "$HARD_CLIPS" \
      --bank "$BANK" \
      --offsets 0,1,2,3,4,6,8 \
      --window 3 \
      --episodes 8 \
      --seed "$seed" \
      --out "$method_strat" \
      > "$R/logs/campaign/${name}_hard20_strat.log" 2>&1
  fi

  baseline_dir=$(ls -d \
    "$R"/logs/rsl_rl/g1_tracking/*"grounded-mixed100-s${seed}" \
    2>/dev/null | tail -1)
  baseline_strat=$R/reports/FGAS/grounded-mixed100-s${seed}_hard20_strat.csv
  if [ ! -f "$baseline_strat" ]; then
    CUDA_VISIBLE_DEVICES=$gpu MUJOCO_GL=egl "$PY" "$R/tools/eval_stratified.py" \
      --checkpoint "$baseline_dir/model_3999.pt" \
      --clips "$HARD_CLIPS" \
      --bank "$BANK" \
      --offsets 0,1,2,3,4,6,8 \
      --window 3 \
      --episodes 8 \
      --seed "$seed" \
      --out "$baseline_strat" \
      > "$R/logs/campaign/grounded-mixed100-s${seed}_hard20_strat.log" 2>&1
  fi
done

"$PY" "$R/tools/analyze_fgas.py" --root "$R" --out "$R/reports/FGAS_result.json" \
  > "$R/logs/campaign/fgas_analysis.log"
touch "$R/reports/FGAS/COMPLETED"
echo "FGAS complete: $R/reports/FGAS_result.json"
