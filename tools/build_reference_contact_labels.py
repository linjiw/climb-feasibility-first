#!/usr/bin/env python3
"""Build provenance-bound kinematic foot-contact proxy labels.

The output is an *unvalidated proxy*, not force-plate contact truth. Promotion
to a paper metric is governed separately by ``plan/G_CONTACT_TIMING_VALIDATION.md``.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from climb.contact_timing import contact_mask_from_signals, event_frames

SCHEMA_VERSION = "reference_contact_proxy/1"
DEFAULT_MODEL = Path(
    "mjlab-1.6.0/src/mjlab/asset_zoo/robots/unitree_g1/xmls/g1.xml"
)
FOOT_GEOM_PREFIXES = ("left_foot", "right_foot")
ANKLE_BODY_NAMES = ("left_ankle_roll_link", "right_ankle_roll_link")
THRESHOLDS = {
    "enter_clearance_m": 0.010,
    "exit_clearance_m": 0.020,
    "enter_speed_mps": 0.250,
    "exit_speed_mps": 0.500,
    "minimum_run_frames": 3,
}


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _npz_bytes(arrays: dict[str, np.ndarray]) -> bytes:
    """Serialize arrays as a byte-stable compressed NPZ archive."""
    output = io.BytesIO()
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name in sorted(arrays):
            payload = io.BytesIO()
            np.lib.format.write_array(
                payload,
                np.asarray(arrays[name]),
                allow_pickle=False,
            )
            info = zipfile.ZipInfo(f"{name}.npy", (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, payload.getvalue(), compresslevel=9)
    return output.getvalue()


def _write_immutable(path: Path, payload: bytes) -> None:
    """Write a new artifact, accepting an identical existing artifact only."""
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(f"refusing to replace differing artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _read_clips(path: Path) -> list[str]:
    clips = [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not clips or len(clips) != len(set(clips)):
        raise ValueError("clip list must be nonempty and unique")
    for clip in clips:
        if Path(clip).name != clip:
            raise ValueError(f"clip name may not contain a path component: {clip}")
    return clips


def _load_model(model_path: Path) -> tuple[mujoco.MjModel, int]:
    spec = mujoco.MjSpec.from_file(str(model_path.resolve()))
    spec.worldbody.add_geom(
        name="contact_label_plane",
        type=mujoco.mjtGeom.mjGEOM_PLANE,
        size=[0.0, 0.0, 0.05],
    )
    model = spec.compile()
    plane_id = mujoco.mj_name2id(
        model,
        mujoco.mjtObj.mjOBJ_GEOM,
        "contact_label_plane",
    )
    if plane_id < 0:
        raise RuntimeError("failed to add contact-label plane")
    return model, plane_id


def _named_ids(
    model: mujoco.MjModel,
) -> tuple[tuple[list[int], list[int]], tuple[int, int]]:
    foot_geoms: list[list[int]] = [[], []]
    for geom_id in range(model.ngeom):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id) or ""
        short_name = name.split("/")[-1]
        for foot_index, prefix in enumerate(FOOT_GEOM_PREFIXES):
            if short_name.startswith(prefix) and short_name.endswith("_collision"):
                foot_geoms[foot_index].append(geom_id)
    if any(not ids for ids in foot_geoms):
        raise ValueError("model lacks named left/right foot collision geoms")

    ankle_bodies = tuple(
        mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        for name in ANKLE_BODY_NAMES
    )
    if any(body_id < 0 for body_id in ankle_bodies):
        raise ValueError("model lacks named left/right ankle-roll bodies")
    return (foot_geoms[0], foot_geoms[1]), ankle_bodies


def _motion_signals(
    motion_path: Path,
    model: mujoco.MjModel,
    plane_id: int,
    foot_geoms: tuple[list[int], list[int]],
    ankle_bodies: tuple[int, int],
) -> dict[str, np.ndarray]:
    with np.load(motion_path, allow_pickle=False) as motion:
        fps = float(np.asarray(motion["fps"]).reshape(-1)[0])
        joint_pos = np.asarray(motion["joint_pos"], dtype=np.float64)
        body_pos = np.asarray(motion["body_pos_w"], dtype=np.float64)
        body_quat = np.asarray(motion["body_quat_w"], dtype=np.float64)
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError(f"invalid fps in {motion_path}")
    frames = joint_pos.shape[0]
    if (
        joint_pos.ndim != 2
        or joint_pos.shape[1] != model.nq - 7
        or body_pos.shape[:2] != (frames, model.nbody - 1)
        or body_quat.shape[:2] != (frames, model.nbody - 1)
        or body_pos.shape[2:] != (3,)
        or body_quat.shape[2:] != (4,)
    ):
        raise ValueError(f"motion/model shape mismatch: {motion_path}")

    data = mujoco.MjData(model)
    clearance = np.empty((frames, 2), dtype=np.float64)
    ankle_position = np.empty((frames, 2, 3), dtype=np.float64)
    nearest = np.empty(6, dtype=np.float64)
    for frame in range(frames):
        data.qpos[:3] = body_pos[frame, 0]
        data.qpos[3:7] = body_quat[frame, 0]
        data.qpos[7:] = joint_pos[frame]
        mujoco.mj_forward(model, data)
        for foot_index, geom_ids in enumerate(foot_geoms):
            clearance[frame, foot_index] = min(
                mujoco.mj_geomDistance(
                    model,
                    data,
                    geom_id,
                    plane_id,
                    10.0,
                    nearest,
                )
                for geom_id in geom_ids
            )
            ankle_position[frame, foot_index] = data.xpos[ankle_bodies[foot_index]]

    edge_order = 2 if frames >= 3 else 1
    ankle_velocity = np.gradient(
        ankle_position,
        1.0 / fps,
        axis=0,
        edge_order=edge_order,
    )
    speed = np.linalg.norm(ankle_velocity, axis=2)
    contact = np.column_stack(
        [
            contact_mask_from_signals(
                clearance[:, foot_index],
                speed[:, foot_index],
                **THRESHOLDS,
            )
            for foot_index in range(2)
        ]
    )
    return {
        "fps": np.asarray(fps, dtype=np.float64),
        "clearance_m": clearance.astype(np.float32),
        "ankle_speed_mps": speed.astype(np.float32),
        "contact": contact,
    }


def _event_counts(contact: np.ndarray) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for foot_index, foot in enumerate(("left", "right")):
        events = event_frames(contact[:, foot_index])
        result[foot] = {name: int(frames.size) for name, frames in events.items()}
    return result


def build_labels(
    clips_path: Path,
    panel_manifest_path: Path,
    bank: Path,
    model_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Build label artifacts and their complete provenance manifest."""
    clips = _read_clips(clips_path)
    panel_manifest = json.loads(panel_manifest_path.read_text())
    if panel_manifest.get("schema_version") != "g_segment_eval_panel/1":
        raise ValueError("unsupported panel manifest")
    if panel_manifest.get("panel_txt_sha256") != sha256_file(clips_path):
        raise ValueError("panel text hash does not match panel manifest")
    source_hashes = panel_manifest.get("motion_sha256")
    if not isinstance(source_hashes, dict) or set(source_hashes) != set(clips):
        raise ValueError("panel motion hashes do not exactly cover clip list")

    model, plane_id = _load_model(model_path)
    foot_geoms, ankle_bodies = _named_ids(model)
    records: dict[str, Any] = {}
    for clip in clips:
        motion_path = bank / f"{clip}.npz"
        if not motion_path.is_file():
            raise FileNotFoundError(f"missing licensed motion: {motion_path}")
        motion_hash = sha256_file(motion_path)
        if motion_hash != source_hashes[clip]:
            raise ValueError(f"source motion hash mismatch: {clip}")
        arrays = _motion_signals(
            motion_path,
            model,
            plane_id,
            foot_geoms,
            ankle_bodies,
        )
        label_path = output_dir / f"{clip}.reference_contact_proxy.npz"
        _write_immutable(label_path, _npz_bytes(arrays))
        contact = arrays["contact"]
        records[clip] = {
            "source_motion_sha256": motion_hash,
            "artifact": {
                "path": str(label_path),
                "sha256": sha256_file(label_path),
            },
            "frames": int(contact.shape[0]),
            "fps": float(arrays["fps"]),
            "event_counts": _event_counts(contact),
        }

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "classification": (
            "exploratory, unvalidated kinematic contact proxy; not physical "
            "contact ground truth"
        ),
        "contact_construct": (
            "minimum signed foot-collision-geometry clearance to z=0 plane plus "
            "ankle-roll-origin speed, with hysteresis and short-run merging"
        ),
        "thresholds": THRESHOLDS,
        "inputs": {
            "clips": {"path": str(clips_path), "sha256": sha256_file(clips_path)},
            "panel_manifest": {
                "path": str(panel_manifest_path),
                "sha256": sha256_file(panel_manifest_path),
            },
            "bank": str(bank),
            "model": {"path": str(model_path), "sha256": sha256_file(model_path)},
        },
        "builder_sha256": sha256_file(Path(__file__).resolve()),
        "clips": records,
    }
    manifest_path = output_dir / "manifest.json"
    encoded = (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode()
    _write_immutable(manifest_path, encoded)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clips",
        type=Path,
        default=Path("reports/g_segment/panel/panel.txt"),
    )
    parser.add_argument(
        "--panel-manifest",
        type=Path,
        default=Path("reports/g_segment/panel/panel_manifest.json"),
    )
    parser.add_argument("--bank", type=Path, default=Path("bank/amass"))
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("reports/g_segment/reference_contact_proxy"),
    )
    args = parser.parse_args()
    manifest = build_labels(
        args.clips,
        args.panel_manifest,
        args.bank,
        args.model,
        args.out_dir,
    )
    total_events = sum(
        count
        for record in manifest["clips"].values()
        for events in record["event_counts"].values()
        for count in events.values()
    )
    print(
        json.dumps(
            {
                "classification": manifest["classification"],
                "clips": len(manifest["clips"]),
                "proxy_events": total_events,
                "manifest": str(args.out_dir / "manifest.json"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
