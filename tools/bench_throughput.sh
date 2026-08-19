#!/usr/bin/env bash
# Sweep mjlab tracking throughput vs num_envs, recording steady-state iteration
# time and peak GPU memory. Peak memory is sampled from nvidia-smi rather than
# torch, because mujoco_warp allocates outside the torch caching allocator.
#
# Usage: bench_throughput.sh [MOTION_NPZ] [ITERS] [ENV_COUNTS...]
set -uo pipefail

MJLAB=/data/robotixx/climb/mjlab-1.6.0
MOTION=${1:-/tmp/mjlab_cache/lafan1_dance1_subject1_demo_motion.npz}
ITERS=${2:-30}
shift 2 2>/dev/null || true
ENVS=("$@")
[ ${#ENVS[@]} -eq 0 ] && ENVS=(1024 2048 4096 8192 16384)

OUT=/data/robotixx/climb/reports/throughput_$(date +%Y%m%d_%H%M%S).csv
echo "num_envs,iter_time_s,steps_per_s,peak_vram_mib,baseline_vram_mib,status" >"$OUT"
echo "writing $OUT"

BASE=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)

for n in "${ENVS[@]}"; do
  log=/tmp/climb_bench_${n}.log
  vram=/tmp/climb_vram_${n}.log
  : >"$vram"
  ( while true; do
      nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 >>"$vram"
      sleep 1
    done ) &
  sampler=$!

  ( cd "$MJLAB" && MUJOCO_GL=egl WANDB_MODE=offline timeout 3600 .venv/bin/train \
      Mjlab-Tracking-Flat-Unitree-G1 \
      --env.commands.motion.motion-file "$MOTION" \
      --env.scene.num-envs "$n" \
      --agent.max-iterations "$ITERS" \
      --agent.logger tensorboard \
      --agent.run-name "bench-$n" ) >"$log" 2>&1
  rc=$?
  kill $sampler 2>/dev/null; wait $sampler 2>/dev/null

  peak=$(sort -n "$vram" | tail -1)
  # Drop the first half of the iterations: early ones carry JIT compilation.
  it=$(grep -oP 'Iteration time: \K[0-9.]+' "$log" | awk '{a[NR]=$1} END{if(NR<2){print (NR?a[1]:"");exit} s=0;c=0; for(i=int(NR/2)+1;i<=NR;i++){s+=a[i];c++} printf "%.4f", s/c}')
  if [ -z "$it" ]; then
    echo "$n,,,${peak:-},$BASE,FAIL(rc=$rc)" >>"$OUT"
    echo "  envs=$n  FAILED (rc=$rc) — see $log"
    tail -3 "$log" | sed 's/^/      /'
  else
    sps=$(awk -v n="$n" -v t="$it" 'BEGIN{printf "%.0f", n*24/t}')
    echo "$n,$it,$sps,$peak,$BASE,OK" >>"$OUT"
    echo "  envs=$n  iter=${it}s  ${sps} steps/s  peak=${peak}MiB"
  fi
done

echo; column -s, -t "$OUT"
