"""Test intervention specificity and rejection of corrupted measured traces."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest
import torch

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / "tools"))

from analyze_physics_sensitivity_smoke import verify_payload
from physics_sensitivity import apply_knee_spec, condition, foot_ids, robot_config
from mjlab.asset_zoo.robots.unitree_g1.g1_constants import get_g1_robot_cfg


@pytest.fixture(scope="module")
def measured():
    path = WORK / "reports/physics_sensitivity_2026-09-06/cpu_smoke"
    result = json.loads((path / "result.json").read_text())
    traces = torch.load(path / "traces.pt", map_location="cpu", weights_only=True)
    entity = get_g1_robot_cfg().build()
    entity.spec.worldbody.add_geom(name="fixture_ground", type=0, size=[0, 0, 0.1])
    return result, traces, foot_ids(entity.compile())


def test_saved_measurement_reproduces(measured):
    assert verify_payload(*measured)["status"] == "saved_trace_verification_pass"


@pytest.mark.parametrize("fault", ["delay", "knee", "hip", "friction", "initial", "reset", "repeat", "missing"])
def test_corrupted_trace_rejected(measured, fault):
    result, original, feet = measured
    result, traces = deepcopy(result), deepcopy(original)
    if fault == "delay":
        traces["delay_20ms"]["controls"][5, 0, 0] += 0.01
    elif fault == "knee":
        traces["knee_90nm"]["saturation_forces"][0, 0, 16] = 139
    elif fault == "hip":
        result["conditions"][5]["compiled"]["actuators"]["left_hip_roll_joint"]["force_range"] = [-90, 90]
    elif fault == "friction":
        traces["friction_0p3"]["friction_after"][0, feet[0], 1] += 0.1
    elif fault == "initial":
        traces["delay_5ms"]["initial"]["qpos"][0, 0] += 0.1
    elif fault == "reset":
        traces["delay_10ms"]["partial_reset_ctrl"][1, 0] = 0.123
    elif fault == "repeat":
        traces["unchanged_repeat"]["positions"][0, 0, 0] += 0.1
    elif fault == "missing":
        traces.pop("delay_5ms")
    with pytest.raises(ValueError):
        verify_payload(result, traces, feet)


def test_unknown_condition_rejected():
    with pytest.raises(ValueError):
        condition("delay_500ms")


@pytest.mark.parametrize("name,cap", [("knee_120nm", 120), ("knee_90nm", 90)])
def test_knee_targets_preserve_shared_hip_limits(name, cap):
    cfg = get_g1_robot_cfg()
    entity = robot_config(cfg, name).build()
    apply_knee_spec(entity, name)
    model = entity.compile()
    for knee in ("left_knee_joint", "right_knee_joint"):
        assert model.actuator(knee).forcerange.tolist() == [-cap, cap]
    for hip in ("left_hip_roll_joint", "right_hip_roll_joint"):
        assert model.actuator(hip).forcerange.tolist() == [-139, 139]
    assert cfg.articulation.actuators[2].effort_limit == 139


def test_delay_config_does_not_mutate_original():
    original = get_g1_robot_cfg()
    changed = robot_config(original, "delay_20ms")
    assert all(a.delay_max_lag == 0 for a in original.articulation.actuators)
    assert all((a.delay_min_lag, a.delay_max_lag) == (4, 4) for a in changed.articulation.actuators)


def test_missing_knee_fails_before_any_clamp_edit():
    entity = get_g1_robot_cfg().build()
    entity.spec.actuator("left_knee_joint").name = "missing_knee"
    with pytest.raises(ValueError):
        apply_knee_spec(entity, "knee_90nm")
    assert list(entity.spec.actuator("right_knee_joint").forcerange) == [-139, 139]
