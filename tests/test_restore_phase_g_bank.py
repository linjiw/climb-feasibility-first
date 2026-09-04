"""Tests for fail-closed licensed Phase-G payload intake."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.restore_phase_g_bank import audit_source, link_bank, load_requirements
from tools.research_preflight import check_motion_bank


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _inputs(tmp_path: Path) -> tuple[Path, Path, dict[str, bytes]]:
    payloads = {"training": b"train", "evaluation": b"eval"}
    sources = [
        {
            "clip": "training",
            "motion_sha256": _sha(payloads["training"]),
        }
    ]
    frozen = {
        "horizon_steps": 50,
        "sources": sources,
        "source_units": [],
        "admissible_units": [],
    }
    canonical = json.dumps(
        frozen, sort_keys=True, separators=(",", ":")
    ).encode()
    unit_table = {
        "schema_version": "segment_unit_table/1",
        **frozen,
        "unit_table_sha256": hashlib.sha256(canonical).hexdigest(),
    }
    unit_path = tmp_path / "unit_table.json"
    unit_path.write_text(json.dumps(unit_table))
    panel_path = tmp_path / "panel_manifest.json"
    panel_list = tmp_path / "panel.txt"
    panel_list.write_text("evaluation\n")
    panel_path.write_text(
        json.dumps(
            {
                "schema_version": "g_segment_eval_panel/1",
                "size": 1,
                "motion_sha256": {"evaluation": _sha(payloads["evaluation"])},
                "panel_txt_sha256": _sha(panel_list.read_bytes()),
            }
        )
    )
    return unit_path, panel_path, payloads


def test_scope_separates_calibration_from_full_payload(tmp_path: Path) -> None:
    unit, panel, _ = _inputs(tmp_path)

    calibration, calibration_counts, _ = load_requirements(
        unit, panel, scope="calibration"
    )
    full, full_counts, _ = load_requirements(unit, panel, scope="full")

    assert set(calibration) == {"training"}
    assert calibration_counts == {"training": 1, "evaluation": 0, "unique": 1}
    assert set(full) == {"training", "evaluation"}
    assert full_counts == {"training": 1, "evaluation": 1, "unique": 2}


def test_full_scope_rejects_panel_list_manifest_disagreement(tmp_path: Path) -> None:
    unit, panel, _ = _inputs(tmp_path)
    panel.with_name("panel.txt").write_text("different\n")

    with pytest.raises(ValueError, match="panel list/hash-map identity"):
        load_requirements(unit, panel, scope="full")


def test_audit_fails_on_missing_or_changed_motion(tmp_path: Path) -> None:
    unit, panel, payloads = _inputs(tmp_path)
    requirements, _, _ = load_requirements(unit, panel, scope="full")
    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / "training.npz").write_bytes(b"changed")

    result = audit_source(bank, requirements)

    assert result["pass"] is False
    assert result["missing"] == ["evaluation"]
    assert result["mismatched"][0]["clip"] == "training"
    assert payloads["training"] != b"changed"


def test_link_is_created_only_for_verified_source(tmp_path: Path) -> None:
    unit, panel, payloads = _inputs(tmp_path)
    requirements, _, _ = load_requirements(unit, panel, scope="full")
    bank = tmp_path / "licensed"
    bank.mkdir()
    for name, payload in payloads.items():
        (bank / f"{name}.npz").write_bytes(payload)
    assert audit_source(bank, requirements)["pass"] is True

    destination = tmp_path / "repo" / "bank" / "amass"
    assert link_bank(bank, destination) == "created_symlink"
    assert destination.resolve() == bank.resolve()
    assert link_bank(bank, destination) == "existing_verified_symlink"

    different = tmp_path / "different"
    different.mkdir()
    with pytest.raises(FileExistsError, match="points elsewhere"):
        link_bank(different, destination)


def test_preflight_full_scope_cannot_pass_with_training_only(tmp_path: Path) -> None:
    unit, panel, payloads = _inputs(tmp_path)
    requirements, counts, _ = load_requirements(unit, panel, scope="full")
    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / "training.npz").write_bytes(payloads["training"])

    result = check_motion_bank(
        requirements,
        counts,
        bank,
        scope="full",
        verify_hashes=True,
    )

    assert result.status == "blocker"
    assert "missing 1/2 full-scope motions" in result.detail
