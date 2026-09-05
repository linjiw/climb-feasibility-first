#!/bin/bash
# Run the approved Phase-G seed-1 G1/G2 arms, then stop at the ledger-only gate.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PY="$ROOT/mjlab-1.6.0/.venv/bin/python"
SEAL="$ROOT/plan/G_SEGMENT_FREEZE.sha256"
RUN_ROOT="$ROOT/reports/g_segment/confirmation/seed1"
TRAIN_ROOT="$RUN_ROOT/training"
LOG_ROOT="$RUN_ROOT/logs"
DRY_RUN=0

if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
  shift
fi
if [ "$#" -ne 0 ]; then
  echo "usage: $0 [--dry-run]" >&2
  exit 2
fi
for name in CLIMB_BANK CLIMB_CLIPS CLIMB_SEGMENT_MANIFEST; do
  if [ -z "${!name:-}" ]; then
    echo "source research.env first; missing $name" >&2
    exit 2
  fi
done
if [ ! -f "$SEAL" ]; then
  echo "Phase-G seal is absent: $SEAL" >&2
  exit 2
fi
(cd "$ROOT" && sha256sum -c plan/G_SEGMENT_FREEZE.sha256)

export CLIMB_SEGMENT_SEED=1
export CLIMB_SEGMENT_RANK=learning_progress
export CLIMB_SEGMENT_DIFFICULTY_POWER=0
export CLIMB_SEGMENT_EXPLORATION_RATIO=0.40
export CLIMB_SEGMENT_PROGRESS_WINDOW=10
export CLIMB_SEGMENT_PROGRESS_FLOOR=0.05
export CLIMB_SEGMENT_MAX_UNIT_PROBABILITY=0.05
export CLIMB_SEGMENT_MAX_CLIP_PROBABILITY=0.25
export CLIMB_SEGMENT_FAILURE_PENALTY=-10
export CLIMB_SEGMENT_SAVE_INTERVAL=500
export CLIMB_VERIFY_MOTION_HASHES=1
export WANDB_MODE=offline

(cd "$ROOT" && "$PY" tools/research_preflight.py \
  --g2-stage confirmation --verify-motion-hashes --strict)

mkdir -p "$TRAIN_ROOT" "$LOG_ROOT"

run_arm() {
  local arm=$1
  local task=$2
  local run_name=$3
  local log="$LOG_ROOT/${run_name}.log"
  local parent="$TRAIN_ROOT/g1_tracking"
  local command=(
    "$PY" "$ROOT/tools/climb_segment_train.py" "$task"
    --env.scene.num-envs 512
    --agent.max-iterations 4000
    --agent.logger tensorboard
    --agent.run-name "$run_name"
    --log-root "$TRAIN_ROOT"
  )
  if find "$parent" -mindepth 1 -maxdepth 1 -type d \
      -name "*_${run_name}" -print -quit 2>/dev/null | grep -q .; then
    echo "$arm run directory already exists; refusing an ambiguous rerun" >&2
    exit 2
  fi
  if [ -e "$log" ]; then
    echo "$arm launch log already exists: $log" >&2
    exit 2
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '%q ' "$ROOT/tools/run_when_free.sh" 14000 "$log" -- "${command[@]}"
    printf '\n'
    return
  fi
  "$ROOT/tools/run_when_free.sh" 14000 "$log" -- "${command[@]}"
  if ! grep -q '^DONE rc=0 ' "$log"; then
    echo "$arm lacks a successful durable sentinel" >&2
    exit 1
  fi
}

run_arm G1 Climb-Tracking-Flat-Unitree-G1-SegmentV2-Uniform phase_g_g1_s1
run_arm G2 Climb-Tracking-Flat-Unitree-G1-SegmentV2-Adaptive phase_g_g2_s1

if [ "$DRY_RUN" -eq 1 ]; then
  echo "dry run only; no training or endpoint access"
  exit 0
fi

resolve_complete_run() {
  local run_name=$1
  local candidate
  local complete=()
  while IFS= read -r candidate; do
    if [ -f "$candidate/model_0_segment.json" ] \
      && [ -f "$candidate/model_500_segment.json" ] \
      && [ -f "$candidate/model_1000_segment.json" ] \
      && [ -f "$candidate/model_1500_segment.json" ] \
      && [ -f "$candidate/model_2000_segment.json" ] \
      && [ -f "$candidate/model_2500_segment.json" ] \
      && [ -f "$candidate/model_3000_segment.json" ] \
      && [ -f "$candidate/model_3500_segment.json" ] \
      && [ -f "$candidate/model_3999_segment.json" ]; then
      complete+=("$candidate")
    fi
  done < <(find "$TRAIN_ROOT/g1_tracking" -mindepth 1 -maxdepth 1 -type d \
    -name "*_${run_name}" -print | sort)
  if [ "${#complete[@]}" -ne 1 ]; then
    echo "$run_name: expected one complete run, found ${#complete[@]}" >&2
    exit 1
  fi
  printf '%s\n' "${complete[0]}"
}

G1_DIR=$(resolve_complete_run phase_g_g1_s1)
G2_DIR=$(resolve_complete_run phase_g_g2_s1)
"$PY" "$ROOT/tools/check_g_seed1_manipulation.py" \
  --g1-run-dir "$G1_DIR" \
  --g2-run-dir "$G2_DIR" \
  --calibration-design "$ROOT/plan/G2_CALIBRATION_GRID.json" \
  --calibration-result "$ROOT/reports/g_segment/calibration/result.json" \
  --out "$RUN_ROOT/manipulation_result.json"

echo "Phase-G seed-1 training complete; stopped before evaluator endpoint access."
