"""Cost accounting must not discard failed attempts or call queue time GPU use."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from analyze_relative_cost import execution_cost, summarize

LAUNCH = "LAUNCH attempt=1 free_mib=15000 util_pct=5 baseline_vram_mib=1000 2026-09-05T18:00:00-04:00\n"
DONE = "DONE rc=0 attempt=1 elapsed_s=36 gpu_hours=0.010000 baseline_vram_mib=1000 peak_total_vram_mib=12000 peak_delta_mib=11000 2026-09-05T18:00:36-04:00\n"
GATE = "GAVE_UP polls=1 2026-09-05T18:01:06-04:00\n"


def test_success_uses_elapsed_cost_and_shared_memory():
    result = execution_cost(LAUNCH + DONE)
    assert result["status"] == "completed"
    assert result["elapsed_gpu_hours"] == pytest.approx(0.01)
    assert result["shared_gpu_peak_total_mib"] == 12000


def test_gate_miss_has_no_training_cost():
    result = execution_cost(GATE)
    assert result["actual_launches"] == 0
    assert result["elapsed_gpu_hours"] == 0


def test_failed_and_oom_attempts_keep_cost(tmp_path):
    failed = tmp_path / "failed.log"
    oom = tmp_path / "oom.log"
    failed.write_text(LAUNCH + DONE.replace("rc=0", "rc=1"))
    oom.write_text(LAUNCH + DONE.replace("DONE rc=0", "ATTEMPT_DONE status=oom rc=1") + GATE)
    result = summarize({"failed": failed, "oom": oom}, "two synthetic failed attempts")
    assert result["total_elapsed_gpu_hours"] == pytest.approx(0.02)
    assert all(row["status"] == "failed" for row in result["runs"].values())


@pytest.mark.parametrize("log", ["", LAUNCH, LAUNCH + DONE + LAUNCH + DONE,
                                 LAUNCH + DONE.replace("0.010000", "0.020000"),
                                 LAUNCH + DONE.replace("peak_delta_mib=11000", "peak_delta_mib=0"),
                                 LAUNCH + DONE.replace("18:00:36", "18:03:36"), LAUNCH + DONE + GATE])
def test_ambiguous_or_inconsistent_logs_rejected(log):
    with pytest.raises(ValueError):
        execution_cost(log)
