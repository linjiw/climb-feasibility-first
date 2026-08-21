"""Feasibility sidecars and masked sampling for multi-clip motion banks.

The feasibility screen and the sampler use different axes.  Sidecars describe
fixed-width frame bins, while CLIMB first chooses a clip and then a start frame
inside it.  This module expands sidecars back to frames, derives clip weights,
and keeps both choices on the same eligibility signal.
"""

from __future__ import annotations

import json
import math
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import torch

EligibilityMode = Literal["off", "hard", "soft"]
SamplerMode = Literal["additive", "mixture"]

_SIDECAR_SCHEMA = "eligibility_sidecar/1"


@dataclass(frozen=True)
class EligibilityState:
    """Eligibility projected onto a bank's frame and clip axes."""

    frame_screen: torch.Tensor
    frame_applied: torch.Tensor | None
    clip_screen: torch.Tensor
    clip_applied: torch.Tensor | None
    clips_without_sidecar_frac: float
    applied_cumulative: torch.Tensor | None


def validate_fgas_config(
    eligibility_path: str | None,
    eligibility_mode: str,
    sampling_mode: str,
) -> None:
    """Reject launch combinations that would masquerade as an FGAS arm."""
    if eligibility_mode not in ("off", "hard", "soft"):
        raise ValueError(f"unknown eligibility_mode={eligibility_mode!r}")
    if eligibility_mode != "off" and eligibility_path is None:
        raise ValueError(
            f"eligibility_mode={eligibility_mode!r} requires eligibility_path"
        )
    if eligibility_mode != "off" and sampling_mode != "grounded":
        raise ValueError(
            "eligibility masking requires sampling_mode='grounded'; otherwise the "
            "mask and the uniform-floor repair change in the same arm"
        )


def clip_sampling_probabilities(
    failure_ema: torch.Tensor,
    uniform_ratio: float,
    mode: SamplerMode,
    eligibility: torch.Tensor | None = None,
) -> torch.Tensor:
    """Return additive, mixture, or eligibility-masked clip probabilities."""
    count = failure_ema.numel()
    if count == 0:
        raise ValueError("cannot sample an empty clip bank")
    if not 0.0 <= uniform_ratio <= 1.0:
        raise ValueError(f"uniform_ratio must be in [0, 1], got {uniform_ratio}")

    uniform = torch.full_like(failure_ema, 1.0 / count)
    if eligibility is not None:
        if eligibility.shape != failure_ema.shape:
            raise ValueError(
                f"eligibility shape {tuple(eligibility.shape)} does not match "
                f"failure shape {tuple(failure_ema.shape)}"
            )
        if mode != "mixture":
            raise ValueError("eligibility masking is defined only for mixture mode")
        weight = eligibility.to(failure_ema).clamp_min(0.0)
        if float(weight.sum()) > 0.0:
            base = weight / weight.sum()
            focus_mass = failure_ema.clamp_min(0.0) * weight
            focus = (
                focus_mass / focus_mass.sum() if float(focus_mass.sum()) > 0.0 else base
            )
            return (1.0 - uniform_ratio) * focus + uniform_ratio * base

    if mode == "mixture":
        mass = failure_ema.clamp_min(0.0)
        focus = mass / mass.sum() if float(mass.sum()) > 0.0 else uniform
        return (1.0 - uniform_ratio) * focus + uniform_ratio * uniform
    if mode == "additive":
        probabilities = failure_ema + uniform_ratio / count
        return probabilities / probabilities.sum()
    raise ValueError(f"unknown sampler mode={mode!r}")


def _read_records(
    path: str, clip_names: Sequence[str]
) -> tuple[dict[str, dict], list[str]]:
    root = Path(path)
    if root.is_dir():
        records = {}
        for name in clip_names:
            candidate = root / f"{name}.json"
            if candidate.is_file():
                records[name] = json.loads(candidate.read_text())
        return records, [name for name in clip_names if name not in records]
    if not root.is_file():
        raise FileNotFoundError(f"eligibility_path {path!r} is not readable")

    blob = json.loads(root.read_text())
    if isinstance(blob, dict) and "clips" in blob and "bin_eligible" not in blob:
        blob = blob["clips"]
    if isinstance(blob, list):
        bundle = {str(record["clip"]): record for record in blob}
    elif isinstance(blob, dict) and "bin_eligible" in blob:
        if len(clip_names) != 1:
            raise ValueError(
                f"{path} contains one record but the bank has {len(clip_names)} clips"
            )
        bundle = {clip_names[0]: blob}
    elif isinstance(blob, dict):
        bundle = {str(name): record for name, record in blob.items()}
    else:
        raise ValueError(f"{path}: unrecognized eligibility sidecar structure")
    records = {name: bundle[name] for name in clip_names if name in bundle}
    return records, [name for name in clip_names if name not in records]


