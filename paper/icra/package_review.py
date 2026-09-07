"""Package the current paper with anonymous, reproducible paired-seed statistics."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def paired_files(summary: dict, panels: tuple[str, str]) -> tuple[str, dict]:
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(['seed', 'feasible_hard_difference', 'all_panel_difference'])
    primary, broad = (summary[k] for k in panels)
    seeds = list(primary['paired_seed_deltas'])
    if seeds != list(broad['paired_seed_deltas']):
        raise ValueError('paired panel seed order differs')
    for seed in seeds:
        writer.writerow([seed, primary['paired_seed_deltas'][seed], broad['paired_seed_deltas'][seed]])
    expected = {'status': summary['status'], 'independent_unit': 'paired trained seed',
                'feasible_hard_difference': {k: primary[k] for k in ('mean', 'seed_t_95ci', 'independent_units', 'df')},
                'all_panel_difference': {k: broad[k] for k in ('mean', 'seed_t_95ci', 'independent_units', 'df')}}
    return stream.getvalue(), expected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--h1-report', type=Path)
    args = parser.parse_args()
    pdf = ROOT / 'paper/icra/ICRA_DRAFT.pdf'
    source = (ROOT / 'paper/icra/root.tex').read_text()
    build = ROOT / 'paper/icra/build'
    if (pdf.read_bytes() != (build / 'root.pdf').read_bytes()
            or source != (build / 'root.tex').read_text()
            or (ROOT / 'paper/icra/references.bib').read_bytes() != (build / 'references.bib').read_bytes()):
        raise ValueError('paper PDF, source and bibliography must match the latest successful build')
    text = subprocess.check_output(['pdftotext', str(pdf), '-'], text=True)
    if any(term in text for term in ('linjiw', 'github.io', '/home/')) or 'Anonymous Authors' not in text:
        raise ValueError('paper literal anonymity screen failed')
    if ('\\label{sec:h1result}' in source) != bool(args.h1_report):
        raise ValueError('paper and companion H1 inclusion disagree')
    original = json.loads((ROOT / 'reports/relative_confirmation_results_2026-09-06/summary.json').read_text())
    csv_text, expected = paired_files(original, ('primary_R_minus_U', 'all_panel_nonregression'))
    files = {'paper.pdf': pdf.read_bytes(), 'allocation_paired.csv': csv_text.encode(),
             'allocation_expected.json': (json.dumps(expected, indent=2)+'\n').encode(),
             'allocation_learning_curves.csv': (ROOT / 'reports/relative_confirmation_results_2026-09-06/learning_curves.csv').read_bytes()}
    if args.h1_report:
        from report_h1 import digest, terminal_input
        verification = json.loads((args.h1_report / 'verification.json').read_text())
        campaign = Path(verification['terminal']['path']).parent
        terminal, frozen = terminal_input(campaign)
        h1 = json.loads((args.h1_report / 'summary.json').read_text())
        if verification['status'] != 'exact_H1_replay_pass' or h1['primary_on_minus_off'] != frozen['primary_on_minus_off'] or h1['all_panel_on_minus_off'] != frozen['all_panel_on_minus_off']:
            raise ValueError('H1 statistics differ from verified result')
        if digest(Path(verification['analysis']['path'])) != verification['analysis']['sha256']:
            raise ValueError('H1 analysis changed')
        csv_text, expected = paired_files(h1, ('primary_on_minus_off', 'all_panel_on_minus_off'))
        files.update({'h1_paired.csv': csv_text.encode(), 'h1_expected.json': (json.dumps(expected, indent=2)+'\n').encode(),
                      'h1_learning_curves.csv': (args.h1_report / 'learning_curves.csv').read_bytes()})
        # Source unit metadata contain clip IDs and intervals, not local machine paths.
        files['h1_allocation_attribution.json'] = (json.dumps({'scope': h1['mechanism_scope'], 'seeds': h1['mechanism']}, indent=2)+'\n').encode()
    script = '''"""Recompute paired-seed means/t intervals; does not rerun policies or bootstrap."""
from pathlib import Path
import csv
import json
import numpy as np
from scipy.stats import t
root = Path(__file__).resolve().parent
for path in sorted(root.glob('*_paired.csv')):
    rows = list(csv.DictReader(path.open()))
    expected = json.loads(path.with_name(path.name.replace('_paired.csv', '_expected.json')).read_text())
    n = len(rows)
    for column in ('feasible_hard_difference', 'all_panel_difference'):
        values = np.array([float(row[column]) for row in rows])
        mean = values.mean()
        half = t.ppf(.975, n-1) * values.std(ddof=1) / np.sqrt(n)
        result = expected[column]
        assert result['independent_units'] == n and result['df'] == n-1
        assert np.allclose([mean, mean-half, mean+half], [result['mean'], *result['seed_t_95ci']], atol=1e-12, rtol=0)
        print(path.name, column, 'mean', mean, 't95', [mean-half, mean+half], 'n', n)
    print('Stored registered disposition:', expected['status'])
print('Paired-seed statistics reproduced. This check does not authenticate training or redefine a decision rule.')
'''
    files['verify_statistics.py'] = script.encode()
    files['README.md'] = '''# Anonymous manuscript and statistical companion

Draft for author/reviewer inspection; not a submission receipt.

`paper.pdf` contains the essential evidence. The CSV files contain paired trained-seed
differences and descriptive learning curves. Run `python verify_statistics.py` with
NumPy and SciPy to reproduce the seed-level means and two-sided 95% Student-t intervals.
The verification tolerance is 1e-12 for this numerical companion only; the underlying
campaign replay compares its complete serialized result exactly.

The allocation contrast is R minus U, with three seed pairs. Its original hard
point target is +0.02 with a positive lower interval bound and a separate all-panel
lower-bound margin of −0.01. H1, when included, is admission on minus off under D,
with five fresh seed pairs; its primary disposition follows the sign of the hard
interval. H1's +0.02 line and all-panel interval are descriptive. Neither analysis
can replace independent policies with clip or trial counts.

Learning curves and allocation attribution are separate from the primary decision.
Positive excess attribution is not the fraction of all samples or a causal waste
estimate. An inconclusive interval establishes neither equivalence nor absence of harm.
The H1 panel is reused from the allocation study.

This companion reproduces statistics from aggregate differences. It does not rerun
training, verify simulator physics, or reproduce the supplementary clip bootstrap.
Licensed motion payloads and model checkpoints are not included. Full reconstruction
requires the declared references, pinned runtime, split/support manifests and source
contracts. No identifying local machine paths are included in this archive.
'''.encode()
    for name, contents in files.items():
        if name.endswith(('.json', '.csv', '.md', '.py')) and any(term in contents for term in (b'/home/', b'linjiw', b'github.io')):
            raise ValueError(f'identifying machine path in {name}')
    checksums = ''.join(f'{hashlib.sha256(value).hexdigest()}  {name}\n' for name, value in sorted(files.items()))
    files['SHA256SUMS'] = checksums.encode()
    with zipfile.ZipFile(args.out, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, value)
    print(json.dumps({'archive': str(args.out), 'sha256': hashlib.sha256(args.out.read_bytes()).hexdigest(),
                      'files': len(files), 'h1_included': bool(args.h1_report), 'paper_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
