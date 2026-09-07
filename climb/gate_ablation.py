"""Development-only admission ablation on a shared exact-start candidate table."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import torch

from climb.segment_command import SegmentNativeMotionCommand, SegmentNativeMotionCommandCfg
from climb.segment_runtime import SegmentSampler

PROTOCOL = "matched_gate_development/1"


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_manifest(path: Path, digest: str, admission: str) -> dict:
    if file_digest(path) != digest:
        raise ValueError("gate runtime manifest changed")
    manifest = json.loads(path.read_text())
    gate = manifest.get("gate_ablation", {})
    if (gate.get("protocol") != PROTOCOL or gate.get("admission") != admission
            or gate.get("full_training_enabled") is not False):
        raise ValueError("requires the explicit development-only admission profile")
    candidates = manifest["source_units"]
    selected = [row for row in candidates if admission == "off" or row["gate_admitted"]]
    expected = [{**row, "table_index": i, "deployment_mass": row["legal_start_count"]}
                for i, row in enumerate(selected)]
    if manifest["admissible_units"] != expected:
        raise ValueError("runtime support does not equal the declared admission mask")
    if admission not in ("on", "off"):
        raise ValueError("unknown admission setting")
    return manifest


def sampler_for(path: Path, seed: int) -> SegmentSampler:
    return SegmentSampler(path, mode="adaptive", seed=seed, rank="failure",
                          exploration_ratio=0.8, difficulty_power=1.0,
                          decay=0.99, progress_window=10, progress_floor=0.0,
                          max_unit_probability=0.05, max_clip_probability=0.25)


def rejection_telemetry(sampler: SegmentSampler) -> dict:
    rows = sampler.manifest["admissible_units"]
    rejected = torch.tensor([not row["gate_admitted"] for row in rows], dtype=torch.bool)
    base = sampler.deployment_mass.double()
    base /= base.sum()
    clip_mass = torch.bincount(sampler.intervals.clip_ids, weights=sampler.probabilities)
    return {
        "protocol": PROTOCOL, "admission": sampler.manifest["gate_ablation"]["admission"],
        "candidate_partition_sha256": sampler.manifest["gate_ablation"]["candidate_partition_sha256"],
        "runtime_units": sampler.num_units,
        "uncapped_prior_rejected_mass": float(base[rejected].sum()),
        "post_cap_rejected_mass": float(sampler.probabilities[rejected].sum()),
        "rejected_completed_trials": int(sampler.lifetime_attempts[rejected].sum()),
        "rejected_failed_trials": int(sampler.lifetime_failures[rejected].sum()),
        "max_clip_mass": float(clip_mass.max()),
        "full_training_enabled": False,
    }


class GateAblationCommand(SegmentNativeMotionCommand):
    """Keep the original exact-trial implementation and change only its support."""

    def __init__(self, cfg: GateAblationCommandCfg, env: Any) -> None:
        verified_manifest(Path(cfg.segment_manifest), cfg.gate_manifest_sha256, cfg.gate_admission)
        if (cfg.segment_sampling_mode, cfg.segment_rank, cfg.segment_exploration_ratio,
                cfg.segment_difficulty_power, cfg.segment_progress_floor, cfg.segment_decay,
                cfg.max_unit_probability, cfg.max_clip_probability) != (
                    "adaptive", "failure", 0.8, 1.0, 0.0, 0.99, 0.05, 0.25):
            raise ValueError("gate ablation must retain the fixed D profile")
        super().__init__(cfg, env)

    def segment_telemetry(self) -> dict[str, object]:
        result = super().segment_telemetry()
        result["gate_ablation"] = rejection_telemetry(self.sampler)
        return result


@dataclass
class GateAblationCommandCfg(SegmentNativeMotionCommandCfg):
    gate_admission: Literal["on", "off"] = "on"
    gate_manifest_sha256: str = ""

    def build(self, env: Any) -> GateAblationCommand:
        return GateAblationCommand(self, env)
