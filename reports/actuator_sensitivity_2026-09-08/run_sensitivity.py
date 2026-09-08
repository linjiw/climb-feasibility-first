#!/usr/bin/env python
"""Re-screen the local Phase-G bank at three knee/hip-roll effort limits.

Design declared before the tightened conditions ran:
plan/ACTUATOR_SENSITIVITY_2026-09-08.md

Only the four knee/hip-roll `forcerange` attributes differ between the three models.
Everything else -- screen source, bank, contact band, friction, clip extent -- is held fixed.
"""
from __future__ import annotations

import concurrent.futures as cf
import glob
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path('/home/linjiw/climb-feasibility-first')
OUT = ROOT / 'reports/actuator_sensitivity_2026-09-08'
SCREEN = ROOT / 'refeas/refeas/screen.py'
PY = ROOT / 'mjlab-1.6.0/.venv/bin/python'
BANK = ROOT / 'bank/amass'
GAP, MU = 0.06, 0.6
LEVELS = (139, 120, 90)
WORKERS = 24


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def one(args):
    clip, level = args
    out = OUT / 'raw' / f'{level}' / f'{clip}.json'
    if out.exists():
        try:
            return level, json.loads(out.read_text())
        except Exception:
            out.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(PY), str(SCREEN), '--clip', clip, '--bank', str(BANK),
           '--model', str(OUT / 'models' / f'g1_flat_{level}.xml'),
           '--gap', str(GAP), '--mu', str(MU), '--t0', '0', '--t1', '1e9',
           '--brief', '--out', str(out)]
    env = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', CUDA_VISIBLE_DEVICES='')
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0 or not out.exists():
        return level, {'clip': clip, 'error': (r.stderr or '')[-400:]}
    return level, json.loads(out.read_text())


def main() -> None:
    clips = sorted(os.path.basename(p)[:-4] for p in glob.glob(str(BANK / '*.npz')))
    print(f'{len(clips)} clips x {len(LEVELS)} levels = {len(clips)*len(LEVELS)} screens', flush=True)
    jobs = [(c, l) for l in LEVELS for c in clips]
    results = {l: {} for l in LEVELS}
    errors = []
    done = 0
    with cf.ProcessPoolExecutor(max_workers=WORKERS) as ex:
        for level, row in ex.map(one, jobs, chunksize=4):
            done += 1
            if 'error' in row:
                errors.append(row)
            else:
                results[level][row['clip']] = row
            if done % 300 == 0:
                print(f'  {done}/{len(jobs)}', flush=True)
    manifest = {
        'design': 'plan/ACTUATOR_SENSITIVITY_2026-09-08.md',
        'classification': 'measured CPU screen sensitivity; no policy, no training, no endpoint',
        'clips': len(clips), 'levels': list(LEVELS), 'gap_m': GAP, 'mu': MU,
        'screen_sha256': sha(SCREEN),
        'model_sha256': {str(l): sha(OUT / 'models' / f'g1_flat_{l}.xml') for l in LEVELS},
        'bank': str(BANK.resolve()),
        'errors': errors,
        'completed': {str(l): len(results[l]) for l in LEVELS},
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    with (OUT / 'sensitivity.json').open('w') as fh:
        json.dump({str(l): results[l] for l in LEVELS}, fh)
    print('manifest:', json.dumps(manifest['completed']), 'errors:', len(errors), flush=True)


if __name__ == '__main__':
    main()
