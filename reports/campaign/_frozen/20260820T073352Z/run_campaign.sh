#!/usr/bin/env bash
# Campaign launcher with a frozen execution copy (Research Plan v2 §7.2/§7.3).
#
# Bash reads a script incrementally by byte offset, so editing the file while it
# runs makes the shell resume mid-token. That happened once here: a live edit
# corrupted the loop tail and the driver died on a syntax error after the last
# cell. No data was lost, but only by luck.
#
# The fix is structural rather than disciplinary: this script copies itself and
# its fully-resolved configuration into the report directory, hashes both, and
# execs the copy. Editing the working tree afterwards cannot affect a run in
# flight, and a resumed run re-execs the same frozen bytes rather than
# re-resolving config that may have drifted (v2 §7.3 -- a resumed arm with a
# silently different epsilon or bank is exposure-hazard territory).
set -uo pipefail

R=/data/robotixx/climb
RUNTAG=${RUNTAG:-$(date -u +%Y%m%dT%H%M%SZ)}
FROZEN_DIR="$R/reports/campaign/_frozen/$RUNTAG"

if [ "${CLIMB_FROZEN:-0}" != "1" ]; then
  mkdir -p "$FROZEN_DIR"
  cp "$0" "$FROZEN_DIR/run_campaign.sh"
  {
    echo "RUNTAG=$RUNTAG"
    echo "ITERS=${ITERS:-4000}"
    echo "ENVS=${ENVS:-4096}"
    echo "SEEDS=\"${SEEDS:-1 2 3}\""
    echo "ARMS=\"${ARMS:-uniform adaptive}\""
    echo "EPISODES=${EPISODES:-8}"
    echo "TRAIN_CLIPS=${TRAIN_CLIPS:-$R/bank/tiers/tier_mixed100.txt}"
    echo "BANKTAG=${BANKTAG:-mixed100}"
    echo "EVAL_CLIPS=${EVAL_CLIPS:-$R/bank/tiers/heldout100.txt}"
    echo "BANK=${BANK:-$R/bank/amass}"
  } > "$FROZEN_DIR/config.env"
  ( cd "$FROZEN_DIR" && sha256sum run_campaign.sh config.env > checksums.txt )
  # Record the exact bank contents too: a clip list can be regenerated with a
  # different RNG and the run would otherwise look identical in the log.
  cp "${TRAIN_CLIPS:-$R/bank/tiers/tier_mixed100.txt}" "$FROZEN_DIR/train_clips.txt"
  cp "${EVAL_CLIPS:-$R/bank/tiers/heldout100.txt}" "$FROZEN_DIR/eval_clips.txt"
  echo "frozen launch copy: $FROZEN_DIR"
  exec env CLIMB_FROZEN=1 FROZEN_DIR="$FROZEN_DIR" \
       bash "$FROZEN_DIR/run_campaign.sh"
fi

# ---- from here on we are the frozen copy -------------------------------------
# shellcheck disable=SC1091
. "$FROZEN_DIR/config.env"
PY=$R/mjlab-1.6.0/.venv/bin/python

mkdir -p "$R/reports/campaign" "$R/logs/campaign"
echo "campaign[$RUNTAG]: arms={$ARMS} seeds={$SEEDS} iters=$ITERS envs=$ENVS"

for seed in $SEEDS; do
  for arm in $ARMS; do
    case $arm in
      uniform)  task=Climb-Tracking-Flat-Unitree-G1 ;;
      adaptive) task=Climb-Tracking-Flat-Unitree-G1-Adaptive ;;
      grounded) task=Climb-Tracking-Flat-Unitree-G1-Grounded ;;
      *) echo "unknown arm: $arm"; continue ;;
    esac
    name="${arm}-${BANKTAG:-mixed100}-s${seed}"
    log="$R/logs/campaign/${name}.log"

    run_dir=$(ls -d "$R"/logs/rsl_rl/g1_tracking/*"${name}" 2>/dev/null | tail -1)
    if [ -z "$run_dir" ] || [ ! -f "$run_dir/model_$((ITERS-1)).pt" ]; then
      echo "[train] $name"
      ( cd "$R" && CLIMB_CLIPS=$TRAIN_CLIPS CLIMB_BANK=$BANK \
        MUJOCO_GL=egl WANDB_MODE=offline "$PY" tools/climb_train.py "$task" \
          --env.scene.num-envs "$ENVS" --agent.max-iterations "$ITERS" \
          --agent.logger tensorboard --agent.seed "$seed" \
          --agent.run-name "$name" ) >"$log" 2>&1
      rc=$?
      run_dir=$(ls -d "$R"/logs/rsl_rl/g1_tracking/*"${name}" 2>/dev/null | tail -1)
      if [ $rc -ne 0 ] || [ -z "$run_dir" ]; then
        echo "  TRAIN FAILED (rc=$rc) — see $log"; tail -3 "$log" | sed 's/^/    /'; continue
      fi
      echo "$name $run_dir" >> "$FROZEN_DIR/runs.txt"
    else
      echo "[skip train] $name (already complete)"
    fi

    for ck in "$run_dir"/model_*.pt; do
      it=$(basename "$ck" .pt); it=${it#model_}
      out="$R/reports/campaign/${name}_it${it}.csv"
      [ -f "$out" ] && continue
      ( cd "$R" && MUJOCO_GL=egl "$PY" tools/climb_eval.py --checkpoint "$ck" \
          --clips "$EVAL_CLIPS" --bank "$BANK" --episodes-per-clip "$EPISODES" \
          --max-seconds 10 --start random --out "$out" ) \
        >>"$R/logs/campaign/${name}_eval.log" 2>&1 \
        && echo "  [eval] it=$it" || echo "  [eval] it=$it FAILED"
    done
  done
done

echo "done [$RUNTAG]. results in $R/reports/campaign/"
