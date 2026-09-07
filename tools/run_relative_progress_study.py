#!/usr/bin/env python3
"""Run the fixed relative-ALP smoke/long sequence with durable stop decisions."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys

from check_relative_progress_probe import check_run, sha256

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "mjlab-1.6.0/.venv/bin/python"
TASK = "Climb-Tracking-Flat-Unitree-G1-RelativeALP-Probe"


def write_once(path: Path, payload: dict) -> None:
    with path.open("x") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, choices=(11, 12), default=11)
    parser.add_argument("--smoke-result", type=Path)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, CLIMB_BANK=str(ROOT / "bank/amass"),
               CLIMB_CLIPS=str(ROOT / "bank/tiers/tier_800.txt"),
               CLIMB_SEGMENT_MANIFEST=str(ROOT / "reports/g_segment/unit_table.json"),
               CLIMB_RELATIVE_SEED=str(args.seed), WANDB_MODE="offline", MUJOCO_GL="egl",
               ATTEMPTS="1")
    # One gate attempt avoids automatically repeating a scientific run after OOM.
    sources = ["tools/run_relative_progress_study.py", "tools/check_relative_progress_probe.py",
               "tools/train_relative_progress_probe.py", "climb/relative_progress.py",
               "plan/RESEARCH_DESIGN_RELATIVE_PROGRESS_2026-09-05.md",
               "plan/RELATIVE_ALP_PROBE_2026-09-05.md", "plan/G_SEGMENT_FREEZE.sha256"]
    design = {"schema_version": "relative_progress_execution/1", "seed": args.seed,
              "task": TASK, "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "sources": {name: sha256(ROOT / name) for name in sources},
              "environment": {key: env[key] for key in env if key.startswith("CLIMB_")},
              "stages": ["smoke", "long"], "policy_endpoints_opened": False}
    write_once(out / "design.json", design)
    try:
        subprocess.run(["sha256sum", "--status", "-c", "plan/G_SEGMENT_FREEZE.sha256"],
                       cwd=ROOT, check=True)
        for stage, num_envs, iterations in (("smoke", 8, 20), ("long", 512, 4000)):
            if stage == "smoke" and args.smoke_result:
                previous = json.loads(args.smoke_result.read_text())
                run_dir = Path(next(iter(previous["bindings"]))).parent
                result = check_run(run_dir, Path(env["CLIMB_SEGMENT_MANIFEST"]),
                                   seed=args.seed, stage="smoke")
                if result != previous:
                    raise ValueError("supplied smoke result does not reproduce")
                write_once(out / "smoke_result.json", result)
                continue
            for name, digest in design["sources"].items():
                if sha256(ROOT / name) != digest:
                    raise ValueError(f"source changed during study: {name}")
            train_root = out / stage
            command = [str(PYTHON), str(ROOT / "tools/train_relative_progress_probe.py"), TASK,
                       "--env.scene.num-envs", str(num_envs), "--agent.max-iterations", str(iterations),
                       "--agent.logger", "tensorboard", "--agent.run-name", f"relative_{stage}_s{args.seed}",
                       "--log-root", str(train_root)]
            write_once(out / f"{stage}_command.json", {"argv": command, "seed": args.seed})
            log = out / f"{stage}.log"
            subprocess.run([str(ROOT / "tools/run_when_free.sh"), "14000", str(log), "--", *command],
                           cwd=ROOT, env=env, check=True)
            if "DONE rc=0 " not in log.read_text():
                raise ValueError("missing successful training sentinel")
            candidates = list(train_root.glob("g1_tracking/*"))
            if len(candidates) != 1:
                raise ValueError("ambiguous training run directory")
            result = check_run(candidates[0], Path(env["CLIMB_SEGMENT_MANIFEST"]),
                               seed=args.seed, stage=stage)
            write_once(out / f"{stage}_result.json", result)
            print(json.dumps({"stage": stage, "status": result["status"]}), flush=True)
            if result["status"] not in ("smoke_pass", "manipulation_pass"):
                raise ValueError(f"{stage}: {result['status']}; candidate stopped")
        status = {"status": "completed", "seed": args.seed, "policy_endpoints_opened": False,
                  "next": "independent manipulation replication; policy benefit remains pending"}
    except (ValueError, KeyError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        status = {"status": "stopped", "seed": args.seed, "reason": str(exc),
                  "policy_endpoints_opened": False}
    write_once(out / "terminal_status.json", status)
    print(json.dumps(status), flush=True)
    if status["status"] != "completed":
        sys.exit(1)


if __name__ == "__main__":
    main()
