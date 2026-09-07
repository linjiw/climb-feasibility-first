"""Isolated S1 interventions; exact named knee targets and physics-step delays."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import re

import numpy as np


CONDITIONS = {
    "unchanged": {"delay_steps": 0, "knee_cap_nm": None, "foot_friction": None},
    "delay_5ms": {"delay_steps": 1, "knee_cap_nm": None, "foot_friction": None},
    "delay_10ms": {"delay_steps": 2, "knee_cap_nm": None, "foot_friction": None},
    "delay_20ms": {"delay_steps": 4, "knee_cap_nm": None, "foot_friction": None},
    "knee_120nm": {"delay_steps": 0, "knee_cap_nm": 120.0, "foot_friction": None},
    "knee_90nm": {"delay_steps": 0, "knee_cap_nm": 90.0, "foot_friction": None},
    "friction_0p3": {"delay_steps": 0, "knee_cap_nm": None, "foot_friction": 0.3},
    "friction_1p2": {"delay_steps": 0, "knee_cap_nm": None, "foot_friction": 1.2},
}
KNEES = {"left_knee_joint", "right_knee_joint"}
FOOT_PATTERN = re.compile(r"^(left|right)_foot[1-7]_collision$")


def condition(name: str) -> dict:
    if name not in CONDITIONS:
        raise ValueError(f"unknown S1 condition: {name}")
    return dict(CONDITIONS[name])


def robot_config(base, name: str):
    """Clone the robot, retaining actuator ordering and all non-delay fields."""
    selected = condition(name)
    cfg = deepcopy(base)
    if selected["delay_steps"]:
        cfg.articulation = replace(cfg.articulation, actuators=tuple(
            replace(a, delay_min_lag=selected["delay_steps"],
                    delay_max_lag=selected["delay_steps"])
            for a in cfg.articulation.actuators))
    return cfg


def apply_knee_spec(entity, name: str) -> None:
    """Limit only named knee actuators after construction, before compilation.

    Hip roll shares the upstream config group. Editing named MjSpec actuators
    avoids changing that group's hip limits or reordering its actuator indices.
    """
    cap = condition(name)["knee_cap_nm"]
    if cap is None:
        return
    matched = []
    for actuator in entity.spec.actuators:
        if actuator.name.split("/")[-1] in KNEES:
            if actuator.target.split("/")[-1] != actuator.name.split("/")[-1]:
                raise ValueError("knee actuator name/target mismatch")
            matched.append(actuator)
    if {a.name.split("/")[-1] for a in matched} != KNEES:
        raise ValueError("requires exactly two named knee actuators")
    for actuator in matched:
        actuator.forcelimited = True
        actuator.forcerange = [-cap, cap]


def foot_ids(model) -> list[int]:
    ids = [i for i in range(model.ngeom)
           if FOOT_PATTERN.fullmatch(model.geom(i).name.split("/")[-1])]
    if len(ids) != 14:
        raise ValueError("expected exactly 14 G1 foot collision geoms")
    return ids


def apply_friction(sim, name: str) -> None:
    """Override sliding friction after common startup draws; preserve RNG state.

    Caller must expand geom_friction before taking the shared startup snapshot.
    Torsional/rolling coefficients and every non-foot geom remain unchanged.
    """
    coefficient = condition(name)["foot_friction"]
    if coefficient is None:
        return
    if "geom_friction" not in sim.expanded_fields:
        raise ValueError("expand geom_friction before shared startup initialization")
    sim.model.geom_friction[:, foot_ids(sim.mj_model), 0] = coefficient


def compiled_parameters(model) -> dict:
    """Export name-indexed physics to check intervention specificity."""
    return {
        "actuator_order": [model.actuator(i).name for i in range(model.nu)],
        "actuators": {model.actuator(i).name: {
            "target": model.joint(int(model.actuator_trnid[i, 0])).name,
            "force_limited": bool(model.actuator_forcelimited[i]),
            "force_range": model.actuator_forcerange[i].tolist(),
            "gear": model.actuator_gear[i].tolist(),
            "gain": model.actuator_gainprm[i].tolist(),
            "bias": model.actuator_biasprm[i].tolist(),
        } for i in range(model.nu)},
        "joint_armature": np.asarray(model.dof_armature).tolist(),
        "joint_ranges": np.asarray(model.jnt_range).tolist(),
        "body_mass": np.asarray(model.body_mass).tolist(),
    }
