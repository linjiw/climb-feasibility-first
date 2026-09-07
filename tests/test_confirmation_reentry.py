"""Keep operational reentry distinct from scientific retries or endpoint rescue."""

import importlib.util
import json
from pathlib import Path

import pytest

WORK = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("follow_reentry", WORK / "tools/follow_confirmation_reentry.py")
follow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(follow)


@pytest.fixture
def binding(tmp_path):
    contract = tmp_path / "contract.json"
    contract.write_text("{}")
    return {"sources": {}, "contract": {"path": str(contract), "sha256": follow.sha256(contract)},
            "campaign": str(tmp_path), "root": str(tmp_path)}


@pytest.mark.parametrize("status", ["execution_stopped", "invalid", "not_tested"])
def test_stopped_campaign_never_opens_analysis(binding, status):
    campaign = Path(binding["campaign"])
    (campaign / "terminal_status.json").write_text(json.dumps({"status": status}))
    (campaign / "analysis.json").write_text("deliberately not valid JSON")
    assert follow.postprocess(binding)["policy_endpoints_opened"] is False


def test_wrong_contract_blocks_completed_campaign(binding):
    campaign = Path(binding["campaign"])
    (campaign / "terminal_status.json").write_text('{"status":"completed"}')
    (campaign / "campaign_manifest.json").write_text('{"contract":{}}')
    with pytest.raises(ValueError, match="another contract"):
        follow.postprocess(binding)


def test_changed_dependency_rejected(binding):
    dependency = Path(binding["campaign"]) / "dependency.py"
    dependency.write_text("pass")
    binding["sources"][str(dependency)] = follow.sha256(dependency)
    dependency.write_text("changed")
    with pytest.raises(ValueError, match="dependency changed"):
        follow.verify_binding(binding)


def test_actual_reentry_schedule_changes_only_output_paths():
    root = Path('/home/linjiw/climb-feasibility-first')
    freeze = root / 'reports/relative_progress_2026-09-05/confirmation_freeze'
    previous = freeze / 'campaign'
    current = freeze / 'campaign_gpu_reentry_2026-09-06'
    old = json.loads((previous / 'schedule.json').read_text())
    new = json.loads((current / 'schedule.json').read_text())
    assert json.loads(json.dumps(new).replace(str(current), str(previous))) == old
    assert sum(j['stage'] == 'train' for j in new['jobs']) == 12
    assert sum(j['stage'] == 'evaluate' for j in new['jobs']) == 48
