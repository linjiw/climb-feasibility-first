#!/usr/bin/env python3
"""Audit whether the next CLIMB segment-native experiment can launch safely.

The command is deliberately fail-closed around the licensed motion payload,
the hash-bound Phase-G inputs, the pinned MJLab/Newton environments, and the
unsealed experiment gate.  It does not download data, invent checkpoints, or
seal a preregistration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
try:
    from tools.restore_phase_g_bank import load_requirements
except ModuleNotFoundError:  # Direct execution places tools/ on sys.path.
    from restore_phase_g_bank import load_requirements

EXPECTED_G1_SHA256 = (
    "febdcbeffbbf84051556ae41a5ac1b43fb479a5d76bdb3f54824dbc2721c20aa"
)
EXPECTED_NEWTON_VERSIONS = {
    "newton": "1.5.0",
    "warp": "1.16.0",
    "mujoco": "3.11.0",
    "mujoco_warp": "3.11.0",
}
EXPECTED_TRAIN_TASKS = {
    "Climb-Tracking-Flat-Unitree-G1",
    "Climb-Tracking-Flat-Unitree-G1-Adaptive",
    "Climb-Tracking-Flat-Unitree-G1-Grounded",
}

Status = Literal["ok", "warning", "blocker"]


@dataclass(frozen=True)
class Check:
    """One readiness assertion with a user-actionable result."""

    name: str
    status: Status
    detail: str


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    """Match the canonical JSON identity used by the segment runtime."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def path_from_env(name: str, fallback: str) -> Path:
    """Resolve a configurable research path relative to the repository."""
    raw = os.environ.get(name, fallback)
    path = Path(raw).expanduser()
    return path if path.is_absolute() else ROOT / path


