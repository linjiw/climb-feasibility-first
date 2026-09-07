#!/usr/bin/env python3
"""Verify saved S1 fixture traces independently of its online assertions."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import torch

from physics_sensitivity import CONDITIONS, KNEES, foot_ids


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_payload(result: dict, traces: dict, feet: list[int]) -> dict:
    rows = result["conditions"]
    if ([r["condition"] for r in rows] != list(CONDITIONS)
            or set(traces) != {*CONDITIONS, "unchanged_repeat"}):
        raise ValueError("incomplete or reordered fixture conditions")
    base = traces["unchanged"]
    compiled = rows[0]["compiled"]
    order = compiled["actuator_order"]
    if len(order) != 29 or len(set(order)) != 29 or len(feet) != 14:
        raise ValueError("unexpected robot actuator/foot identity")
    if base["controls"].shape != (12, 2, 29):
        raise ValueError("requires full two-world, twelve-substep traces")
    # Check the commanded ramp independently, including joint-distinct offsets.
    expected_offsets = torch.arange(29).float() * 0.001 + 0.01
    if not torch.equal(base["controls"][0, 0].sort().values, expected_offsets):
        raise ValueError("baseline first command differs from fixed ramp")
    for i in range(12):
        if not torch.allclose(base["controls"][i], base["controls"][0] + i * 0.01, atol=3e-8, rtol=0):
            raise ValueError("baseline command is not the fixed ramp")
    checked = []
    for row in rows:
        name = row["condition"]
        data, selected = traces[name], CONDITIONS[name]
        if row["parameters"] != selected or row["physics_timestep_s"] != 0.005:
            raise ValueError("condition differs from fixed physical units")
        for key, value in base["initial"].items():
            if not torch.equal(data["initial"][key], value):
                raise ValueError("initial fixture state or RNG differs")
        lag = selected["delay_steps"]
        indices = torch.arange(12).sub(lag).clamp_min(0)
        if not torch.equal(data["controls"], base["controls"][indices]):
            raise ValueError("saved command trace does not exhibit declared delay")
        expected_parameters = deepcopy(compiled)
        cap = selected["knee_cap_nm"]
        if cap is not None:
            for knee in KNEES:
                expected_parameters["actuators"][knee]["force_range"] = [-cap, cap]
        if row["compiled"] != expected_parameters:
            raise ValueError("unrelated compiled parameter changed")
        force = data["saturation_forces"]
        if force.shape != (2, 2, 29) or not torch.isfinite(force).all():
            raise ValueError("incomplete saturation trace")
        for sign_index, bound in enumerate((1, 0)):
            limits = torch.tensor([row["compiled"]["actuators"][a]["force_range"][bound] for a in order])
            if not torch.allclose(force[sign_index], limits[None, :].expand(2, -1), atol=1e-4, rtol=0):
                raise ValueError("saved force does not reach declared signed clamp")
        friction = base["initial"]["friction"].clone()
        if selected["foot_friction"] is not None:
            friction[:, feet, 0] = selected["foot_friction"]
        if not torch.equal(data["friction_after"], friction):
            raise ValueError("friction override missing or modifies unrelated coefficients")
        reset = data["partial_reset_ctrl"]
        if not torch.equal(reset[0], torch.full((29,), 0.123)):
            raise ValueError("reset row backfill failed")
        if not torch.equal(reset[1], torch.full((29,), -1000.0 if lag else 0.123)):
            raise ValueError("reset altered another row's buffer history")
        if data["positions"].shape != base["positions"].shape or not torch.isfinite(data["positions"]).all():
            raise ValueError("incomplete or nonfinite physics trace")
        checked.append({"condition": name, "delay_ms": lag * 5,
                        "left_knee_positive_force_nm": float(force[0, 0, order.index("left_knee_joint")]),
                        "left_hip_roll_positive_force_nm": float(force[0, 0, order.index("left_hip_roll_joint")]),
                        "sliding_friction_per_world": data["friction_after"][:, feet[0], 0].tolist()})
    repeat = traces["unchanged_repeat"]
    for key in ("controls", "positions", "saturation_forces", "friction_after", "partial_reset_ctrl"):
        if not torch.equal(base[key], repeat[key]):
            raise ValueError("baseline repeat differs")
    return {"status": "saved_trace_verification_pass", "conditions": checked,
            "classification": "measured CPU actuator instrumentation; no policy outcomes",
            "full_evaluation_enabled": False, "confirmation_endpoints_opened": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--smoke-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    design_path = args.smoke_dir / "design.json"
    result_path = args.smoke_dir / "result.json"
    trace_path = args.smoke_dir / "traces.pt"
    design = json.loads(design_path.read_text())
    result = json.loads(result_path.read_text())
    if (result["design_sha256"] != sha256(design_path)
            or result["traces_sha256"] != sha256(trace_path)):
        raise ValueError("saved artifact hashes differ")
    for path, digest in design["sources"].items():
        if sha256(Path(path)) != digest:
            raise ValueError("collector source changed")
    inventory = design["runtime_inventory"]
    if sha256(Path(inventory["path"])) != inventory["sha256"]:
        raise ValueError("bound runtime inventory changed")
    for path, digest in json.loads(Path(inventory["path"]).read_text())["files"].items():
        if sha256(Path(path)) != digest:
            raise ValueError("original runtime changed")
    root = args.campaign_root.resolve()
    contract = root / "reports/relative_progress_2026-09-05/confirmation_freeze/contract.json"
    if sha256(contract) != design["contract_sha256"]:
        raise ValueError("wrong original campaign")
    sys.path.insert(0, str(root))
    from mjlab.asset_zoo.robots.unitree_g1.g1_constants import get_g1_robot_cfg
    entity = get_g1_robot_cfg().build()
    entity.spec.worldbody.add_geom(name="fixture_ground", type=0, size=[0, 0, 0.1])
    feet = foot_ids(entity.compile())
    traces = torch.load(trace_path, map_location="cpu", weights_only=True)
    checked = verify_payload(result, traces, feet)
    checked.update(collector_result_sha256=sha256(result_path), traces_sha256=sha256(trace_path),
                   analyzer_sha256=sha256(Path(__file__)))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(checked, handle, indent=2)
        handle.write("\n")
    print(checked["status"])


if __name__ == "__main__":
    main()
