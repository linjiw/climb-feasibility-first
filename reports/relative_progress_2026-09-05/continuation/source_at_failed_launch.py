#!/usr/bin/env python3
"""Reproduce R1's complete decision before launching the independent R2 study."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from check_relative_progress_probe import check_run, sha256
from run_relative_progress_study import write_once

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "reports/g_segment/unit_table.json"
PYTHON = ROOT / "mjlab-1.6.0/.venv/bin/python"


def verify_study(study: Path, seed: int) -> dict:
    """Reproduce complete evidence, including scientific failures, before promotion."""
    design = json.loads((study / "design.json").read_text())
    terminal = json.loads((study / "terminal_status.json").read_text())
    if design["seed"] != seed or terminal["seed"] != seed:
        raise ValueError("study seed mismatch")
    if design["policy_endpoints_opened"] or terminal["policy_endpoints_opened"]:
        raise ValueError("unexpected endpoint access")
    for name, digest in design["sources"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"study source changed: {name}")
    summaries = {}
    for stage in ("smoke", "long"):
        path = study / f"{stage}_result.json"
        saved = json.loads(path.read_text())
        if saved["seed"] != seed or saved["stage"] != stage:
            raise ValueError("result stage/seed mismatch")
        parents = {Path(name).resolve().parent for name in saved["bindings"]}
        if len(parents) != 1:
            raise ValueError("ambiguous ledger run directory")
        reproduced = check_run(parents.pop(), MANIFEST, seed=seed, stage=stage)
        if reproduced != saved:
            raise ValueError(f"{stage} result does not reproduce")
        summaries[stage] = {"path": str(path), "sha256": sha256(path),
                            "status": saved["status"], "gate": saved["gate"]}
    if "DONE rc=0 " not in (study / "long.log").read_text():
        raise ValueError("long training lacks successful completion sentinel")
    passed = (summaries["smoke"]["status"] == "smoke_pass"
              and summaries["long"]["status"] == "manipulation_pass")
    if passed != (terminal["status"] == "completed"):
        raise ValueError("terminal decision disagrees with reproduced result")
    return {"seed": seed, "status": "pass" if passed else "fail",
            "results": summaries, "design_sha256": sha256(study / "design.json"),
            "terminal_sha256": sha256(study / "terminal_status.json")}


def wait_for_terminal(study: Path, deadline: float, expected_pid: int | None) -> None:
    while not (study / "terminal_status.json").is_file():
        if time.monotonic() >= deadline:
            raise TimeoutError("predecessor has no terminal result before deadline")
        if expected_pid is not None:
            try:
                os.kill(expected_pid, 0)
            except ProcessLookupError as exc:
                raise RuntimeError("predecessor supervisor disappeared without terminal result") from exc
        time.sleep(15)
    # The original runner writes a small terminal JSON non-atomically.
    for attempt in range(5):
        try:
            json.loads((study / "terminal_status.json").read_text())
            return
        except json.JSONDecodeError:
            if attempt == 4:
                raise
            time.sleep(1)


def wait_for_gpu(deadline: float) -> None:
    while time.monotonic() < deadline:
        text = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.free,utilization.gpu",
             "--format=csv,noheader,nounits"], text=True,
        )
        free, utilization = (int(value.strip()) for value in text.splitlines()[0].split(","))
        if free >= 14000 and utilization <= 60:
            return
        time.sleep(30)
    raise TimeoutError("shared GPU did not become available before deadline")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predecessor", type=Path, required=True)
    parser.add_argument("--predecessor-pid", type=int)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--wait-seconds", type=int, default=7200)
    args = parser.parse_args()
    if args.wait_seconds <= 0:
        parser.error("--wait-seconds must be positive")
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    predecessor = args.predecessor.resolve()
    deadline = time.monotonic() + args.wait_seconds
    source_names = ("tools/continue_relative_progress.py", "tools/run_relative_progress_study.py",
                    "tools/check_relative_progress_probe.py", "tools/train_relative_progress_probe.py",
                    "tools/plot_relative_progress.py", "climb/relative_progress.py")
    sources = {name: sha256(ROOT / name) for name in source_names}
    predecessor_design_hash = sha256(predecessor / "design.json")
    write_once(out / "design.json", {
        "schema_version": "relative_progress_continuation/1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "predecessor": str(predecessor), "predecessor_seed": 11, "next_seed": 12,
        "sources": sources, "predecessor_design_sha256": predecessor_design_hash,
        "wait_seconds": args.wait_seconds, "policy_endpoints_opened": False,
        "rule": "Complete reproduced seed-11 pass is required; then unchanged seed-12 smoke and long study.",
    })
    try:
        print("Waiting for complete seed-11 decision", flush=True)
        wait_for_terminal(predecessor, deadline, args.predecessor_pid)
        if sha256(predecessor / "design.json") != predecessor_design_hash:
            raise ValueError("predecessor design changed while waiting")
        for name, digest in sources.items():
            if sha256(ROOT / name) != digest:
                raise ValueError(f"continuation source changed while waiting: {name}")
        first = verify_study(predecessor, 11)
        write_once(out / "seed11_verification.json", first)
        subprocess.run([str(PYTHON), str(ROOT / "tools/plot_relative_progress.py"),
                        "--results", str(predecessor / "long_result.json"),
                        "--out-dir", str(out / "seed11_figure")], check=True, cwd=ROOT)
        if first["status"] != "pass":
            final = {"status": "candidate_stopped", "reason": "seed11_manipulation_fail"}
        else:
            print("Seed 11 reproduced and passed; waiting for shared GPU", flush=True)
            wait_for_gpu(deadline)
            next_study = out / "study_s12"
            command = [str(PYTHON), str(ROOT / "tools/run_relative_progress_study.py"),
                       "--seed", "12", "--out-dir", str(next_study)]
            write_once(out / "seed12_launch.json", {"argv": command})
            with (out / "seed12_launcher.log").open("x") as log:
                completed = subprocess.run(command, cwd=ROOT, stdout=log,
                                           stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            second = verify_study(next_study, 12)
            write_once(out / "seed12_verification.json", second)
            if (completed.returncode == 0) != (second["status"] == "pass"):
                raise ValueError("seed-12 exit code disagrees with verified decision")
            subprocess.run([str(PYTHON), str(ROOT / "tools/plot_relative_progress.py"),
                            "--results", str(predecessor / "long_result.json"),
                            str(next_study / "long_result.json"),
                            "--out-dir", str(out / "replication_figure")], check=True, cwd=ROOT)
            final = {"status": "replicated_manipulation" if second["status"] == "pass"
                     else "candidate_stopped", "seed11": first["status"], "seed12": second["status"]}
    except Exception as exc:
        # Artifact decoding failures must also leave a durable failed decision.
        final = {"status": "execution_stopped", "reason": str(exc)}
    final.update({"policy_endpoints_opened": False, "policy_benefit": "pending",
                  "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat()})
    write_once(out / "terminal_status.json", final)
    print(json.dumps(final), flush=True)
    if final["status"] != "replicated_manipulation":
        sys.exit(1)


if __name__ == "__main__":
    main()
