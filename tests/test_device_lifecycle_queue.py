"""Validate CPU entrypoint parity and fail-closed GPU queue prerequisites."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / "tools"))
from analyze_device_lifecycle import analyze
from eval_device_lifecycle import verify_graphs
from queue_device_lifecycle import prerequisites_ready, sha256, verify_design


def test_measured_cpu_device_entrypoint():
    result = analyze(WORK / "reports/device_lifecycle_cpu_2026-09-06")
    assert result["status"] == "device_lifecycle_pass"
    assert result["device"] == "cpu"
    assert result["episode_rows"] == 21


@pytest.mark.parametrize("fault", ["device", "disabled", "missing_graph", "step_count", "reset_count"])
def test_gpu_graph_receipt_rejects_missing_execution(fault):
    graph = {"device": "cuda:0", "use_cuda_graph": True,
             "graphs": {k: True for k in ("step", "forward", "reset", "sense")},
             "launches": {"step": 600, "forward": 150, "reset": 2, "sense": 150}}
    verify_graphs(graph, "cuda:0", 600)
    if fault == "device":
        graph["device"] = "cpu"
    elif fault == "disabled":
        graph["use_cuda_graph"] = False
    elif fault == "missing_graph":
        graph["graphs"]["sense"] = False
    elif fault == "step_count":
        graph["launches"]["step"] -= 1
    elif fault == "reset_count":
        graph["launches"]["reset"] = 0
    with pytest.raises(ValueError):
        verify_graphs(graph, "cuda:0", 600)


def test_both_prerequisites_required(tmp_path):
    confirmation, pilot = tmp_path / "confirmation.json", tmp_path / "pilot.json"
    jobs = [{"stage": "train", "arm": "U", "seed": 21}]
    queue = {"prerequisites": [
        {"path": str(confirmation), "status": "completed", "completed_jobs": jobs},
        {"path": str(pilot), "status": "development_pilot_completed", "stationarity_established": False}]}
    assert prerequisites_ready(queue) is False
    confirmation.write_text(json.dumps({"status": "completed", "completed_jobs": jobs, "policy_endpoints_opened": True}))
    assert prerequisites_ready(queue) is False
    pilot.write_text(json.dumps({"status": "development_pilot_completed", "stationarity_established": False}))
    assert prerequisites_ready(queue) is True
    confirmation.write_text(json.dumps({"status": "completed", "completed_jobs": [], "policy_endpoints_opened": True}))
    with pytest.raises(ValueError, match="bound schedule"):
        prerequisites_ready(queue)


@pytest.mark.parametrize("status", ["execution_stopped", "invalid", "not_tested"])
def test_stopped_confirmation_is_not_permission(tmp_path, status):
    terminal = tmp_path / "terminal.json"
    terminal.write_text(json.dumps({"status": status}))
    with pytest.raises(ValueError, match="prerequisite stopped"):
        prerequisites_ready({"prerequisites": [{"path": str(terminal), "status": "completed"}]})


def test_source_binding_and_cpu_gate(tmp_path):
    cpu = tmp_path / "cpu.json"
    cpu.write_text(json.dumps({"status": "device_lifecycle_pass", "device": "cpu"}))
    design = {"stage": "device_lifecycle_development", "full_evaluation_enabled": False,
              "evaluator_arguments": {"device": "cuda:0"},
              "queue": {"automatic_retries": 0, "cpu_verification": str(cpu)},
              "bindings": {str(cpu): sha256(cpu)}}
    path = tmp_path / "design.json"
    path.write_text(json.dumps(design))
    digest = sha256(path)
    assert verify_design(path, digest) == design
    cpu.write_text(json.dumps({"status": "incomplete", "device": "cpu"}))
    with pytest.raises(ValueError, match="dependency changed"):
        verify_design(path, digest)
    altered = deepcopy(design)
    altered["queue"]["automatic_retries"] = 1
    path.write_text(json.dumps(altered))
    with pytest.raises(ValueError, match="single-attempt"):
        verify_design(path, sha256(path))