def _record_frames(
    record: dict,
    clip: str,
    frames: int,
    field: Literal["bin_eligible", "bin_score"],
) -> torch.Tensor:
    schema = record.get("schema_version")
    if schema is not None and str(schema) != _SIDECAR_SCHEMA:
        raise ValueError(
            f"{clip}: sidecar declares schema {schema!r}, expected {_SIDECAR_SCHEMA!r}"
        )
    if field not in record:
        raise ValueError(f"{clip}: eligibility sidecar has no {field!r} field")
    if int(record.get("frames", -1)) != frames:
        raise ValueError(
            f"{clip}: sidecar covers {record.get('frames')} frames but motion has {frames}"
        )
    bin_frames = int(record.get("bin_frames", 0))
    if bin_frames <= 0:
        raise ValueError(f"{clip}: invalid bin_frames={record.get('bin_frames')!r}")
    values = torch.tensor(record[field], dtype=torch.float32)
    expected = math.ceil(frames / bin_frames)
    if values.numel() != expected:
        raise ValueError(
            f"{clip}: {values.numel()} {field} entries, but frame grid implies {expected}"
        )
    if not bool(torch.isfinite(values).all()):
        raise ValueError(f"{clip}: {field} contains non-finite values")
    if float(values.min()) < -1e-6 or float(values.max()) > 1.0 + 1e-6:
        raise ValueError(f"{clip}: {field} must stay in [0, 1]")
    return values.clamp(0.0, 1.0).repeat_interleave(bin_frames)[:frames]


def _check_score_orientation(record: dict, clip: str) -> None:
    """Catch severity scores accidentally supplied as eligibility weights."""
    if "bin_score" not in record or "bin_eligible" not in record:
        return
    hard = torch.tensor(record["bin_eligible"], dtype=torch.float32)
    soft = torch.tensor(record["bin_score"], dtype=torch.float32)
    if hard.shape != soft.shape:
        raise ValueError(f"{clip}: bin_score and bin_eligible shapes disagree")
    keep = hard > 0.5
    if (
        bool(keep.any())
        and not bool(keep.all())
        and float(soft[keep].mean()) < float(soft[~keep].mean())
    ):
        raise ValueError(f"{clip}: bin_score appears to be severity, not eligibility")


def load_bank_eligibility(
    path: str,
    clip_names: Sequence[str],
    clip_start: torch.Tensor,
    clip_len: torch.Tensor,
    fps: float,
    mode: EligibilityMode,
    hard_threshold: float,
    device: str | torch.device,
) -> EligibilityState:
    """Load sidecars and project them onto the bank's exact frame timeline."""
    if not 0.0 <= hard_threshold <= 1.0:
        raise ValueError("eligibility_hard_threshold must be in [0, 1]")
    if len(clip_names) != clip_start.numel() or len(clip_names) != clip_len.numel():
        raise ValueError("clip name, start, and length tables disagree")

    records, missing = _read_records(path, clip_names)
    total = int((clip_start + clip_len).max())
    frame_screen = torch.ones(total, dtype=torch.float32)
    frame_soft = torch.ones(total, dtype=torch.float32) if mode == "soft" else None
    assumed = []

    for index, clip in enumerate(clip_names):
        record = records.get(clip)
        if record is None:
            continue
        if str(record.get("policy", "screened")) != "screened":
            assumed.append(clip)
        recorded_fps = float(record.get("fps", fps))
        if recorded_fps > 0.0 and abs(recorded_fps - fps) / recorded_fps > 1e-3:
            print(
                f"[climb] WARNING: {clip} screened at {recorded_fps:g} Hz but "
                f"played at {fps:g} Hz",
                file=sys.stderr,
            )
        start = int(clip_start[index])
        frames = int(clip_len[index])
        frame_screen[start : start + frames] = _record_frames(
            record, clip, frames, "bin_eligible"
        )
        if frame_soft is not None:
            _check_score_orientation(record, clip)
            frame_soft[start : start + frames] = _record_frames(
                record, clip, frames, "bin_score"
            )

    unscreened = sorted(set(missing) | set(assumed))
    clip_hard_fraction = torch.stack(
        [
            frame_screen[int(start) : int(start + length)].double().mean()
            for start, length in zip(clip_start, clip_len, strict=True)
        ]
    ).float()
    clip_screen = (clip_hard_fraction >= hard_threshold).float()

    if mode == "hard":
        frame_applied = frame_screen
        # Keep partially feasible clips.  Thresholding the mean here would turn
        # segment curation back into clip pruning; the mean is the exact amount
        # of the clip's uniform-within proposal that survives the hard mask.
        clip_applied = clip_hard_fraction
    elif mode == "soft":
        assert frame_soft is not None
        frame_applied = frame_soft
        clip_applied = torch.stack(
            [
                frame_soft[int(start) : int(start + length)].double().mean()
                for start, length in zip(clip_start, clip_len, strict=True)
            ]
        ).float()
    else:
        frame_applied = None
        clip_applied = None

    frame_screen = frame_screen.to(device)
    clip_screen = clip_screen.to(device)
    frame_applied = None if frame_applied is None else frame_applied.to(device)
    clip_applied = None if clip_applied is None else clip_applied.to(device)
    cumulative = None
    if frame_applied is not None:
        cumulative = torch.cat(
            [
                torch.zeros(1, dtype=torch.float64, device=device),
                frame_applied.double().cumsum(0),
            ]
        )

    print(
        f"[climb] eligibility: {len(clip_names) - len(unscreened)}/"
        f"{len(clip_names)} clips screened; mode={mode}; "
        f"hard-frame fraction={float(frame_screen.mean()):.3f}"
    )
    if unscreened:
        preview = ", ".join(unscreened[:5])
        suffix = " ..." if len(unscreened) > 5 else ""
        print(f"[climb] eligibility unscreened: {preview}{suffix}", file=sys.stderr)

    return EligibilityState(
        frame_screen=frame_screen,
        frame_applied=frame_applied,
        clip_screen=clip_screen,
        clip_applied=clip_applied,
        clips_without_sidecar_frac=len(unscreened) / max(len(clip_names), 1),
        applied_cumulative=cumulative,
    )


