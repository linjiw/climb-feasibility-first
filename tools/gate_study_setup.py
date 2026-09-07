"""Fixed H1 configurations and prospective launch contract validation."""

from __future__ import annotations

from dataclasses import fields
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from climb.env_cfg import read_clip_list
from climb.gate_ablation import file_digest
from climb.gate_study import GateStudyCommandCfg, PROTOCOL, verify_support
from climb.segment_env_cfg import segment_native_g1_tracking_env_cfg
from eval_paired_v2 import software_versions
from mjlab.tasks.tracking.config.g1.rl_cfg import unitree_g1_tracking_ppo_runner_cfg
from relative_confirmation_setup import canonical

ARMS = ("on", "off")
SEEDS = (61, 62, 63)
EVALUATION_ITERATIONS = (1000, 2000, 3000, 3999)
SPEC = {"arms": ["on", "off"], "seeds": [61, 62, 63], "num_envs": 512,
        "iterations": 4000, "rollout_steps": 24, "save_interval": 100,
        "smoke_seed": 81, "smoke_num_envs": 8, "smoke_iterations": 20,
        "horizon_steps": 50, "exploration_ratio": 0.8, "unit_cap": 0.05, "clip_cap": 0.25,
        "benefit_target": 0.02, "nonregression_margin": -0.01}


def record(path: Path) -> dict:
    return {"path": str(path.resolve()), "sha256": file_digest(path)}


def verified(entry: dict) -> Path:
    if set(entry) != {"path", "sha256"} or file_digest(Path(entry["path"])) != entry["sha256"]:
        raise ValueError("missing or changed bound artifact")
    return Path(entry["path"]).resolve()


def sources() -> dict[str, str]:
    import mjlab
    import rsl_rl
    paths = set((ROOT / "climb").rglob("*.py")) | set((ROOT / "tools").glob("*.py"))
    mjlab_root = Path(mjlab.__file__).resolve().parent
    paths.update(mjlab_root.rglob("*.py"))
    paths.update(Path(rsl_rl.__file__).resolve().parent.rglob("*.py"))
    paths.update(p for p in (mjlab_root / "asset_zoo/robots/unitree_g1/xmls").rglob("*") if p.is_file())
    return {str(p.resolve()): file_digest(p) for p in sorted(paths)}


def configs(contract: dict, arm: str, seed: int, *, smoke: bool, digest: str):
    if arm not in ARMS or seed not in ((81,) if smoke else SEEDS):
        raise ValueError("not an assigned gate-study arm/seed")
    support = contract["support"][arm]
    path = verified(support)
    verify_support(path, support["sha256"], arm)
    cfg = segment_native_g1_tracking_env_cfg(
        motion_files=read_clip_list(str(verified(contract["training_clips"])), contract["bank"]),
        segment_manifest=str(path), segment_sampling_mode="adaptive", sampler_seed=seed, env_seed=seed,
        segment_rank="failure", segment_exploration_ratio=0.8, segment_difficulty_power=1.0,
        segment_progress_window=10, segment_progress_floor=0.0,
        max_unit_probability=0.05, max_clip_probability=0.25, verify_motion_hashes=True, failure_penalty=-10)
    command = cfg.commands["motion"]
    cfg.commands["motion"] = GateStudyCommandCfg(
        **{f.name: getattr(command, f.name) for f in fields(command)}, gate_admission=arm,
        gate_manifest_sha256=support["sha256"], gate_stage="entrypoint_smoke" if smoke else "confirmation",
        gate_contract_sha256=digest)
    cfg.scene.num_envs = 8 if smoke else 512
    agent = unitree_g1_tracking_ppo_runner_cfg()
    agent.seed, agent.max_iterations, agent.save_interval = seed, 20 if smoke else 4000, 100
    agent.resume, agent.logger = False, "tensorboard"
    agent.run_name = f"gate_{arm}_{'entrypoint_smoke' if smoke else 'confirmation'}_s{seed}"
    return cfg, agent


def configuration_digest(cfg, agent) -> str:
    value = canonical({"env": cfg, "agent": agent})
    # The contract binds these hashes; remove its own digest to avoid a cycle.
    value["env"]["fields"]["commands"]["motion"]["fields"]["gate_contract_sha256"] = "contract-bound-at-launch"
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_contract(path: Path, digest: str, *, smoke: bool) -> dict:
    contract = json.loads(verified({"path": str(path), "sha256": digest}).read_text())
    if (contract.get("schema_version") != "gate_study_contract/1"
            or contract.get("status") != ("draft" if smoke else "frozen_before_training")
            or contract.get("full_training_enabled") is not (not smoke)
            or contract.get("specification") != SPEC):
        raise ValueError("full H1 training requires its own fixed prospective frozen contract")
    if contract["sources"] != sources() or contract["software_versions"] != software_versions():
        raise ValueError("gate-study runtime or software changed")
    for arm in ARMS:
        value = verify_support(verified(contract["support"][arm]), contract["support"][arm]["sha256"], arm)
        original = json.loads(verified(contract["development_support"][arm]).read_text())
        if any(value[k] != original[k] for k in ("sources", "source_units", "admissible_units", "unit_table_sha256", "horizon_steps")):
            raise ValueError("study support changed from tested development views")
        for seed in SEEDS:
            cfg, agent = configs(contract, arm, seed, smoke=False, digest=digest)
            if configuration_digest(cfg, agent) != contract["configuration_sha256"][arm][str(seed)]:
                raise ValueError("full configuration differs from prospective binding")
    if not smoke:
        if "SYNTHETIC" in contract.get("classification", ""):
            raise ValueError("synthetic fixture cannot authorize scientific execution")
        terminal = json.loads(verified(contract["previous_confirmation_terminal"]).read_text())
        if terminal.get("status") != "completed":
            raise ValueError("resolve the existing confirmation before H1")
        audit = json.loads(verified(contract["fresh_seed_audit"]).read_text())
        if audit.get("status") != "fresh_seed_audit_pass" or audit.get("seeds") != list(SEEDS):
            raise ValueError("fresh training seeds not audited")
        # Require actual GPU entrypoint validation of both arms before full training.
        from gate_training_provenance import verify_training
        for arm in ARMS:
            smoke_result = json.loads(verified(contract["gpu_entrypoint_smokes"][arm]).read_text())
            draft_record = smoke_result["contract"]
            draft = verify_contract(verified(draft_record), draft_record["sha256"], smoke=True)
            replay = verify_training(Path(smoke_result["run_dir"]), draft, draft_record["sha256"], arm, 81, smoke=True)
            if replay != smoke_result or replay["device"] != "cuda:0":
                raise ValueError("GPU entrypoint smoke does not reproduce")
    return contract
