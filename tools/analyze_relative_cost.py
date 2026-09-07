#!/usr/bin/env python3
"""Account for scoped execution logs, including failed or unlaunched attempts."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path

from check_relative_progress_probe import sha256


def fields(line: str) -> tuple[dict[str, str], datetime]:
    tokens = line.split()
    values = dict(token.split("=", 1) for token in tokens[1:-1])
    return values, datetime.fromisoformat(tokens[-1])


def execution_cost(log: str) -> dict:
    """Require one actual launch at most; elapsed GPU-hours are not utilization."""
    launches = [line for line in log.splitlines() if line.startswith("LAUNCH ")]
    finishes = [line for line in log.splitlines() if line.startswith(("DONE ", "ATTEMPT_DONE "))]
    gave_up = [line for line in log.splitlines() if line.startswith("GAVE_UP ")]
    if not launches:
        if len(gave_up) != 1 or finishes:
            raise ValueError("missing or ambiguous execution sentinels")
        values, end = fields(gave_up[0])
        if int(values["polls"]) <= 0:
            raise ValueError("invalid gate poll count")
        return {"status": "not_launched", "actual_launches": 0, "elapsed_s": 0,
                "elapsed_gpu_hours": 0.0, "gate_polls": int(values["polls"]),
                "finished": end.isoformat()}
    if len(launches) != 1 or len(finishes) != 1:
        raise ValueError("incomplete or repeated training launch; separate attempts explicitly")
    launch, start = fields(launches[0])
    done, end = fields(finishes[0])
    elapsed = int(done["elapsed_s"])
    hours = float(done["gpu_hours"])
    baseline = int(done["baseline_vram_mib"])
    peak = int(done["peak_total_vram_mib"])
    if (elapsed < 0 or not math.isfinite(hours) or hours < 0
            or abs(hours - elapsed / 3600) > 1e-6
            or abs((end - start).total_seconds() - elapsed) > 2
            or baseline < 0 or peak < baseline or int(done["peak_delta_mib"]) != peak - baseline
            or int(launch["baseline_vram_mib"]) != baseline
            or int(launch["attempt"]) < 1 or done["attempt"] != launch["attempt"]):
        raise ValueError("inconsistent execution cost telemetry")
    oom = finishes[0].startswith("ATTEMPT_DONE ")
    if oom and done.get("status") != "oom":
        raise ValueError("unknown attempt terminal status")
    if (not oom and gave_up) or len(gave_up) > 1:
        raise ValueError("contradictory gate and training terminal sentinels")
    rc = int(done["rc"])
    return {"status": "completed" if rc == 0 and not oom else "failed",
            "actual_launches": 1, "returncode": rc, "oom_reported": oom,
            "elapsed_s": elapsed, "elapsed_gpu_hours": elapsed / 3600,
            "shared_gpu_baseline_mib": baseline, "shared_gpu_peak_total_mib": peak,
            "started": start.isoformat(), "finished": end.isoformat()}


def summarize(paths: dict[str, Path], scope: str) -> dict:
    """Retain every supplied attempt; callers must define the coverage scope."""
    if not paths or not scope.strip():
        raise ValueError("named logs and an explicit cost scope are required")
    runs = {name: {**execution_cost(path.read_text()), "log": str(path.resolve()),
                   "log_sha256": sha256(path)} for name, path in paths.items()}
    return {"schema_version": "relative_execution_cost/1", "classification": "measured execution cost only",
            "scope": scope, "runs": runs,
            "total_elapsed_s": sum(row["elapsed_s"] for row in runs.values()),
            "total_elapsed_gpu_hours": sum(row["elapsed_gpu_hours"] for row in runs.values()),
            "analyzer_sha256": sha256(Path(__file__)), "policy_endpoints_opened": False,
            "limitations": ["Elapsed GPU-hours are wall time while a job runs, not GPU-active time or energy.",
                            "Memory values cover the shared device, not an isolated process.",
                            "Only the named logs are included; queue time, engineering, and omitted studies are excluded."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", action="append", required=True, help="Unique label=log_path; repeat per attempt")
    parser.add_argument("--scope", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    pairs = [item.split("=", 1) for item in args.log]
    if any(len(pair) != 2 for pair in pairs) or len({pair[0] for pair in pairs}) != len(pairs):
        parser.error("logs require unique label=path arguments")
    result = summarize({label: Path(path) for label, path in pairs}, args.scope)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({key: result[key] for key in ("scope", "total_elapsed_gpu_hours")}))
