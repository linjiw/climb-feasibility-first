#!/usr/bin/env python3
"""Replay the sealed paired evaluator with exact Phase-G provenance validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import eval_paired_v2 as evaluator
from check_relative_progress_probe import sha256

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ROOT / 'reports/g_segment/eval_conditions.json'
PANEL = ROOT / 'reports/g_segment/panel/panel.txt'
CONDITIONS_SHA256 = '74b723d42c4050eea9f4ea7ff87d22771e8e32c5155b56829900bf4cb3744a4e'
CLASSIFICATION = 'outcome-blind Phase-G evaluation conditions; built before any Phase-G arm exists'
PROTOCOL = 'sealed_phase_g_extra_provenance/1'


def load_sealed_conditions(path: Path, *args, **kwargs) -> dict:
    """Require the unchanged sealed file and exact regenerated condition payload."""
    if path.resolve() != CONDITIONS or sha256(path) != CONDITIONS_SHA256:
        raise ValueError('adapter requires the unchanged sealed Phase-G conditions')
    saved = json.loads(path.read_text())
    expected = evaluator.build_conditions(*args, **kwargs)
    expected.update(panel_txt_sha256=sha256(PANEL), classification=CLASSIFICATION)
    if saved != expected:
        raise ValueError('sealed condition payload or provenance differs from requested setup')
    return saved


def adapter_record() -> dict:
    return {'path': str(Path(__file__).resolve()), 'sha256': sha256(Path(__file__)), 'protocol': PROTOCOL}


def main() -> int:
    # Reuse the sealed CLI and rollout implementation. Restore even on a failed
    # preflight; neither the source file nor condition artifact is rewritten.
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--synthetic", action="store_true")
    args, _ = parser.parse_known_args()
    original = evaluator.load_or_create_manifest
    evaluator.load_or_create_manifest = load_sealed_conditions
    try:
        result = evaluator.main()
    finally:
        evaluator.load_or_create_manifest = original
    if result == 0 and not args.synthetic:
        output = args.out.resolve()
        path = output.with_suffix(output.suffix + '.meta.json')
        metadata = json.loads(path.read_text())
        if 'execution_adapter' in metadata:
            raise ValueError('evaluation metadata already contains an adapter record')
        metadata['execution_adapter'] = adapter_record()
        path.write_text(json.dumps(metadata, indent=1) + '\n')
    return result


if __name__ == '__main__':
    raise SystemExit(main())
