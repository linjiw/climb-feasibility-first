#!/usr/bin/env python3
"""Run the frozen 50-iteration G2 screen or its one-seed validation.

This orchestrator launches training but never launches an evaluator. It writes
only the ledger map consumed by ``calibrate_g2_treatment.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TASK = "Climb-Tracking-Flat-Unitree-G1-SegmentV2-Adaptive"
REPRODUCIBILITY_ENV = (
    "CLIMB_BANK",
    "CLIMB_CLIPS",
    "CLIMB_SEGMENT_MANIFEST",
    "CLIMB_SEGMENT_SEED",
    "CLIMB_SEGMENT_RANK",
    "CLIMB_SEGMENT_DIFFICULTY_POWER",
    "CLIMB_SEGMENT_EXPLORATION_RATIO",
    "CLIMB_SEGMENT_PROGRESS_WINDOW",
    "CLIMB_SEGMENT_PROGRESS_FLOOR",
    "CLIMB_SEGMENT_MAX_UNIT_PROBABILITY",
    "CLIMB_SEGMENT_MAX_CLIP_PROBABILITY",
    "CLIMB_SEGMENT_SAVE_INTERVAL",
    "CLIMB_SEGMENT_FAILURE_PENALTY",
    "CLIMB_VERIFY_MOTION_HASHES",
    "WANDB_MODE",
)


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def candidate_command(
    design: dict[str, Any],
    candidate: dict[str, Any],
    *,
    seed: int,
    run_name: str,
    log_root: Path,
) -> tuple[dict[str, str], list[str]]:
    """Build one exact calibration environment and argv without a shell."""
    environment = os.environ.copy()
    environment.update({
        "CLIMB_SEGMENT_SEED": str(seed),
        "CLIMB_SEGMENT_RANK": str(design["rank"]),
        "CLIMB_SEGMENT_DIFFICULTY_POWER": str(design["difficulty_power"]),
        "CLIMB_SEGMENT_EXPLORATION_RATIO": str(candidate["exploration_ratio"]),
        "CLIMB_SEGMENT_PROGRESS_WINDOW": str(design["progress_window"]),
        "CLIMB_SEGMENT_PROGRESS_FLOOR": str(candidate["progress_floor"]),
        "CLIMB_SEGMENT_MAX_UNIT_PROBABILITY": str(design["max_unit_probability"]),
        "CLIMB_SEGMENT_MAX_CLIP_PROBABILITY": str(design["max_clip_probability"]),
        "CLIMB_SEGMENT_SAVE_INTERVAL": "10",
        "CLIMB_SEGMENT_FAILURE_PENALTY": str(design["failure_penalty"]),
        "CLIMB_VERIFY_MOTION_HASHES": "1",
        "WANDB_MODE": "offline",
    })
    command = [
        str(ROOT / "mjlab-1.6.0/.venv/bin/python"),
        str(ROOT / "tools/climb_segment_train.py"),
        TASK,
        "--env.scene.num-envs",
        str(design["num_envs"]),
        "--agent.max-iterations",
        str(design["iterations"]),
        "--agent.logger",
        "tensorboard",
        "--agent.run-name",
        run_name,
        "--log-root",
        str(log_root),
    ]
    return environment, command


def collect_ledgers(
    log_root: Path, run_name: str, required_iterations: list[int]
) -> list[str]:
    """Resolve the single just-completed run and its required sampler ledgers."""
    candidates = sorted((log_root / "g1_tracking").glob(f"*_{run_name}"))
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected one run directory for {run_name}, found {len(candidates)}"
        )
    run_dir = candidates[0]
    ledgers = [run_dir / f"model_{iteration}_segment.json" for iteration in required_iterations]
    missing = [str(path) for path in ledgers if not path.is_file()]
    if missing:
        raise RuntimeError(f"{run_name}: missing ledgers {missing}")
    return [str(path.resolve().relative_to(ROOT)) for path in ledgers]


def write_run_map(
    path: Path,
    *,
    design_hash: str,
    stage: str,
    runs: dict[str, dict[str, list[str]]],
) -> None:
    """Write the deliberately narrow, ledger-only selection input."""
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing run map {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema_version": "g2_calibration_runs/1",
        "design_sha256": design_hash,
        "stage": stage,
        "runs": runs,
    }, indent=1) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("screen", "validation"))
    parser.add_argument(
        "--design", type=Path, default=Path("plan/G2_CALIBRATION_GRID.json")
    )
    parser.add_argument("--need-mib", type=int, required=True)
    parser.add_argument(
        "--root", type=Path, default=Path("reports/g_segment/calibration")
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.need_mib <= 0:
        parser.error("--need-mib must be positive")
    missing_environment = [
        name
        for name in ("CLIMB_BANK", "CLIMB_CLIPS", "CLIMB_SEGMENT_MANIFEST")
        if name not in os.environ
    ]
    if missing_environment:
        parser.error(f"source research.env first; missing {missing_environment}")

    design_path = args.design.resolve()
    design = json.loads(design_path.read_text())
    if design.get("schema_version") != "g2_calibration_design/1":
        raise ValueError("unsupported calibration design")
    design_hash = sha256_file(design_path)
    calibration_root = args.root.resolve()
    log_root = calibration_root / f"{args.stage}_training"
    logs = calibration_root / "logs"
    required = [int(value) for value in design["required_ledger_iterations"]]

    if args.stage == "screen":
        candidates = design["candidates"]
        seed = int(design["screen_seed"])
    else:
        from calibrate_g2_treatment import analyze

        screen_runs = calibration_root / "screen_runs.json"
        screen_result = analyze(design_path, screen_runs, None)
        if screen_result["status"] != "selected_pending_independent_validation":
            raise RuntimeError(f"screen selection is not valid: {screen_result['status']}")
        candidates = [screen_result["selected"]]
        seed = int(design["validation_seed"])

    runs: dict[str, dict[str, list[str]]] = {}
    for candidate in candidates:
        candidate_id = candidate["id"]
        run_name = f"g2cal_{args.stage}_{candidate_id}"
        environment, command = candidate_command(
            design,
            candidate,
            seed=seed,
            run_name=run_name,
            log_root=log_root,
        )
        launch = [
            str(ROOT / "tools/run_when_free.sh"),
            str(args.need_mib),
            str(logs / f"{run_name}.log"),
            "--",
            *command,
        ]
        if args.dry_run:
            reproducible = [
                "env",
                *(f"{key}={environment[key]}" for key in REPRODUCIBILITY_ENV),
                *launch,
            ]
            print(" ".join(shlex.quote(value) for value in reproducible))
            continue
        logs.mkdir(parents=True, exist_ok=True)
        subprocess.run(launch, cwd=ROOT, env=environment, check=True)
        runs[candidate_id] = {
            "ledgers": collect_ledgers(log_root, run_name, required)
        }

    if args.dry_run:
        return 0
    run_map = calibration_root / f"{args.stage}_runs.json"
    write_run_map(
        run_map,
        design_hash=design_hash,
        stage=args.stage,
        runs=runs,
    )
    print(f"wrote {run_map}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
