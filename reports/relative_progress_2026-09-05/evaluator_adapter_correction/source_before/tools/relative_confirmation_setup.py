"""Fixed confirmation configuration and prelaunch evidence checks."""

from __future__ import annotations

import dataclasses
import enum
import functools
import hashlib
from importlib import metadata
import json
import math
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import torch

from check_relative_inputs import audit
from check_relative_progress_probe import sha256
from continue_relative_progress import verify_study
from eval_paired_v2 import software_versions
from relative_policy_provenance import ARMS, SEEDS, verified
from run_relative_failure_calibration import verify_calibration
from run_relative_policy_smokes import verify_smoke
import train_relative_policy as development

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "plan/R3_BASELINE_CONTRACT_2026-09-05.json"


def fixed_profiles(path: Path) -> dict:
    """Only confirmation enablement may differ from the fixed development profiles."""
    profiles = json.loads(path.read_text())
    expected = json.loads(PROFILE_PATH.read_text())
    if type(profiles["confirmation"]["enabled"]) is not bool:
        raise ValueError("confirmation enablement must be a boolean")
    comparable = json.loads(json.dumps(profiles))
    comparable["confirmation"]["enabled"] = False
    if comparable != expected:
        raise ValueError("confirmation changes the fixed profile contract")
    return profiles


