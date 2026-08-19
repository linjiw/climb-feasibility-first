#!/bin/bash
# with_sentinel.sh <report_dir> -- cmd...   Runs cmd; writes <report_dir>/COMPLETED or FAILED
# with exit code + UTC timestamps. Policy: every background job uses this (GLOBAL_EVAL_ADDENDUM).
set -u
DIR=$1; shift; [ "$1" = "--" ] && shift
mkdir -p "$DIR"
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
"$@"
RC=$?
NAME=$([ $RC -eq 0 ] && echo COMPLETED || echo FAILED)
{ echo "exit_code=$RC"; echo "started_utc=$START"; echo "finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"; echo "cmd=$*"; } > "$DIR/$NAME"
exit $RC
