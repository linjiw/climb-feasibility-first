#!/bin/bash
# Gap-gated launcher for the shared NVIDIA GPU (model discovered at runtime).
# usage: tools/run_when_free.sh <need_MiB> <log> -- cmd...
#   env: ATTEMPTS (default 120 polls of 30 s), MAX_UTIL (default 60 %),
#        GPU_TOTAL_MIB (default from nvidia-smi), POLL_S (default 30)
# Gates on BOTH free memory and utilization so a probe or training arm never
# starts on top of a saturated foreign job; retries on CUDA OOM / Warp
# "Failed to allocate". Writes a sentinel line "DONE rc=..." on completion.
set -u
need=$1; log=$2; shift 3
total=${GPU_TOTAL_MIB:-$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)}
max_util=${MAX_UTIL:-60}
poll=${POLL_S:-30}
for attempt in $(seq 1 "${ATTEMPTS:-120}"); do
  read -r used util <<< "$(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits | head -1 | tr -d ',')"
  free=$(( total - used ))
  if [ "$free" -ge "$need" ] && [ "$util" -le "$max_util" ]; then
    echo "attempt $attempt: launching (free ${free}MiB, util ${util}%) $(date -Is)"
    ( MUJOCO_GL=egl nice -n 5 "$@" ) > "$log" 2>&1
    rc=$?
    if grep -qiE "out of memory|failed to allocate" "$log"; then
      echo "attempt $attempt: OOM (free was ${free}MiB), retrying"; sleep "$poll"; continue
    fi
    echo "DONE rc=$rc attempt=$attempt $(date -Is)"; exit "$rc"
  fi
  sleep "$poll"
done
echo "GAVE UP after ${ATTEMPTS:-120} polls $(date -Is)"; exit 1
