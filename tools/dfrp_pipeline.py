#!/usr/bin/env python3
"""Build a deterministic DFRP v0 bank-routing manifest."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from climb.dfrp import DfrpConfig, build_dfrp_manifest, validate_dfrp_manifest


def materialize_training_view(
    manifest: dict,
    *,
    overlay_dir: Path,
    sidecar_overlay_dir: Path,
    repair_record_overlay_dir: Path | None = None,
    clips_out: Path,
    root: Path,
    force: bool,
) -> None:
    """Create relocatable symlink views for training-ready motions/sidecars."""
    selected = [row for row in manifest["clips"] if row["training_eligible"]]
    if not selected:
        raise ValueError("DFRP manifest has no training-ready clips")
    directories = [overlay_dir, sidecar_overlay_dir]
    if repair_record_overlay_dir is not None:
        directories.append(repair_record_overlay_dir)
    for directory in directories:
        if directory.exists():
            entries = list(directory.iterdir())
            if entries and not force:
                raise FileExistsError(
                    f"{directory} is not empty; pass --force to rebuild symlinks"
                )
            for entry in entries:
                if not entry.is_symlink():
                    raise ValueError(f"refusing to replace non-symlink {entry}")
                entry.unlink()
        directory.mkdir(parents=True, exist_ok=True)
    clips_out.parent.mkdir(parents=True, exist_ok=True)
    clips_out.write_text("".join(f"{row['name']}\n" for row in selected))
    for row in selected:
        motion = (root / row["training_motion"]["path"]).resolve()
        sidecar = (root / row["training_sidecar"]["path"]).resolve()
        motion_link = overlay_dir / f"{row['name']}.npz"
        sidecar_link = sidecar_overlay_dir / f"{row['name']}.json"
        motion_link.symlink_to(os.path.relpath(motion, overlay_dir))
        sidecar_link.symlink_to(os.path.relpath(sidecar, sidecar_overlay_dir))
        if repair_record_overlay_dir is not None and row.get("repair"):
            record = (root / row["repair"]["record_path"]).resolve()
            record_link = repair_record_overlay_dir / f"{row['name']}.json"
            record_link.symlink_to(
                os.path.relpath(record, repair_record_overlay_dir)
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clips", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--screen-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument(
        "--screen-tool",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "refeas/refeas/screen.py",
    )
    parser.add_argument(
        "--repair-tool",
        type=Path,
        default=Path(__file__).resolve().parent / "dfrp_repair.py",
    )
    parser.add_argument("--repair-records-dir", type=Path)
    parser.add_argument("--repaired-bank", type=Path)
    parser.add_argument("--raw-sidecar-dir", type=Path)
    parser.add_argument("--repaired-sidecar-dir", type=Path)
    parser.add_argument("--contact-gap-m", type=float, default=0.06)
    parser.add_argument("--flag-infeasible-frac", type=float, default=0.10)
    parser.add_argument("--recovered-infeasible-frac", type=float, default=0.05)
    parser.add_argument("--primary-root-offset-m", type=float, default=0.08)
    parser.add_argument("--exploratory-root-offset-m", type=float, default=0.15)
    parser.add_argument("--horizon-steps", type=int, default=50)
    parser.add_argument("--ik-contact-residual-m", type=float, default=0.01)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--overlay-dir", type=Path)
    parser.add_argument("--sidecar-overlay-dir", type=Path)
    parser.add_argument("--repair-record-overlay-dir", type=Path)
    parser.add_argument("--training-clips-out", type=Path)
    parser.add_argument(
        "--force-overlay",
        action="store_true",
        help="replace existing symlinks in the requested training views",
    )
    parser.add_argument(
        "--require-training-ready",
        action="store_true",
        help="fail if any primary/raw/segment route lacks exact training support",
    )
    parser.add_argument(
        "--check-only", action="store_true", help="validate inputs without writing"
    )
    args = parser.parse_args()

    config = DfrpConfig(
        contact_gap_m=args.contact_gap_m,
        flag_infeasible_frac=args.flag_infeasible_frac,
        recovered_infeasible_frac=args.recovered_infeasible_frac,
        primary_root_offset_m=args.primary_root_offset_m,
        exploratory_root_offset_m=args.exploratory_root_offset_m,
        horizon_steps=args.horizon_steps,
        ik_contact_residual_m=args.ik_contact_residual_m,
    )
    manifest = build_dfrp_manifest(
        clips_path=args.clips.resolve(),
        bank=args.bank.resolve(),
        screen_dir=args.screen_dir.resolve(),
        model_path=args.model.resolve(),
        repair_records_dir=(
            args.repair_records_dir.resolve() if args.repair_records_dir else None
        ),
        repaired_bank=(args.repaired_bank.resolve() if args.repaired_bank else None),
        raw_sidecar_dir=(
            args.raw_sidecar_dir.resolve() if args.raw_sidecar_dir else None
        ),
        repaired_sidecar_dir=(
            args.repaired_sidecar_dir.resolve()
            if args.repaired_sidecar_dir
            else None
        ),
        screen_tool_path=args.screen_tool.resolve(),
        repair_tool_path=args.repair_tool.resolve(),
        config=config,
    )
    validate_dfrp_manifest(manifest)
    if args.require_training_ready:
        incomplete = [
            row["name"]
            for row in manifest["clips"]
            if row["route"] in ("raw_feasible", "repair_primary", "segment_only")
            and not row["training_eligible"]
        ]
        if incomplete:
            raise SystemExit(
                f"{len(incomplete)} routed clips lack exact training support, "
                f"e.g. {incomplete[:3]}"
            )
    print(json.dumps(manifest["counts"], indent=1, sort_keys=True))
    print(f"payload sha256 {manifest['payload_sha256']}")
    if not args.check_only:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(manifest, indent=1) + "\n")
        args.out.with_suffix(args.out.suffix + ".sha256").write_text(
            f"{manifest['payload_sha256']}  {args.out.name}:payload\n"
        )
        print(f"wrote {args.out}")
        view_args = (
            args.overlay_dir,
            args.sidecar_overlay_dir,
            args.training_clips_out,
        )
        if any(value is not None for value in view_args):
            if any(value is None for value in view_args):
                raise SystemExit(
                    "--overlay-dir, --sidecar-overlay-dir, and "
                    "--training-clips-out must be supplied together"
                )
            materialize_training_view(
                manifest,
                overlay_dir=args.overlay_dir.resolve(),
                sidecar_overlay_dir=args.sidecar_overlay_dir.resolve(),
                repair_record_overlay_dir=(
                    args.repair_record_overlay_dir.resolve()
                    if args.repair_record_overlay_dir
                    else None
                ),
                clips_out=args.training_clips_out.resolve(),
                root=Path.cwd(),
                force=args.force_overlay,
            )
            print(
                f"materialized {manifest['counts']['training_eligible']} "
                "training-ready clips"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
