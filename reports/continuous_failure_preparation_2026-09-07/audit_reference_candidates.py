"""Audit continuous-reference readiness without opening policy outcomes."""
from datetime import datetime
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


panel_path = ROOT / 'reports/g_segment/panel/panel.txt'
manifest_path = panel_path.with_name('panel_manifest.json')
manifest = json.loads(manifest_path.read_text())
assert sha(panel_path) == manifest['panel_txt_sha256']
names = panel_path.read_text().splitlines()
assert len(names) == len(set(names)) == 100
with panel_path.with_name('strata.csv').open() as handle:
    strata = {r['clip']: r['stratum'] for r in csv.DictReader(handle)}
assert set(strata) == set(names)
# Locate named frame-screen/sidecar artifacts throughout this report tree,
# including compressed screens. Absence is a readiness finding, not admission.
candidate_artifacts = {name: [] for name in names}
for pattern in ('*.json', '*.json.gz'):
    for path in (ROOT / 'reports').rglob(pattern):
        name = path.name.removesuffix('.gz').removesuffix('.json')
        if name in candidate_artifacts and any(
                term in str(path.parent) for term in ('screen', 'sidecar')):
            candidate_artifacts[name].append(str(path.relative_to(ROOT)))
rows = []
for name in names:
    motion = ROOT / 'bank/amass' / (name + '.npz')
    digest = sha(motion)
    assert digest == manifest['motion_sha256'][name]
    with np.load(motion) as data:
        frames = len(data['joint_pos'])
        fps = float(np.asarray(data['fps']).reshape(-1)[0])
    assert fps == 50
    rows.append({'clip': name, 'stratum': strata[name], 'frames': frames,
                 'fps': fps, 'complete_reference_duration_s': (frames - 1) / fps,
                 'reference_sha256': digest,
                 'located_frame_artifacts': len(candidate_artifacts[name]),
                 'admission_status': 'not_yet_verified'})
with (OUT / 'reference_candidates.csv').open('x', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
durations = [r['complete_reference_duration_s'] for r in rows]
result = {'checked_at': datetime.now().astimezone().isoformat(),
          'classification': 'reference-only readiness census; not an admission or tracking result',
          'panel_clips': len(rows),
          'feasible_hard_reference_labels': sum(r['stratum'] == 'feasible_hard_reference' for r in rows),
          'duration_s': {'min': min(durations), 'median': float(np.median(durations)),
                         'max': max(durations), 'sum': sum(durations)},
          'clips_longer_than_three_seconds': sum(d > 3 for d in durations),
          'clips_with_located_named_frame_artifacts': sum(bool(v) for v in candidate_artifacts.values()),
          'artifact_search_scope': 'reports/**/*.json and reports/**/*.json.gz in screen/sidecar directories',
          'full_continuous_admission_manifest_ready': False,
          'existing_screener_runtime_ready': {
              'hardcoded_bank_exists': Path('/data/robotixx/climb/bank/amass').exists(),
              'default_bridge_python_exists': (ROOT / 'bridge/.venv/bin/python').exists(),
              'legacy_compiled_model_candidates': len(list(Path('/tmp').glob('s1_*/g1_compiled.xml.mj.xml')))},
          'policy_outcomes_opened': False,
          'inputs': {str(p.relative_to(ROOT)): sha(p) for p in
                     (panel_path, manifest_path, panel_path.with_name('strata.csv'),
                      ROOT / 'tools/n1_knee_id.py', ROOT / 'tools/screen_segments.py')},
          'census_sha256': sha(OUT / 'reference_candidates.csv'),
          'auditor_sha256': sha(Path(__file__)),
          'next_step': 'Recover and authenticate frame screens, or separately bind a reproducible screen model and runtime before deriving contiguous admitted intervals. Clip-level feasibility summaries are insufficient.'}
with (OUT / 'reference_readiness.json').open('x') as handle:
    handle.write(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k not in ('inputs',)}))
