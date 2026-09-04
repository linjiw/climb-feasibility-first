#!/bin/bash
# Gap-gated launcher for the shared NVIDIA GPU (model discovered at runtime).
# usage: tools/run_when_free.sh <need_MiB> <log> -- cmd...
#   env: ATTEMPTS (default 120 polls of 30 s), MAX_UTIL (default 60 %),
#        GPU_TOTAL_MIB (default from nvidia-smi), POLL_S (default 30),
#        VRAM_POLL_S (default 1)
# Gates on BOTH free memory and utilization so a probe or training arm never
# starts on top of a saturated foreign job; retries on CUDA OOM / Warp
# "Failed to allocate". Appends launch, retry, and DONE sentinels to the log.
# DONE includes elapsed GPU-hours and nvidia-smi baseline/peak total memory.
set -uo pipefail

if [ "$#" -lt 4 ] || [ "$3" != "--" ]; then
  echo "usage: $0 <need_MiB> <log> -- cmd..." >&2
  exit 2
fi

need=$1
log=$2
shift 3
if ! [[ "$need" =~ ^[1-9][0-9]*$ ]]; then
  echo "need_MiB must be a positive integer" >&2
  exit 2
fi

total=${GPU_TOTAL_MIB:-$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)}
max_util=${MAX_UTIL:-60}
poll=${POLL_S:-30}
vram_poll=${VRAM_POLL_S:-1}
mkdir -p "$(dirname "$log")"
: > "$log"

sampler_pid=""
vram_file=""
attempt_file=""

stop_sampler() {
  if [ -n "$sampler_pid" ]; then
    kill "$sampler_pid" 2>/dev/null || true
    wait "$sampler_pid" 2>/dev/null || true
    sampler_pid=""
  fi
}

cleanup() {
  stop_sampler
  if [ -n "$vram_file" ]; then
    rm -f -- "$vram_file"
  fi
  if [ -n "$attempt_file" ]; then
    rm -f -- "$attempt_file"
  fi
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

for attempt in $(seq 1 "${ATTEMPTS:-120}"); do
  read -r used util <<< "$(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits | head -1 | tr -d ',')"
  free=$(( total - used ))
  if [ "$free" -ge "$need" ] && [ "$util" -le "$max_util" ]; then
    launch="LAUNCH attempt=$attempt free_mib=$free util_pct=$util baseline_vram_mib=$used $(date -Is)"
    echo "$launch" | tee -a "$log"
    vram_file=$(mktemp "${log}.vram.XXXXXX")
    attempt_file=$(mktemp "${log}.attempt.XXXXXX")
    echo "$used" > "$vram_file"
    (
      while true; do
        sample=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')
        if [[ "$sample" =~ ^[0-9]+$ ]]; then
          echo "$sample" >> "$vram_file"
        fi
        sleep "$vram_poll"
      done
    ) &
    sampler_pid=$!
    start_epoch=$(date +%s)
    MUJOCO_GL=egl nice -n 5 "$@" 2>&1 | tee -a "$log" "$attempt_file" >/dev/null
    rc=${PIPESTATUS[0]}
    end_epoch=$(date +%s)
    stop_sampler

    peak=$(sort -n "$vram_file" | tail -1)
    elapsed_s=$(( end_epoch - start_epoch ))
    gpu_hours=$(awk -v seconds="$elapsed_s" 'BEGIN {printf "%.6f", seconds / 3600}')
    peak_delta=$(( peak - used ))
    if grep -qiE "out of memory|failed to allocate" "$attempt_file"; then
      retry="ATTEMPT_DONE rc=$rc status=oom attempt=$attempt elapsed_s=$elapsed_s gpu_hours=$gpu_hours baseline_vram_mib=$used peak_total_vram_mib=$peak peak_delta_mib=$peak_delta $(date -Is)"
      echo "$retry" | tee -a "$log"
      rm -f -- "$vram_file" "$attempt_file"
      vram_file=""
      attempt_file=""
      sleep "$poll"
      continue
    fi
    done_line="DONE rc=$rc attempt=$attempt elapsed_s=$elapsed_s gpu_hours=$gpu_hours baseline_vram_mib=$used peak_total_vram_mib=$peak peak_delta_mib=$peak_delta $(date -Is)"
    echo "$done_line" | tee -a "$log"
    exit "$rc"
  fi
  sleep "$poll"
done
gave_up="GAVE_UP polls=${ATTEMPTS:-120} $(date -Is)"
echo "$gave_up" | tee -a "$log"
exit 1