def run_json(python: Path, code: str) -> tuple[dict[str, Any] | None, str]:
    """Run an isolated environment probe and decode its last output line."""
    try:
        result = subprocess.run(
            [str(python), "-c", code],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    if result.returncode != 0:
        return None, (result.stderr or result.stdout).strip()
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return None, "probe produced no output"
    try:
        return json.loads(lines[-1]), ""
    except json.JSONDecodeError:
        return None, result.stdout.strip()


def load_unit_table(path: Path) -> tuple[dict[str, Any] | None, Check]:
    """Validate the compact Phase-G unit-table contract."""
    if not path.is_file():
        return None, Check("Phase-G unit table", "blocker", f"missing {path}")
    try:
        table = json.loads(path.read_text())
        frozen = {
            "horizon_steps": table["horizon_steps"],
            "sources": table["sources"],
            "source_units": table["source_units"],
            "admissible_units": table["admissible_units"],
        }
        if table.get("schema_version") != "segment_unit_table/1":
            raise ValueError("unsupported schema")
        if canonical_hash(frozen) != table.get("unit_table_sha256"):
            raise ValueError("embedded canonical hash mismatch")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return None, Check("Phase-G unit table", "blocker", f"invalid: {exc}")
    detail = (
        f"{len(table['sources'])} clips, {len(table['admissible_units'])} "
        f"admissible units, {sum(u['legal_start_count'] for u in table['admissible_units']):,} "
        "legal starts; canonical hash passes"
    )
    return table, Check("Phase-G unit table", "ok", detail)


def materialize_clip_list(table: dict[str, Any], path: Path) -> Check:
    """Reconstruct the sealed tier list already encoded by the unit table."""
    payload = "".join(f"{row['clip']}\n" for row in table["sources"])
    expected = table.get("clips_sha256")
    actual = hashlib.sha256(payload.encode()).hexdigest()
    if actual != expected:
        return Check(
            "Phase-G clip list",
            "blocker",
            "unit-table source order does not reproduce its bound clip-list hash",
        )
    if path.exists():
        if not path.is_file() or sha256_file(path) != expected:
            return Check(
                "Phase-G clip list",
                "blocker",
                f"existing {path} differs from sealed hash {expected}",
            )
        return Check("Phase-G clip list", "ok", f"{path} matches {expected}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload)
    return Check(
        "Phase-G clip list",
        "ok",
        f"materialized {len(table['sources'])} names at {path}; hash {expected}",
    )


def check_clip_list(table: dict[str, Any], path: Path) -> Check:
    """Require the training list to match the unit-table source order exactly."""
    if not path.is_file():
        return Check(
            "Phase-G clip list",
            "blocker",
            f"missing {path}; rerun with --materialize-clips",
        )
    expected = table.get("clips_sha256")
    actual = sha256_file(path)
    if actual != expected:
        return Check(
            "Phase-G clip list",
            "blocker",
            f"hash {actual} differs from bound hash {expected}",
        )
    return Check("Phase-G clip list", "ok", f"800-name list matches {expected}")


def check_motion_bank(
    requirements: dict[str, str],
    counts: dict[str, int],
    bank: Path,
    *,
    scope: str,
    verify_hashes: bool,
) -> Check:
    """Check every hash-bound G1 payload required by the current stage."""
    if not bank.is_dir():
        return Check(
            "AMASS→G1 motion bank",
            "blocker",
            f"missing licensed/local payload directory {bank}; {scope} scope "
            f"requires {counts['unique']} exact motions",
        )
    missing = [
        name for name in requirements if not (bank / f"{name}.npz").is_file()
    ]
    if missing:
        return Check(
            "AMASS→G1 motion bank",
            "blocker",
            f"missing {len(missing)}/{len(requirements)} {scope}-scope motions; "
            f"first: {missing[:3]}",
        )
    if verify_hashes:
        mismatched = []
        for name, expected in requirements.items():
            motion = bank / f"{name}.npz"
            if sha256_file(motion) != expected:
                mismatched.append(name)
        if mismatched:
            return Check(
                "AMASS→G1 motion bank",
                "blocker",
                f"{len(mismatched)} motion hashes differ; first: {mismatched[:3]}",
            )
        suffix = f"; all {len(requirements)} SHA-256 identities pass"
    else:
        suffix = "; existence checked (use --verify-motion-hashes for identities)"
    return Check(
        "AMASS→G1 motion bank",
        "ok",
        f"{scope} scope: {counts['training']} training + "
        f"{counts['evaluation']} evaluation = {counts['unique']} unique motions present"
        f"{suffix}",
    )


def check_eval_inputs(
    panel: Path,
    panel_manifest_path: Path,
    conditions_path: Path,
    strata_path: Path,
) -> list[Check]:
    """Validate the disjoint evaluation panel's compact committed inputs."""
    checks = []
    if not panel.is_file():
        checks.append(Check("evaluation panel", "blocker", f"missing {panel}"))
        panel_names: set[str] = set()
    else:
        names = [line.strip() for line in panel.read_text().splitlines() if line.strip()]
        panel_names = set(names)
        status: Status = "ok" if len(names) == len(panel_names) == 100 else "blocker"
        checks.append(
            Check(
                "evaluation panel",
                status,
                f"{len(names)} rows, {len(panel_names)} unique clips",
            )
        )
    if not panel_manifest_path.is_file():
        checks.append(
            Check(
                "evaluation reference identities",
                "blocker",
                f"missing {panel_manifest_path}",
            )
        )
    else:
        try:
            manifest = json.loads(panel_manifest_path.read_text())
            identities = manifest["motion_sha256"]
            valid_manifest = (
                manifest.get("schema_version") == "g_segment_eval_panel/1"
                and manifest.get("size") == len(identities) == 100
                and set(identities) == panel_names
                and manifest.get("panel_txt_sha256") == sha256_file(panel)
            )
            identity_detail = (
                f"{len(identities)} hash-bound motions; "
                f"panel match={set(identities) == panel_names}"
            )
        except (KeyError, OSError, TypeError, json.JSONDecodeError) as exc:
            valid_manifest = False
            identity_detail = f"invalid: {exc}"
        checks.append(
            Check(
                "evaluation reference identities",
                "ok" if valid_manifest else "blocker",
                identity_detail,
            )
        )
    if not conditions_path.is_file():
        checks.append(
            Check("evaluation conditions", "blocker", f"missing {conditions_path}")
        )
        return checks
    try:
        conditions = json.loads(conditions_path.read_text())
        rows = conditions["conditions"]
        condition_clips = {row["clip"] for row in rows}
        full_window = all(bool(row["full_window"]) for row in rows)
        valid = (
            conditions.get("schema_version") == "paired_eval_conditions/2"
            and len(rows) == 2_800
            and condition_clips == panel_names
            and full_window
        )
        detail = (
            f"{len(rows)} conditions over {len(condition_clips)} clips; "
            f"panel match={condition_clips == panel_names}, full-window={full_window}"
        )
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        valid = False
        detail = f"invalid: {exc}"
    checks.append(Check("evaluation conditions", "ok" if valid else "blocker", detail))
    if not strata_path.is_file():
        checks.append(Check("evaluation strata", "blocker", f"missing {strata_path}"))
        return checks
    try:
        import csv

        with strata_path.open() as handle:
            strata = list(csv.DictReader(handle))
        strata_names = {row["clip"] for row in strata}
        counts = {
            label: sum(row["stratum"] == label for row in strata)
            for label in ("feasible_hard_reference", "feasible_remainder")
        }
        manifest_path = strata_path.with_suffix(".manifest.json")
        manifest = json.loads(manifest_path.read_text())
        strata_valid = (
            len(strata) == len(strata_names) == 100
            and strata_names == panel_names
            and counts == {
                "feasible_hard_reference": 25,
                "feasible_remainder": 75,
            }
            and manifest.get("output_sha256") == sha256_file(strata_path)
            and manifest.get("inputs", {}).get("panel_sha256")
            == sha256_file(panel)
        )
        strata_detail = f"counts={counts}, panel match={strata_names == panel_names}"
    except (KeyError, OSError, TypeError, json.JSONDecodeError) as exc:
        strata_valid = False
        strata_detail = f"invalid: {exc}"
    checks.append(
        Check("evaluation strata", "ok" if strata_valid else "blocker", strata_detail)
    )
    return checks


def check_internal_dataset(path: Path) -> Check:
    """Validate the ignored Parquet candidate against its tracked manifest."""
    manifest_path = path.with_suffix(".manifest.json")
    if not manifest_path.is_file():
        return Check("feasibility dataset", "warning", f"missing {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text())
        expected = manifest["artifact"]["sha256"]
    except (KeyError, json.JSONDecodeError) as exc:
        return Check("feasibility dataset", "warning", f"invalid manifest: {exc}")
    if not path.is_file():
        return Check(
            "feasibility dataset",
            "warning",
            "internal Parquet absent; rebuild with tools/build_feasibility_release.py",
        )
    actual = sha256_file(path)
    if actual != expected:
        return Check(
            "feasibility dataset",
            "warning",
            f"Parquet hash {actual} differs from manifest {expected}",
        )
    return Check(
        "feasibility dataset",
        "ok",
        f"10,705-row internal candidate hash {actual}; public distribution blocked",
    )


def check_phase_g_instruments() -> Check:
    """Require a current six-branch analyzer self-test and provenance builder."""
    analyzer = ROOT / "tools/analyze_g_segment.py"
    builder = ROOT / "tools/build_g_run_manifest.py"
    evaluator = ROOT / "tools/eval_paired_v2.py"
    training = ROOT / "tools/climb_segment_train.py"
    report_path = ROOT / "reports/g_segment/SYNTHETIC.json"
    required = (analyzer, builder, evaluator, training, report_path)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        return Check("Phase-G instruments", "blocker", f"missing {missing}")
    try:
        report = json.loads(report_path.read_text())
        expected = {
            "positive": "positive",
            "null": "null",
            "inconclusive": "inconclusive",
            "gate_fail": "not_tested",
            "seed_mismatch": "not_tested",
            "provenance_mismatch": "not_tested",
        }
        passed = (
            report.get("pass") is True
            and report.get("verdicts") == expected
            and report.get("expected") == expected
            and report.get("analyzer_sha256") == sha256_file(analyzer)
        )
    except (OSError, json.JSONDecodeError):
        passed = False
    detail = (
        "six decision/provenance branches match current analyzer; hash-complete "
        "manifest builder present"
        if passed
        else "synthetic report is absent, stale, or does not cover all six branches"
    )
    return Check("Phase-G instruments", "ok" if passed else "blocker", detail)


def check_contact_timing_instrument() -> list[Check]:
    """Audit proxy machinery separately from its still-pending real validation."""
    panel = ROOT / "reports/g_segment/contact_validation/panel.csv"
    panel_manifest_path = panel.with_suffix(".manifest.json")
    synthetic_path = ROOT / "reports/g_segment/contact_validation/SYNTHETIC.json"
    selector = ROOT / "tools/build_contact_validation_panel.py"
    builder = ROOT / "tools/build_reference_contact_labels.py"
    renderer = ROOT / "tools/render_contact_validation.py"
    scorer = ROOT / "tools/validate_contact_proxy.py"
    evaluator = ROOT / "tools/eval_paired_v2.py"
    required = (
        panel,
        panel_manifest_path,
        synthetic_path,
        selector,
        builder,
        renderer,
        scorer,
        evaluator,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        return [Check("contact-timing instrument", "blocker", f"missing {missing}")]
    try:
        panel_manifest = json.loads(panel_manifest_path.read_text())
        synthetic = json.loads(synthetic_path.read_text())
        infrastructure_ok = (
            panel_manifest.get("schema_version") == "contact_validation_panel/1"
            and panel_manifest.get("counts")
            == {
                "development": 10,
                "feasible_hard_reference": 10,
                "feasible_remainder": 10,
                "validation": 10,
            }
            and panel_manifest.get("output", {}).get("sha256") == sha256_file(panel)
            and panel_manifest.get("builder_sha256") == sha256_file(selector)
            and synthetic.get("branches")
            == {
                "passing": "validated",
                "failed": "failed_validation",
                "insufficient": "insufficient_support",
            }
            and synthetic.get("scorer_sha256") == sha256_file(scorer)
        )
    except (OSError, json.JSONDecodeError):
        infrastructure_ok = False
    checks = [
        Check(
            "contact-timing instrument",
            "ok" if infrastructure_ok else "blocker",
            (
                "20-clip outcome-blind panel and three-branch validation scorer pass"
                if infrastructure_ok
                else "panel or synthetic validation report is stale/malformed"
            ),
        )
    ]

    result_path = ROOT / "reports/g_segment/contact_validation/result.json"
    if not result_path.is_file():
        checks.append(
            Check(
                "contact-timing validation",
                "warning",
                "real blinded labels absent; metric remains exploratory and cannot "
                "affect the Phase-G verdict",
            )
        )
        return checks
    try:
        result = json.loads(result_path.read_text())
        valid = (
            result.get("schema_version") == "contact_proxy_validation/1"
            and result.get("status") == "validated"
            and result.get("scorer_sha256") == sha256_file(scorer)
        )
        detail = f"held-out instrument status={result.get('status')!r}"
    except (OSError, json.JSONDecodeError) as exc:
        valid = False
        detail = f"invalid validation report: {exc}"
    checks.append(
        Check("contact-timing validation", "ok" if valid else "warning", detail)
    )
    return checks


def check_simulator(python: Path) -> Check:
    """Import the pinned MJLab stack and run a small CUDA/MJWarp step test."""
    if not python.is_file():
        return Check("MJLab simulator", "blocker", f"missing {python}")
    code = """
import json
import os
os.environ.pop('CLIMB_CLIPS', None)
os.environ.pop('CLIMB_BANK', None)
import climb
import mujoco, mujoco_warp, torch, warp
from mjlab.envs import ManagerBasedRlEnv
from mjlab.tasks.registry import list_tasks, load_env_cfg

cfg = load_env_cfg('Mjlab-Cartpole-Balance', play=True)
cfg.scene.num_envs = 4
cfg.seed = 20260903
env = ManagerBasedRlEnv(cfg=cfg, device='cuda:0')
try:
  env.reset(seed=20260903)
  action = torch.zeros(
    (env.num_envs, env.action_manager.total_action_dim), device=env.device
  )
  reward_finite = True
  for _ in range(5):
    _, reward, _, _, _ = env.step(action)
    reward_finite = reward_finite and bool(torch.isfinite(reward).all())
finally:
  env.close()
print(json.dumps({
  'tasks': list_tasks(), 'mujoco': mujoco.__version__,
  'mujoco_warp': mujoco_warp.__version__, 'warp': warp.__version__,
  'torch': torch.__version__, 'cuda': torch.cuda.is_available(),
  'step_smoke': reward_finite,
}))
"""
    payload, error = run_json(python, code)
    if payload is None:
        status: Status = "warning" if "timed out" in error else "blocker"
        return Check("MJLab simulator", status, error)
    missing = EXPECTED_TRAIN_TASKS - set(payload["tasks"])
    versions_pass = (
        payload["mujoco"] == "3.11.0" and payload["mujoco_warp"] == "3.11.0"
    )
    passed = (
        not missing
        and versions_pass
        and payload["cuda"]
        and payload["step_smoke"]
    )
    detail = (
        f"MuJoCo/MJWarp {payload['mujoco']}/{payload['mujoco_warp']}, "
        f"Warp {payload['warp']}, Torch {payload['torch']}, CUDA={payload['cuda']}, "
        f"4-env/5-step smoke={payload['step_smoke']}, missing tasks={sorted(missing)}"
    )
    return Check("MJLab simulator", "ok" if passed else "blocker", detail)


def check_newton(python: Path) -> Check:
    """Import Newton's isolated pinned stack and verify CUDA allocation."""
    if not python.is_file():
        return Check("Newton 1.5 stack", "blocker", f"missing {python}")
    code = """
import json
import mujoco, mujoco_warp, newton, torch, warp
warp.init()
allocation = warp.zeros(1, dtype=warp.float32, device='cuda:0')
print(json.dumps({
  'newton': newton.__version__, 'warp': warp.__version__,
  'mujoco': mujoco.__version__, 'mujoco_warp': mujoco_warp.__version__,
  'torch': torch.__version__, 'cuda': torch.cuda.is_available(),
  'allocation_device': str(allocation.device),
}))
"""
    payload, error = run_json(python, code)
    if payload is None:
        status: Status = "warning" if "timed out" in error else "blocker"
        return Check("Newton 1.5 stack", status, error)
    core = {key: payload[key] for key in EXPECTED_NEWTON_VERSIONS}
    passed = (
        core == EXPECTED_NEWTON_VERSIONS
        and payload["cuda"]
        and payload["allocation_device"] == "cuda:0"
    )
    detail = ", ".join(f"{key}={value}" for key, value in core.items())
    detail += f", Torch={payload['torch']}, CUDA allocation={payload['allocation_device']}"
    return Check("Newton 1.5 stack", "ok" if passed else "blocker", detail)


def check_gpu() -> Check:
    """Report current shared-GPU capacity without treating it as ownership."""
    command = [
        "nvidia-smi",
        "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        name, total, used, free, utilization = [
            item.strip() for item in result.stdout.splitlines()[0].split(",")
        ]
        detail = (
            f"{name}: {free}/{total} MiB free, {used} MiB used, "
            f"{utilization}% utilization; launch remains gap-gated"
        )
        status: Status = (
            "ok" if int(utilization) <= 60 and int(free) >= 8_192 else "warning"
        )
        return Check("shared GPU", status, detail)
    except (OSError, subprocess.SubprocessError, ValueError, IndexError) as exc:
        return Check("shared GPU", "warning", f"could not query: {exc}")


def check_g1_model(path: Path) -> Check:
    """Verify the exact Unitree G1 MJCF used by the experiment."""
    if not path.is_file():
        return Check("Unitree G1 model", "blocker", f"missing {path}")
    actual = sha256_file(path)
    if actual != EXPECTED_G1_SHA256:
        return Check(
            "Unitree G1 model",
            "blocker",
            f"hash {actual} differs from pinned {EXPECTED_G1_SHA256}",
        )
    return Check("Unitree G1 model", "ok", f"MJCF hash {actual}")


def check_research_state(stage: str) -> list[Check]:
    """Enforce the measured Newton decision and the still-unsealed Phase-G gate."""
    checks = []
    recert_path = ROOT / "reports/newton15_recert/result.json"
    pred_path = ROOT / "reports/newton15_pred/result.json"
    try:
        recert = json.loads(recert_path.read_text())
        recert_ok = recert.get("pass") is True
        recert_detail = "measured two-unit conformance PASS" if recert_ok else "PASS not recorded"
    except (OSError, json.JSONDecodeError):
        recert_ok = False
        recert_detail = f"missing or invalid {recert_path}"
    checks.append(
        Check("Newton conformance record", "ok" if recert_ok else "blocker", recert_detail)
    )
    try:
        prediction = json.loads(pred_path.read_text())
        decision = prediction["decision"]
        scope_ok = decision.get("measurement_valid") is True and decision.get("gate_pass") is False
        scope_detail = decision.get("next_action", "missing next action")
    except (OSError, KeyError, json.JSONDecodeError):
        scope_ok = False
        scope_detail = f"missing or invalid {pred_path}"
    checks.append(
        Check("Newton scope guard", "ok" if scope_ok else "blocker", scope_detail)
    )
    seal = ROOT / "plan/G_SEGMENT_FREEZE.sha256"
    if seal.is_file():
        checks.append(Check("Phase-G seal", "ok", f"present at {seal}"))
    else:
        status: Status = "warning" if stage == "calibration" else "blocker"
        checks.append(
            Check(
                "Phase-G seal",
                status,
                "not sealed; calibration may run, but confirmation requires "
                "S8/S10/S11 and the seal",
            )
        )
    return checks


def check_checkpoint(path: Path | None) -> Check:
    """Distinguish an optional analysis checkpoint from the from-scratch G1/G2 arms."""
    if path is None:
        return Check(
            "policy checkpoint",
            "warning",
            "not configured; Phase-G G1/G2 train from scratch, but old "
            "conformance/probe reruns need their archived checkpoints",
        )
    if not path.is_file():
        return Check("policy checkpoint", "blocker", f"missing {path}")
    return Check("policy checkpoint", "ok", f"{path}; SHA-256 {sha256_file(path)}")


def check_g2_launch_environment(stage: str) -> Check:
    """Require explicit calibration or frozen-confirmation sampler settings."""
    expected = {
        "CLIMB_SEGMENT_RANK": "learning_progress",
        "CLIMB_SEGMENT_DIFFICULTY_POWER": "0",
        "CLIMB_SEGMENT_PROGRESS_WINDOW": "10",
        "CLIMB_SEGMENT_MAX_UNIT_PROBABILITY": "0.05",
        "CLIMB_SEGMENT_MAX_CLIP_PROBABILITY": "0.25",
        "CLIMB_SEGMENT_FAILURE_PENALTY": "-10",
        "CLIMB_VERIFY_MOTION_HASHES": "1",
    }
    if stage == "calibration":
        design = json.loads((ROOT / "plan/G2_CALIBRATION_GRID.json").read_text())
        allowed_pairs = {
            (
                float(row["exploration_ratio"]),
                float(row["progress_floor"]),
            )
            for row in design["candidates"]
        }
        expected["CLIMB_SEGMENT_SAVE_INTERVAL"] = "10"
        allowed_seeds = {str(design["screen_seed"]), str(design["validation_seed"])}
    else:
        allowed_pairs = set()
        allowed_seeds = {"1", "2", "3"}
        expected["CLIMB_SEGMENT_SAVE_INTERVAL"] = "500"
    missing = [name for name in expected if name not in os.environ]
    mismatched = {
        name: os.environ[name]
        for name, value in expected.items()
        if name in os.environ and os.environ[name] != value
    }
    seed = os.environ.get("CLIMB_SEGMENT_SEED")
    try:
        pair = (
            float(os.environ["CLIMB_SEGMENT_EXPLORATION_RATIO"]),
            float(os.environ["CLIMB_SEGMENT_PROGRESS_FLOOR"]),
        )
    except (KeyError, ValueError):
        pair = None
    candidate_mismatch = stage == "calibration" and pair not in allowed_pairs
    if stage == "confirmation":
        calibration_path = ROOT / "reports/g_segment/calibration/result.json"
        try:
            calibration = json.loads(calibration_path.read_text())
            selected = calibration["selected"]
            candidate_mismatch = (
                calibration.get("status") != "ready_to_freeze"
                or pair
                != (
                    float(selected["exploration_ratio"]),
                    float(selected["progress_floor"]),
                )
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            candidate_mismatch = True
    if missing or mismatched or seed not in allowed_seeds or candidate_mismatch:
        return Check(
            "G2 launch contract",
            "blocker",
            f"stage={stage}; missing={missing}, mismatched={mismatched}, "
            f"seed={seed!r}, candidate_pair={pair!r}",
        )
    return Check(
        "G2 launch contract",
        "ok",
        f"{stage} seed/settings satisfy the endpoint-blind ALP contract",
    )


def parse_args() -> argparse.Namespace:
    """Parse the readiness audit CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bank",
        type=Path,
        default=path_from_env("CLIMB_BANK", "bank/amass"),
    )
    parser.add_argument(
        "--clips",
        type=Path,
        default=path_from_env("CLIMB_CLIPS", "bank/tiers/tier_800.txt"),
    )
    parser.add_argument(
        "--unit-table",
        type=Path,
        default=ROOT / "reports/g_segment/unit_table.json",
    )
    parser.add_argument(
        "--eval-panel",
        type=Path,
        default=ROOT / "reports/g_segment/panel/panel.txt",
    )
    parser.add_argument(
        "--eval-panel-manifest",
        type=Path,
        default=ROOT / "reports/g_segment/panel/panel_manifest.json",
    )
    parser.add_argument(
        "--eval-conditions",
        type=Path,
        default=ROOT / "reports/g_segment/eval_conditions.json",
    )
    parser.add_argument(
        "--eval-strata",
        type=Path,
        default=ROOT / "reports/g_segment/panel/strata.csv",
    )
    checkpoint = os.environ.get("CLIMB_CHECKPOINT")
    parser.add_argument("--checkpoint", type=Path, default=Path(checkpoint) if checkpoint else None)
    parser.add_argument("--verify-motion-hashes", action="store_true")
    parser.add_argument(
        "--materialize-clips",
        action="store_true",
        help="write the sealed tier_800 list reconstructed from the committed unit table",
    )
    parser.add_argument(
        "--g2-stage",
        choices=("calibration", "confirmation"),
        default="calibration",
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return nonzero while any launch blocker remains",
    )
    return parser.parse_args()


def main() -> int:
    """Run all readiness checks and print a compact status report."""
    args = parse_args()
    checks: list[Check] = []
    table, table_check = load_unit_table(args.unit_table)
    checks.append(table_check)
    if table is not None:
        if args.materialize_clips:
            checks.append(materialize_clip_list(table, args.clips))
        else:
            checks.append(check_clip_list(table, args.clips))
        payload_scope = "calibration" if args.g2_stage == "calibration" else "full"
        try:
            requirements, counts, _ = load_requirements(
                args.unit_table,
                args.eval_panel_manifest,
                scope=payload_scope,
            )
            checks.append(
                Check(
                    "Phase-G payload contract",
                    "ok",
                    f"{payload_scope} scope binds {counts['unique']} identities "
                    f"({counts['training']} training, {counts['evaluation']} evaluation)",
                )
            )
            checks.append(
                check_motion_bank(
                    requirements,
                    counts,
                    args.bank,
                    scope=payload_scope,
                    verify_hashes=args.verify_motion_hashes,
                )
            )
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            checks.append(
                Check("Phase-G payload contract", "blocker", f"invalid: {exc}")
            )
    checks.extend(
        check_eval_inputs(
            args.eval_panel,
            args.eval_panel_manifest,
            args.eval_conditions,
            args.eval_strata,
        )
    )
    checks.append(
        check_internal_dataset(ROOT / "datasets/amass_g1_feasibility_v1.parquet")
    )
    checks.append(check_phase_g_instruments())
    checks.extend(check_contact_timing_instrument())
    checks.append(
        check_g1_model(
            ROOT
            / "mjlab-1.6.0/src/mjlab/asset_zoo/robots/unitree_g1/xmls/g1.xml"
        )
    )
    checks.append(check_simulator(ROOT / "mjlab-1.6.0/.venv/bin/python"))
    checks.append(check_newton(ROOT / "newton15/.venv/bin/python"))
    checks.append(check_gpu())
    checks.extend(check_research_state(args.g2_stage))
    checks.append(check_g2_launch_environment(args.g2_stage))
    checks.append(check_checkpoint(args.checkpoint))

    counts = {
        status: sum(row.status == status for row in checks)
        for status in ("ok", "warning", "blocker")
    }
    for row in checks:
        print(f"[{row.status.upper():7}] {row.name}: {row.detail}")
    print(
        f"summary: {counts['ok']} ok, {counts['warning']} warning, "
        f"{counts['blocker']} blocker"
    )
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "schema_version": "climb_research_preflight/1",
            "root": str(ROOT),
            "checks": [asdict(row) for row in checks],
            "summary": counts,
            "launch_ready": counts["blocker"] == 0,
        }
        args.json_out.write_text(json.dumps(report, indent=1) + "\n")
    return 2 if args.strict and counts["blocker"] else 0


if __name__ == "__main__":
    sys.exit(main())