def sample_eligible_local_frames(
    state: EligibilityState | None,
    clip_start: torch.Tensor,
    clip_len: torch.Tensor,
    clips: torch.Tensor,
) -> torch.Tensor:
    """Draw local frames uniformly, or proportionally to the applied mask."""
    lengths = clip_len[clips]
    uniform_draw = torch.rand(len(clips), device=clips.device)
    uniform_local = (uniform_draw * lengths.float()).long()
    if state is None or state.frame_applied is None:
        return uniform_local

    starts = clip_start[clips]
    assert state.applied_cumulative is not None
    cumulative = state.applied_cumulative
    low = cumulative[starts]
    mass = cumulative[starts + lengths] - low
    target = low + uniform_draw.double() * mass
    index = torch.searchsorted(cumulative[1:].contiguous(), target, right=True)
    weighted_local = index - starts
    local = torch.where(mass > 0.0, weighted_local, uniform_local)
    return torch.minimum(local.clamp_min(0), lengths - 1)


def sampling_ineligible_mass(
    probabilities: torch.Tensor,
    state: EligibilityState,
    clip_start: torch.Tensor,
    clip_len: torch.Tensor,
) -> float:
    """Exact hard-rejected mass under the joint clip/start distribution."""
    conditional = []
    for start, length in zip(clip_start, clip_len, strict=True):
        lo, hi = int(start), int(start + length)
        rejected = 1.0 - state.frame_screen[lo:hi]
        if state.frame_applied is None:
            conditional.append(rejected.double().mean())
            continue
        weights = state.frame_applied[lo:hi].double()
        conditional.append(
            (weights * rejected).sum() / weights.sum()
            if float(weights.sum()) > 0.0
            else rejected.double().mean()
        )
    conditional_tensor = torch.stack(conditional).to(probabilities)
    return float((probabilities * conditional_tensor).sum())


def eligible_entropy(probabilities: torch.Tensor, screen: torch.Tensor) -> float:
    """Normalized entropy after restricting a distribution to eligible clips."""
    keep = screen > 0
    count = int(keep.sum())
    if count == 0:
        return 0.0
    restricted = probabilities[keep]
    if float(restricted.sum()) <= 0.0:
        return 0.0
    restricted = restricted / restricted.sum()
    entropy = float(-(restricted * (restricted + 1e-12).log()).sum())
    return entropy / math.log(count) if count > 1 else 1.0


def eligibility_set_hash(path: str) -> str:
    """Return the producer's set hash when a manifest provides one."""
    manifest = Path(path) / "manifest.json"
    if not manifest.is_file():
        return ""
    record = json.loads(manifest.read_text())
    return str(record.get("set_sha256", record.get("set_hash", "")))


def relative_eligibility_path(path: str | None) -> str | None:
    """Compact an absolute path for run metadata without changing resolution."""
    if path is None:
        return None
    try:
        return os.path.relpath(path, Path.cwd())
    except ValueError:
        return path
