from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import numpy as np
import pytest

from climb.contact_validation import score_event_maps
from tools.build_contact_validation_panel import select_rows
from tools.build_reference_contact_labels import _npz_bytes
from tools.eval_paired_v2 import load_validated_contact_proxy, score_contact_window
from tools.validate_contact_proxy import synthetic_report


def test_reference_contact_npz_serialization_is_byte_stable() -> None:
    arrays = {
        "contact": np.array([[False, True], [True, False]]),
        "fps": np.asarray(50.0),
    }

    first = _npz_bytes(arrays)
    second = _npz_bytes(dict(reversed(list(arrays.items()))))

    assert first == second
    with np.load(io.BytesIO(first), allow_pickle=False) as restored:
        np.testing.assert_array_equal(restored["contact"], arrays["contact"])
        assert float(restored["fps"]) == 50.0


def test_contact_validation_panel_is_balanced_and_deterministic(
    tmp_path: Path,
) -> None:
    path = tmp_path / "strata.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["clip", "stratum"])
        writer.writeheader()
        for stratum in ("feasible_hard_reference", "feasible_remainder"):
            for index in range(12):
                writer.writerow({"clip": f"{stratum}_{index}", "stratum": stratum})

    rows = select_rows(path, 20260903)

    assert rows == select_rows(path, 20260903)
    assert len(rows) == 20
    assert sum(row["split"] == "development" for row in rows) == 10
    assert sum(row["split"] == "validation" for row in rows) == 10
    assert sum(row["stratum"] == "feasible_hard_reference" for row in rows) == 10


def test_validation_scorer_pools_events_without_rewarding_empty_groups() -> None:
    clips = {"moving", "empty"}
    expected = {
        ("moving", "left", "touchdown"): np.asarray([5]),
        ("moving", "left", "liftoff"): np.asarray([9]),
    }
    observed = {
        ("moving", "left", "touchdown"): np.asarray([6]),
        ("moving", "left", "liftoff"): np.asarray([12]),
    }

    result = score_event_maps(expected, observed, clips=clips, tolerance_frames=2)

    assert result["tp"] == 1
    assert result["fp"] == 1
    assert result["fn"] == 1
    assert result["micro_f1"] == 0.5
    assert np.isnan(result["subgroups"]["right_touchdown"]["f1"])


def test_contact_validation_synthetic_exercises_all_statuses() -> None:
    report = synthetic_report()

    assert report["branches"] == {
        "passing": "validated",
        "failed": "failed_validation",
        "insufficient": "insufficient_support",
    }


def test_evaluator_contact_window_uses_post_step_reference_alignment() -> None:
    reference = np.zeros((12, 2), dtype=bool)
    reference[4:7, 0] = True
    reference[5:8, 1] = True
    observed = reference[3:9].copy()

    result = score_contact_window(
        reference,
        observed,
        start_frame=2,
        fps=50.0,
    )

    assert result["contact_scored_frames"] == 6
    assert result["reference_contact_event_count"] == 4
    assert result["contact_event_f1"] == 1.0
    assert result["contact_event_timing_mae_s"] == 0.0


def test_evaluator_rejects_validation_status_without_passing_gates(
    tmp_path: Path,
) -> None:
    proxy = tmp_path / "proxy.json"
    proxy.write_text("{}")
    report = tmp_path / "validation.json"
    report.write_text(
        json.dumps(
            {
                "schema_version": "contact_proxy_validation/1",
                "classification": "measured held-out contact-instrument validation",
                "status": "validated",
                "tolerance_frames": 2,
                "gate_results": {"proxy_micro_f1": False},
            }
        )
    )

    with pytest.raises(ValueError, match="absent, failed, or incompatible"):
        load_validated_contact_proxy(proxy, report, ["clip"], {"clip": "hash"})
