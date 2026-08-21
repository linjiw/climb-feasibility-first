"""Focused CPU tests for feasibility-grounded adaptive sampling."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from climb.eligibility import (
    clip_sampling_probabilities,
    eligibility_set_hash,
    load_bank_eligibility,
    sample_eligible_local_frames,
    sampling_ineligible_mass,
    validate_fgas_config,
)


def _write_sidecar(
    directory: Path,
    clip: str,
    eligible: list[float],
    score: list[float] | None = None,
    bin_frames: int = 10,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": "eligibility_sidecar/1",
        "policy": "screened",
        "clip": clip,
        "fps": 50.0,
        "frames": len(eligible) * bin_frames,
        "bin_frames": bin_frames,
        "bin_eligible": eligible,
    }
    if score is not None:
        record["bin_score"] = score
    (directory / f"{clip}.json").write_text(json.dumps(record))


def _load(
    directory: Path,
    mode: str,
    names: tuple[str, ...] = ("a",),
    lengths: tuple[int, ...] = (100,),
):
    clip_len = torch.tensor(lengths)
    clip_start = torch.tensor([0, *torch.cumsum(clip_len, 0).tolist()[:-1]])
    state = load_bank_eligibility(
        str(directory),
        names,
        clip_start,
        clip_len,
        fps=50.0,
        mode=mode,  # type: ignore[arg-type]
        hard_threshold=0.5,
        device="cpu",
    )
    return state, clip_start, clip_len


def test_additive_mode_matches_the_historical_formula_exactly() -> None:
    failures = torch.tensor([17.0, 0.0, 3.0, 0.0])
    expected = failures + 0.1 / failures.numel()
    expected = expected / expected.sum()
    actual = clip_sampling_probabilities(failures, 0.1, "additive")
    assert torch.equal(actual, expected)


def test_mixture_holds_the_uniform_floor() -> None:
    failures = torch.tensor([100.0, 0.0, 0.0, 0.0])
    probabilities = clip_sampling_probabilities(failures, 0.1, "mixture")
    torch.testing.assert_close(
        probabilities, torch.tensor([0.925, 0.025, 0.025, 0.025])
    )


def test_mask_removes_a_clip_from_both_mixture_terms() -> None:
    failures = torch.tensor([100.0, 1.0, 1.0])
    eligibility = torch.tensor([0.0, 1.0, 1.0])
    probabilities = clip_sampling_probabilities(failures, 0.1, "mixture", eligibility)
    assert probabilities[0] == 0.0
    assert probabilities.sum() == pytest.approx(1.0)


def test_default_local_draw_is_bit_identical() -> None:
    clip_start = torch.tensor([0, 10])
    clip_len = torch.tensor([10, 30])
    clips = torch.tensor([0, 1, 1, 0, 1])
    torch.manual_seed(9)
    expected = (torch.rand(len(clips)) * clip_len[clips].float()).long()
    torch.manual_seed(9)
    actual = sample_eligible_local_frames(None, clip_start, clip_len, clips)
    assert torch.equal(actual, expected)


def test_hard_mask_excludes_rejected_clips_and_frames(tmp_path: Path) -> None:
    _write_sidecar(tmp_path, "a", [0.0] * 10)
    _write_sidecar(tmp_path, "b", [0.0, 0.0] + [1.0] * 8)
    state, starts, lengths = _load(
        tmp_path, "hard", names=("a", "b"), lengths=(100, 100)
    )
    probabilities = clip_sampling_probabilities(
        torch.tensor([100.0, 1.0]), 0.1, "mixture", state.clip_applied
    )
    torch.testing.assert_close(state.clip_applied, torch.tensor([0.0, 0.8]))
    assert torch.equal(probabilities, torch.tensor([0.0, 1.0]))
    clips = torch.ones(4000, dtype=torch.long)
    local = sample_eligible_local_frames(state, starts, lengths, clips)
    assert int(local.min()) >= 20
    assert sampling_ineligible_mass(probabilities, state, starts, lengths) == 0.0


def test_soft_mask_reports_partial_rejected_mass(tmp_path: Path) -> None:
    _write_sidecar(
        tmp_path,
        "a",
        [1.0, 0.0],
        score=[1.0, 0.25],
        bin_frames=50,
    )
    state, starts, lengths = _load(tmp_path, "soft")
    probabilities = torch.ones(1)
    contamination = sampling_ineligible_mass(probabilities, state, starts, lengths)
    assert contamination == pytest.approx(0.2)

    clips = torch.zeros(40000, dtype=torch.long)
    local = sample_eligible_local_frames(state, starts, lengths, clips)
    first = int((local < 50).sum())
    second = int((local >= 50).sum())
    assert first / second == pytest.approx(4.0, rel=0.1)


def test_invalid_fgas_launches_fail_before_training() -> None:
    with pytest.raises(ValueError, match="requires eligibility_path"):
        validate_fgas_config(None, "soft", "grounded")
    with pytest.raises(ValueError, match="requires sampling_mode='grounded'"):
        validate_fgas_config("sidecars", "soft", "adaptive")
    validate_fgas_config("sidecars", "soft", "grounded")


def test_real_mixed100_sidecar_contract() -> None:
    root = Path("reports/eligibility/tier_mixed100_guard0_bin50")
    clip = "BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos"
    record = json.loads((root / f"{clip}.json").read_text())
    assert record["bin_eligible"] == [0, 0, 1, 1, 1, 1, 1, 1, 0, 1]
    assert record["bin_score"] == [0.0, 0.38, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.6, 1.0]
    assert eligibility_set_hash(str(root)) == (
        "bd742558d72bad2e37a65953cb7ec028e23092df7d9699b33549848aa72519e3"
    )
