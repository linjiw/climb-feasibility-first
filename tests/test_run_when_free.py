"""Regression tests for the shared-GPU launcher sentinels."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "tools/run_when_free.sh"


def _launcher_environment(tmp_path: Path) -> dict[str, str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    nvidia_smi = fake_bin / "nvidia-smi"
    nvidia_smi.write_text(
        """#!/bin/bash
case "$*" in
  *memory.total*) echo "1000" ;;
  *memory.used,utilization.gpu*) echo "100, 10" ;;
  *memory.used*) echo "240" ;;
  *) exit 2 ;;
esac
"""
    )
    nvidia_smi.chmod(0o755)
    return {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "GPU_TOTAL_MIB": "1000",
        "ATTEMPTS": "2",
        "POLL_S": "0.01",
        "VRAM_POLL_S": "0.01",
    }


def test_records_resource_sentinel_in_log(tmp_path: Path) -> None:
    log = tmp_path / "run.log"
    result = subprocess.run(
        [
            str(LAUNCHER),
            "500",
            str(log),
            "--",
            "bash",
            "-c",
            "sleep 0.08; echo TRAINING",
        ],
        env=_launcher_environment(tmp_path),
        text=True,
        capture_output=True,
        check=True,
    )

    payload = log.read_text()
    assert "LAUNCH attempt=1" in payload
    assert "TRAINING" in payload
    assert "DONE rc=0 attempt=1" in payload
    assert "gpu_hours=" in payload
    assert "baseline_vram_mib=100" in payload
    assert "peak_total_vram_mib=240" in payload
    assert "peak_delta_mib=140" in payload
    assert "DONE rc=0 attempt=1" in result.stdout


def test_oom_retry_keeps_both_attempts(tmp_path: Path) -> None:
    log = tmp_path / "retry.log"
    state = tmp_path / "attempt-count"
    worker = tmp_path / "worker.sh"
    worker.write_text(
        """#!/bin/bash
state=$1
count=0
if [ -f "$state" ]; then count=$(cat "$state"); fi
count=$((count + 1))
echo "$count" > "$state"
if [ "$count" -eq 1 ]; then
  echo "CUDA out of memory" >&2
  exit 1
fi
echo "SECOND_ATTEMPT_OK"
"""
    )
    worker.chmod(0o755)

    subprocess.run(
        [str(LAUNCHER), "500", str(log), "--", str(worker), str(state)],
        env=_launcher_environment(tmp_path),
        text=True,
        capture_output=True,
        check=True,
    )

    payload = log.read_text()
    assert payload.count("LAUNCH attempt=") == 2
    assert "ATTEMPT_DONE rc=1 status=oom attempt=1" in payload
    assert "CUDA out of memory" in payload
    assert "SECOND_ATTEMPT_OK" in payload
    assert "DONE rc=0 attempt=2" in payload
