#!/usr/bin/env bash
# Sealed N7 repair-all training and cross-reference evaluation.
set -euo pipefail

R=/data/robotixx/climb
PY=$R/mjlab-1.6.0/.venv/bin/python
TRAIN_CLIPS=$R/bank/tiers/tier_800_repaired.txt
RAW_BANK=$R/bank/amass
REPAIRED_BANK=$R/bank/amass_repaired800
FLAGGED=$R/bank/tiers/tier_800_flagged99.txt
HELDOUT=$R/bank/tiers/heldout100.txt
GROUND=$R/bank/tiers/zs_ground_feasible.txt
ITERS=${ITERS:-4000}
ENVS=${ENVS:-4096}
MIN_FREE_MIB=${MIN_FREE_MIB:-14336}
RUNTAG=${RUNTAG:-$(date -u +%Y%m%dT%H%M%SZ)}
FROZEN_DIR=$R/reports/N7/_frozen/$RUNTAG

if [ "${CLIMB_FROZEN:-0}" != "1" ]; then
  mkdir -p "$FROZEN_DIR" "$R/reports/N7" "$R/logs/campaign"
  cp "$0" "$FROZEN_DIR/run_n7_campaign.sh"
  {
    echo "RUNTAG=$RUNTAG"
    echo "ITERS=$ITERS"
    echo "ENVS=$ENVS"
    echo "MIN_FREE_MIB=$MIN_FREE_MIB"
    echo "TRAIN_CLIPS=$TRAIN_CLIPS"
    echo "RAW_BANK=$RAW_BANK"
    echo "REPAIRED_BANK=$REPAIRED_BANK"
    echo "FLAGGED=$FLAGGED"
    echo "HELDOUT=$HELDOUT"
    echo "GROUND=$GROUND"
    echo "SEED=1"
    echo "TASK=Climb-Tracking-Flat-Unitree-G1"
  } > "$FROZEN_DIR/config.env"
  cp "$TRAIN_CLIPS" "$FROZEN_DIR/train_clips.txt"
  cp "$FLAGGED" "$FROZEN_DIR/flagged99.txt"
  sha256sum \
    "$FROZEN_DIR/run_n7_campaign.sh" \
    "$FROZEN_DIR/config.env" \
    "$R/tools/analyze_n7.py" \
    "$R/reports/repaired800/manifest.json" \
    > "$FROZEN_DIR/checksums.txt"
  echo "frozen N7 launch: $FROZEN_DIR"
  exec env CLIMB_FROZEN=1 FROZEN_DIR="$FROZEN_DIR" \
    bash "$FROZEN_DIR/run_n7_campaign.sh"
fi

# shellcheck disable=SC1091
. "$FROZEN_DIR/config.env"
cd "$R"

if [ ! -e "$R/reports/FGAS/COMPLETED" ]; then
  echo "N7 gate: FGAS primary campaign has priority and is not complete"
  exit 75
fi
if pgrep -af 'tools/climb_train.py' | grep -v "$$" >/dev/null; then
  echo "N7 gate: another climb_train.py process is active"
  exit 75
fi
if ! gpu_rows=$(nvidia-smi --query-gpu=index,memory.free \
  --format=csv,noheader,nounits); then
  echo "N7 gate: NVIDIA driver is unavailable"
  exit 75
fi
gpu_row=$(echo "$gpu_rows" | sort -t, -k2 -nr | head -1)
gpu=$(echo "${gpu_row%%,*}" | xargs)
free_mib=$(echo "${gpu_row##*,}" | xargs)
if [ -z "$gpu" ] || [ "$free_mib" -lt "$MIN_FREE_MIB" ]; then
  echo "N7 gate: best GPU has ${free_mib:-0} MiB free; need $MIN_FREE_MIB MiB"
  exit 75
fi

name=uniform-amass800r-s1
log=$R/logs/campaign/$name.log
run_dir=$(ls -d "$R"/logs/rsl_rl/g1_tracking/*"$name" 2>/dev/null | tail -1 || true)
if [ -z "$run_dir" ] || [ ! -f "$run_dir/model_$((ITERS - 1)).pt" ]; then
  CLIMB_CLIPS=$TRAIN_CLIPS \
    CLIMB_BANK=$REPAIRED_BANK \
    CUDA_VISIBLE_DEVICES=$gpu \
    MUJOCO_GL=egl \
    WANDB_MODE=offline \
    "$PY" "$R/tools/climb_train.py" Climb-Tracking-Flat-Unitree-G1 \
      --env.scene.num-envs "$ENVS" \
      --agent.max-iterations "$ITERS" \
      --agent.logger tensorboard \
      --agent.seed 1 \
      --agent.run-name "$name" \
      > "$log" 2>&1
  run_dir=$(ls -d "$R"/logs/rsl_rl/g1_tracking/*"$name" | tail -1)
  test -f "$run_dir/model_$((ITERS - 1)).pt"
  echo "$name $run_dir" >> "$FROZEN_DIR/runs.txt"
fi

keep_dir=$(ls -d "$R"/logs/rsl_rl/g1_tracking/*uniform-amass800-s1 | tail -1)
keep_ck=$keep_dir/model_3999.pt
repair_ck=$run_dir/model_$((ITERS - 1)).pt

evaluate() {
  local checkpoint=$1
  local clips=$2
  local bank=$3
  local out=$4
  [ -f "$out" ] && return
  CUDA_VISIBLE_DEVICES=$gpu MUJOCO_GL=egl "$PY" "$R/tools/eval_stratified.py" \
    --checkpoint "$checkpoint" \
    --clips "$clips" \
    --bank "$bank" \
    --offsets 0,1,2,3,4,6,8 \
    --window 3 \
    --episodes 8 \
    --seed 0 \
    --out "$out" \
    >> "$R/logs/campaign/n7_evals.log" 2>&1
}

evaluate "$keep_ck" "$FLAGGED" "$RAW_BANK" \
  "$R/reports/N7/keep_policy_raw_reference_flagged99.csv"
evaluate "$keep_ck" "$FLAGGED" "$REPAIRED_BANK" \
  "$R/reports/N7/keep_policy_repaired_reference_flagged99.csv"
evaluate "$repair_ck" "$FLAGGED" "$RAW_BANK" \
  "$R/reports/N7/repair_policy_raw_reference_flagged99.csv"
evaluate "$repair_ck" "$FLAGGED" "$REPAIRED_BANK" \
  "$R/reports/N7/repair_policy_repaired_reference_flagged99.csv"
evaluate "$repair_ck" "$HELDOUT" "$RAW_BANK" \
  "$R/reports/N7/repair_policy_heldout100.csv"
evaluate "$repair_ck" "$GROUND" "$RAW_BANK" \
  "$R/reports/N7/repair_policy_zs_ground.csv"

"$PY" "$R/tools/analyze_n7.py" --root "$R" --out "$R/reports/N7_result.json" \
  > "$R/logs/campaign/n7_analysis.log"
touch "$R/reports/N7/COMPLETED"
echo "N7 complete: $R/reports/N7_result.json"
