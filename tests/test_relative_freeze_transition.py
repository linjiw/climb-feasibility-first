"""Check finalization without launching any scientific job or replacing verifiers."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from relative_campaign_fixture import record
from relative_confirmation_fixture import build_strict_campaign
from relative_confirmation_setup import verify_contract

SCRIPT = ROOT / "tools/freeze_relative_confirmation.sh"


def invoke(draft, out, *, check_only=False):
    argv = ["bash", str(SCRIPT), "--draft", str(draft), "--draft-sha256", record(draft)["sha256"],
            "--out-dir", str(out)]
    if check_only:
        argv.append("--check-only")
    return subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)


@pytest.fixture(scope="module")
def complete_draft(tmp_path_factory):
    root = tmp_path_factory.mktemp("SYNTHETIC_freeze")
    build_strict_campaign(root)
    return root / "SYNTHETIC_draft.json"


def test_current_pending_draft_cannot_enable_or_write(tmp_path):
    draft = ROOT / "reports/relative_progress_2026-09-05/confirmation_preparation_adapter/draft_contract.json"
    # Freeze an immutable test copy with an explicitly missing expected result;
    # actual queued jobs may finish during the test.
    value = json.loads(draft.read_text())
    value["entrypoint_smokes"]["D"] = {"pending_path": str(tmp_path / "absent_result.json")}
    path = tmp_path / "pending_draft.json"
    path.write_text(json.dumps(value))
    out = tmp_path / "must_not_exist"
    result = invoke(path, out)
    assert result.returncode == 2, result.stderr
    assert json.loads(result.stdout)["status"] == "prerequisites_pending"
    assert not out.exists()


def test_failed_available_prerequisite_is_not_hidden_by_pending(tmp_path):
    source = ROOT / "reports/relative_progress_2026-09-05/confirmation_preparation_adapter/draft_contract.json"
    draft = json.loads(source.read_text())
    failure = tmp_path / "SYNTHETIC_failed_decision.json"
    failure.write_text(json.dumps({"status": "calibration_fail"}))
    draft["failure_calibration"]["31"]["decision"] = record(failure)
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(draft))
    out = tmp_path / "absent"
    result = invoke(path, out)
    assert result.returncode == 1 and "available prerequisite has not passed" in result.stderr
    assert not out.exists()


def test_complete_prerequisites_check_only_creates_nothing(complete_draft, tmp_path):
    out = tmp_path / "absent"
    result = invoke(complete_draft, out, check_only=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "ready_to_freeze"
    assert not out.exists()


def test_complete_freeze_reproduces_and_cannot_overwrite(complete_draft, tmp_path):
    out = tmp_path / "SYNTHETIC_freeze_output"
    original = complete_draft.read_bytes()
    result = invoke(complete_draft, out)
    assert result.returncode == 0, result.stderr
    receipt = json.loads((out / "freeze_result.json").read_text())
    contract_record = receipt["contract"]
    contract = verify_contract(Path(contract_record["path"]), contract_record["sha256"])
    assert "SYNTHETIC" in contract["classification"]
    assert contract["training_sources"]["tools/freeze_relative_confirmation.sh"] == record(SCRIPT)
    assert receipt["jobs_launched"] == 0
    assert len(json.loads((out / "schedule.json").read_text())["jobs"]) == 60
    assert not (out / "campaign").exists()
    assert complete_draft.read_bytes() == original
    subprocess.run(["sha256sum", "--status", "-c", str(out / "confirmation.sha256")], check=True)
    retry = invoke(complete_draft, out)
    assert retry.returncode != 0 and "File exists" in retry.stderr
    subprocess.run(["sha256sum", "--status", "-c", str(out / "confirmation.sha256")], check=True)
