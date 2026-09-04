#!/usr/bin/env python3
"""Render reference-only dual-view videos for blinded contact annotation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MUJOCO_GL", "egl")

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw

DEFAULT_MODEL = Path(
    "mjlab-1.6.0/src/mjlab/asset_zoo/robots/unitree_g1/xmls/g1.xml"
)
CAMERAS = (
    {"caption": "front-oblique", "azimuth": 135.0, "elevation": -15.0},
    {"caption": "sagittal", "azimuth": 90.0, "elevation": -10.0},
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_model(model_path: Path) -> mujoco.MjModel:
    spec = mujoco.MjSpec.from_file(str(model_path.resolve()))
    spec.worldbody.add_geom(
        name="contact_annotation_plane",
        type=mujoco.mjtGeom.mjGEOM_PLANE,
        size=[0.0, 0.0, 0.05],
        rgba=[0.35, 0.35, 0.35, 1.0],
    )
    return spec.compile()


def _read_panel(path: Path, split: str) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected_fields = ["clip", "stratum", "split", "stratum_selection_rank"]
    if not rows or list(rows[0]) != expected_fields:
        raise ValueError(f"{path}: unexpected contact-validation panel schema")
    selected = rows if split == "all" else [row for row in rows if row["split"] == split]
    if len(selected) != (20 if split == "all" else 10):
        raise ValueError(f"{path}: unexpected {split} split size")
    return selected


def _load_motion(path: Path, model: mujoco.MjModel) -> dict[str, np.ndarray | float]:
    with np.load(path, allow_pickle=False) as archive:
        fps = float(np.asarray(archive["fps"]).reshape(-1)[0])
        joint_pos = np.asarray(archive["joint_pos"], dtype=np.float64)
        body_pos = np.asarray(archive["body_pos_w"], dtype=np.float64)
        body_quat = np.asarray(archive["body_quat_w"], dtype=np.float64)
    if (
        not np.isclose(fps, 50.0)
        or joint_pos.ndim != 2
        or joint_pos.shape[1] != model.nq - 7
        or body_pos.shape[0] != joint_pos.shape[0]
        or body_quat.shape[0] != joint_pos.shape[0]
    ):
        raise ValueError(f"{path}: expected a model-compatible 50 Hz motion")
    return {
        "fps": fps,
        "joint_pos": joint_pos,
        "root_pos": body_pos[:, 0],
        "root_quat": body_quat[:, 0],
    }


def _camera(settings: dict[str, str | float], root_position: np.ndarray) -> Any:
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.distance = 2.8
    camera.azimuth = float(settings["azimuth"])
    camera.elevation = float(settings["elevation"])
    camera.lookat[:] = root_position + np.array([0.0, 0.0, 0.55])
    return camera


def render_motion(
    motion_path: Path,
    model: mujoco.MjModel,
    output_path: Path,
    *,
    width: int,
    height: int,
) -> tuple[int, float]:
    """Render one full motion with two synchronized, proxy-free views."""
    if output_path.exists():
        raise FileExistsError(f"refusing to replace annotation video: {output_path}")
    motion = _load_motion(motion_path, model)
    joint_pos = np.asarray(motion["joint_pos"])
    root_pos = np.asarray(motion["root_pos"])
    root_quat = np.asarray(motion["root_quat"])
    fps = float(motion["fps"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=height, width=width)
    writer = imageio.get_writer(
        output_path,
        fps=fps,
        codec="libx264",
        quality=8,
        macro_block_size=2,
        pixelformat="yuv420p",
        ffmpeg_params=["-metadata", "creation_time="],
    )
    try:
        for frame in range(joint_pos.shape[0]):
            data.qpos[:3] = root_pos[frame]
            data.qpos[3:7] = root_quat[frame]
            data.qpos[7:] = joint_pos[frame]
            mujoco.mj_forward(model, data)
            views = []
            for settings in CAMERAS:
                renderer.update_scene(data, camera=_camera(settings, root_pos[frame]))
                views.append(renderer.render().copy())
            canvas = Image.new("RGB", (2 * width, height + 40), color=(20, 20, 20))
            for view_index, view in enumerate(views):
                canvas.paste(Image.fromarray(view), (view_index * width, 40))
            draw = ImageDraw.Draw(canvas)
            draw.text(
                (8, 5),
                f"frame {frame:05d} | LEFT/RIGHT denote robot feet | reference only",
                fill="white",
            )
            for view_index, settings in enumerate(CAMERAS):
                draw.text(
                    (view_index * width + width - 110, 5),
                    str(settings["caption"]),
                    fill="white",
                )
            writer.append_data(np.asarray(canvas))
    finally:
        writer.close()
        renderer.close()
    return int(joint_pos.shape[0]), fps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--panel",
        type=Path,
        default=Path("reports/g_segment/contact_validation/panel.csv"),
    )
    parser.add_argument(
        "--panel-manifest",
        type=Path,
        default=Path("reports/g_segment/contact_validation/panel.manifest.json"),
    )
    parser.add_argument("--bank", type=Path, default=Path("bank/amass"))
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument(
        "--split", choices=("development", "validation", "all"), default="all"
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("reports/g_segment/contact_validation/renders"),
    )
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    args = parser.parse_args()
    if args.width <= 0 or args.height <= 0:
        raise ValueError("render dimensions must be positive")

    panel_manifest = json.loads(args.panel_manifest.read_text())
    if (
        panel_manifest.get("schema_version") != "contact_validation_panel/1"
        or panel_manifest.get("output", {}).get("sha256") != sha256_file(args.panel)
    ):
        raise ValueError("panel does not match contact-validation manifest")
    rows = _read_panel(args.panel, args.split)
    source_hashes = panel_manifest.get("motion_sha256", {})
    model = _load_model(args.model)
    outputs: dict[str, Any] = {}
    for row in rows:
        clip = row["clip"]
        motion_path = args.bank / f"{clip}.npz"
        if not motion_path.is_file() or sha256_file(motion_path) != source_hashes.get(clip):
            raise ValueError(f"missing or hash-mismatched source motion: {clip}")
        output_path = args.out_dir / args.split / f"{clip}.mp4"
        frames, fps = render_motion(
            motion_path,
            model,
            output_path,
            width=args.width,
            height=args.height,
        )
        outputs[clip] = {
            "source_motion_sha256": source_hashes[clip],
            "artifact": {"path": str(output_path), "sha256": sha256_file(output_path)},
            "frames": frames,
            "fps": fps,
        }

    manifest = {
        "schema_version": "contact_annotation_renders/1",
        "classification": (
            "reference-only manual-annotation views; no proxy, policy, stratum, "
            "or endpoint overlay"
        ),
        "split": args.split,
        "inputs": {
            "panel": {"path": str(args.panel), "sha256": sha256_file(args.panel)},
            "panel_manifest": {
                "path": str(args.panel_manifest),
                "sha256": sha256_file(args.panel_manifest),
            },
            "bank": str(args.bank),
            "model": {"path": str(args.model), "sha256": sha256_file(args.model)},
        },
        "rendering": {
            "per_view_width": args.width,
            "per_view_height": args.height,
            "header_height": 40,
            "cameras": CAMERAS,
        },
        "outputs": outputs,
        "renderer_sha256": sha256_file(Path(__file__).resolve()),
    }
    manifest_path = args.out_dir / f"{args.split}.manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"refusing to replace render manifest: {manifest_path}")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"split": args.split, "videos": len(outputs)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
