#!/usr/bin/env bash
# Uniform vs adaptive clip sampling, compute-matched, on a headroom-passing bank.
#
# Trains every (arm, seed) cell then evaluates every saved checkpoint against a
# held-out, difficulty-matched bank. Evaluating the whole checkpoint ladder --
# not just the final model -- is what makes the comparison compute-matched: the
# plan's claim is about performance per GPU-hour, which is a learning curve, and
# a single endpoint cannot distinguish "faster" from "better".
#
# Resumable: a cell whose eval CSV already exists is skipped.
set -uo pipefail

R=/data/robotixx/climb
PY=$R/mjlab-1.6.0/.venv/bin/python
TRAIN_CLIPS=$R/bank/tiers/tier_mixed100.txt
EVAL_CLIPS=$R/bank/tiers/heldout100.txt
BANK=$R/bank/amass
ITERS=${ITERS:-4000}
ENVS=${ENVS:-4096}
SEEDS=${SEEDS:-"1 2 3"}
ARMS=${ARMS:-"uniform adaptive"}
EPISODES=${EPISODES:-8}

mkdir -p "$R/reports/campaign" "$R/logs/campaign"
echo "campaign: arms={$ARMS} seeds={$SEEDS} iters=$ITERS envs=$ENVS"

for seed in $SEEDS; do
  for arm in $ARMS; do
    case $arm in
      uniform)  task=Climb-Tracking-Flat-Unitree-G1 ;;
      adaptive) task=Climb-Tracking-Flat-Unitree-G1-Adaptive ;;
      grounded) task=Climb-Tracking-Flat-Unitree-G1-Grounded ;;
    esac
    name="${arm}-mixed100-s${seed}"
    log="$R/logs/campaign/${name}.log"

    # Find an existing run dir for this cell before training again.
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
        && echo "  [eval] it=$it -> $(basename "$out")" \
        || echo "  [eval] it=$it FAILED"
    done
  done
done

echo "done. results in $R/reports/campaign/"