def canonical(value: Any) -> Any:
    """Serialize configuration values without process-specific object addresses."""
    if isinstance(value, type):
        return {"type": f"{value.__module__}.{value.__qualname__}"}
    if dataclasses.is_dataclass(value):
        return {"type": f"{type(value).__module__}.{type(value).__qualname__}",
                "fields": {field.name: canonical(getattr(value, field.name)) for field in dataclasses.fields(value)}}
    if isinstance(value, enum.Enum):
        return {"enum": f"{type(value).__module__}.{type(value).__qualname__}", "value": canonical(value.value)}
    if isinstance(value, functools.partial):
        return {"partial": canonical(value.func), "args": canonical(value.args), "kwargs": canonical(value.keywords)}
    if callable(value):
        return {"callable": f"{value.__module__}.{value.__qualname__}"}
    if isinstance(value, dict):
        return {str(key): canonical(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        return [canonical(item) for item in value]
    if isinstance(value, slice):
        return {"slice": [canonical(value.start), canonical(value.stop), canonical(value.step)]}
    if isinstance(value, (set, frozenset)):
        return {"set": sorted((canonical(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))}
    if isinstance(value, np.ndarray):
        return {"array": value.tolist(), "dtype": str(value.dtype)}
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (Path, torch.dtype, torch.device)):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return {"float": str(value)}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"unsupported configuration value: {type(value)}")


def config_digest(env: Any, agent: Any) -> str:
    payload = json.dumps(canonical({"env": env, "agent": agent}), sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def build_configs(arm: str, seed: int, profiles: dict, inputs: dict) -> tuple[Any, Any]:
    """Build the same environment factory with fixed fresh seed and training budget."""
    if arm not in ARMS or seed not in SEEDS:
        raise ValueError("not a fixed confirmation arm/seed")
    selected, common = profiles["arms"][arm], profiles["common"]
    unit_table = Path(inputs["unit_table"]["path"])
    if json.loads(unit_table.read_text())["unit_table_sha256"] != profiles["unit_table_sha256"]:
        raise ValueError("wrong exact-support identity")
    cfg = development.segment_native_g1_tracking_env_cfg(
        motion_files=development.base.read_clip_list(inputs["training_clips"]["path"], inputs["bank"]),
        segment_manifest=str(unit_table), segment_sampling_mode=selected["mode"],
        sampler_seed=seed, env_seed=seed, segment_rank=selected["rank"],
        segment_exploration_ratio=selected["exploration_ratio"], segment_difficulty_power=selected["difficulty_power"],
        segment_progress_window=common["progress_window"], segment_progress_floor=selected["progress_floor"],
        max_unit_probability=common["max_unit_probability"], max_clip_probability=common["max_clip_probability"],
        verify_motion_hashes=common["verify_motion_hashes"], failure_penalty=common["failure_penalty"],
    )
    if arm == "R":
        command = cfg.commands["motion"]
        cfg.commands["motion"] = development.RelativeProgressCommandCfg(
            **{field.name: getattr(command, field.name) for field in dataclasses.fields(command)},
            relative_progress_factor=selected["relative_factor"])
    cfg.scene.num_envs = 512
    runner = development.base.unitree_g1_tracking_ppo_runner_cfg()
    runner.seed = seed
    runner.max_iterations = 4000
    runner.save_interval = 100
    runner.resume = False
    runner.logger = "tensorboard"
    runner.run_name = f"relative_confirmation_{arm}_s{seed}"
    return cfg, runner


def runtime_inventory() -> dict:
    """Bind repository/runtime Python sources, G1 assets and installed package versions."""
    import rsl_rl
    paths = set(ROOT.glob("climb/**/*.py")) | set(ROOT.glob("tools/*.py"))
    paths.update((ROOT / "mjlab-1.6.0/src/mjlab").rglob("*.py"))
    paths.update(Path(rsl_rl.__file__).parent.rglob("*.py"))
    asset_root = ROOT / "mjlab-1.6.0/src/mjlab/asset_zoo/robots/unitree_g1/xmls"
    assets = {path for path in asset_root.rglob("*") if path.is_file()}
    paths.update(assets)
    return {"schema_version": "relative_runtime_inventory/1",
            "files": {str(path.resolve()): sha256(path) for path in sorted(paths)},
            "g1_asset_count": len(assets),
            "packages": dict(sorted((item.metadata["Name"], item.version) for item in metadata.distributions())),
            "software_versions": software_versions(),
            "gpu_identity": subprocess.check_output(["nvidia-smi", "--query-gpu=name,uuid,driver_version",
                                                      "--format=csv,noheader"], text=True).strip(),
            "limitations": ["Compiled third-party libraries and driver binaries are version-recorded, not content-hashed.",
                            "Configuration callable identities rely on the separately bound source files."]}


def verify_prerequisites(contract: dict) -> None:
    """Replay complete calibration evidence without reading policy outcomes."""
    for seed in (11, 12):
        entry = contract["relative_replication"][str(seed)]
        path = verified(entry["decision"], "relative decision")
        if path != (Path(entry["study_dir"]) / "long_result.json").resolve():
            raise ValueError("relative decision cross-link mismatch")
        if verify_study(Path(entry["study_dir"]), seed)["status"] != "pass":
            raise ValueError("relative manipulation prerequisite failed")
    smoke = contract["four_arm_smokes"]
    design = json.loads(verified(smoke["design"], "smoke design").read_text())
    if set(smoke["decisions"]) != ARMS:
        raise ValueError("all four lifecycle smokes are required")
    for arm in sorted(ARMS):
        saved = json.loads(verified(smoke["decisions"][arm], "smoke decision").read_text())
        parents = {Path(name).parent for name in saved["bindings"]}
        if len(parents) != 1 or verify_smoke(parents.pop(), arm, design["sources"]) != saved:
            raise ValueError("lifecycle smoke does not reproduce")
    for seed in (31, 32):
        entry = contract["failure_calibration"][str(seed)]
        saved = json.loads(verified(entry["decision"], "D calibration").read_text())
        design = json.loads(verified(entry["execution_design"], "D design").read_text())
        parents = {Path(name).parent for name in saved["bindings"]}
        if (len(parents) != 1 or verify_calibration(parents.pop(), seed, design["sources"]) != saved
                or saved["status"] != "calibration_pass"):
            raise ValueError("D calibration prerequisite failed")


def verify_contract(path: Path, digest: str, *, smoke: bool = False) -> dict:
    """Require a prospective freeze and current evidence before configuring training."""
    contract = json.loads(verified({"path": str(path), "sha256": digest}, "confirmation contract").read_text())
    if (contract.get("schema_version") != "relative_confirmation_contract/1"
            or contract.get("status") != ("draft" if smoke else "frozen_before_confirmation")):
        raise ValueError("confirmation requires a prospective frozen contract")
    profiles = fixed_profiles(verified(contract["profiles"], "profiles"))
    if profiles["confirmation"]["enabled"] is not (False if smoke else True):
        raise ValueError("confirmation remains disabled")
    if verified(contract["training_entrypoint"], "training entrypoint") != ROOT / "tools/train_relative_confirmation.py":
        raise ValueError("contract binds another confirmation trainer")
    inventory = json.loads(verified(contract["runtime_inventory"], "runtime inventory").read_text())
    if inventory != runtime_inventory():
        raise ValueError("runtime sources, assets or package versions changed")
    for group in ("training_sources", "analysis_sources", "evaluator_sources"):
        for name, record in contract[group].items():
            verified(record, name)
    inputs = json.loads(verified(contract["reference_audit"], "reference audit").read_text())
    if audit(Path(contract["bank"])) != inputs:
        raise ValueError("reference-input audit no longer reproduces")
    mapping = {"unit_table": "unit_table", "training_clips": "training_clips", "panel": "panel_manifest",
               "panel_clips": "panel", "conditions": "conditions", "strata": "strata"}
    for key, audit_key in mapping.items():
        if contract[key] != inputs["inputs"][audit_key]:
            raise ValueError(f"campaign reference cross-link mismatch: {key}")
    if contract["software_versions"] != software_versions():
        raise ValueError("software versions differ from the evaluation contract")
    configurations = contract["configuration_sha256"]
    if set(configurations) != ARMS or any(set(configurations[arm]) != {str(seed) for seed in SEEDS} for arm in ARMS):
        raise ValueError("all twelve frozen configurations are required")
    if not smoke:
        verify_prerequisites(contract)
        from train_relative_confirmation import verify_entrypoint_smoke
        if set(contract["entrypoint_smokes"]) != ARMS:
            raise ValueError("all four confirmation-entrypoint smokes are required")
        for arm in sorted(ARMS):
            saved = json.loads(verified(contract["entrypoint_smokes"][arm], "entrypoint smoke").read_text())
            draft_path = verified(saved["draft_contract"], "smoke draft")
            draft = verify_contract(draft_path, saved["draft_contract"]["sha256"], smoke=True)
            if verify_entrypoint_smoke(Path(saved["run_dir"]), draft, saved["draft_contract"], arm) != saved:
                raise ValueError("confirmation-entrypoint smoke does not reproduce")
    return contract
