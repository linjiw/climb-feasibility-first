"""Exact gate-study runtime; launch authority belongs to the enclosing contract."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Literal

from climb.gate_ablation import file_digest, rejection_telemetry
from climb.segment_command import SegmentNativeMotionCommand, SegmentNativeMotionCommandCfg

PROTOCOL = "matched_gate_study/1"


def verify_support(path: Path, digest: str, admission: str) -> dict:
    if file_digest(path) != digest:
        raise ValueError("gate-study support changed")
    value = json.loads(path.read_text())
    gate = value.get("gate_ablation", {})
    if (admission not in ("on", "off") or gate.get("protocol") != PROTOCOL
            or gate.get("admission") != admission or gate.get("requires_frozen_launch_contract") is not True):
        raise ValueError("wrong gate-study support protocol or admission")
    selected = [r for r in value["source_units"] if admission == "off" or r["gate_admitted"]]
    if value["admissible_units"] != [{**r, "table_index": i, "deployment_mass": r["legal_start_count"]}
                                     for i, r in enumerate(selected)]:
        raise ValueError("gate-study support does not equal the admission mask")
    return value


class GateStudyCommand(SegmentNativeMotionCommand):
    def __init__(self, cfg: GateStudyCommandCfg, env: Any) -> None:
        verify_support(Path(cfg.segment_manifest), cfg.gate_manifest_sha256, cfg.gate_admission)
        if cfg.gate_stage not in ("entrypoint_smoke", "confirmation") or len(cfg.gate_contract_sha256) != 64:
            raise ValueError("gate-study runtime requires an explicit stage and contract identity")
        if (cfg.segment_sampling_mode, cfg.segment_rank, cfg.segment_exploration_ratio,
                cfg.segment_difficulty_power, cfg.segment_progress_floor, cfg.segment_decay,
                cfg.max_unit_probability, cfg.max_clip_probability, cfg.segment_progress_window,
                cfg.curriculum_update_interval_steps) != (
                    "adaptive", "failure", 0.8, 1.0, 0.0, 0.99, 0.05, 0.25, 10, 50):
            raise ValueError("gate-study D configuration changed")
        super().__init__(cfg, env)

    def segment_telemetry(self) -> dict[str, object]:
        result = super().segment_telemetry()
        gate = rejection_telemetry(self.sampler)
        gate.update(protocol=PROTOCOL, full_training_enabled=self.cfg.gate_stage == "confirmation",
                    stage=self.cfg.gate_stage, campaign_contract_sha256=self.cfg.gate_contract_sha256)
        result["gate_ablation"] = gate
        return result


@dataclass
class GateStudyCommandCfg(SegmentNativeMotionCommandCfg):
    gate_admission: Literal["on", "off"] = "on"
    gate_manifest_sha256: str = ""
    gate_stage: Literal["entrypoint_smoke", "confirmation"] = "entrypoint_smoke"
    gate_contract_sha256: str = ""

    def build(self, env: Any) -> GateStudyCommand:
        return GateStudyCommand(self, env)
