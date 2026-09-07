"""Build a manuscript candidate after complete H1 replay, without altering its protocol."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: dict) -> None:
    with path.open('x') as handle:
        handle.write(json.dumps(value, indent=2, allow_nan=False)+'\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    if sha(args.design) != args.sha256:
        raise ValueError('manuscript handoff design changed')
    design = json.loads(args.design.read_text())
    root, work, report = (Path(design[k]) for k in ('root', 'work', 'report'))
    python = design['python']
    save(work / 'started.json', {'started_at': datetime.now(timezone.utc).isoformat(), 'design_sha256': args.sha256})
    original = {}
    try:
        signal = Path(design['report_terminal'])
        while True:
            if (work / 'STOP').exists():
                raise RuntimeError('manuscript handoff STOP requested')
            if datetime.now(timezone.utc) > datetime.fromisoformat(design['cutoff']):
                raise RuntimeError('manuscript handoff cutoff reached')
            if signal.exists():
                try:
                    status = json.loads(signal.read_text())
                    break
                except json.JSONDecodeError:
                    pass
            time.sleep(30)
        if status['status'] != 'report_ready':
            save(work / 'terminal.json', {'status': 'no_complete_H1_candidate', 'report_status': status})
            return
        for path, digest in {**design['sources'], **design['base_files']}.items():
            if sha(Path(path)) != digest:
                raise RuntimeError(f'file changed while waiting; preserve current edits: {path}')
        summary = json.loads((report / 'summary.json').read_text())
        for name in ('root.tex', 'build.sh', 'DRAFT.md', 'ICRA_DRAFT.pdf'):
            file = root / 'paper/icra' / name
            original[file] = file.read_bytes()
        with (work / 'integration.log').open('x') as log:
            subprocess.run([python, str(root / 'paper/icra/integrate_h1.py'), '--report', str(report)],
                           cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
        with (work / 'build.log').open('x') as log:
            built = subprocess.run([str(root / 'paper/icra/build.sh')], cwd=root, stdout=log, stderr=subprocess.STDOUT)
        if built.returncode:
            (work / 'candidate_root.tex').write_bytes((root / 'paper/icra/root.tex').read_bytes())
            generated = root / 'paper/icra/build/root.pdf'
            if generated.exists():
                (work / 'candidate_unpassed.pdf').write_bytes(generated.read_bytes())
            raise RuntimeError('H1 candidate failed the eight-page/font/layout build; original manuscript restored')
        pdf = root / 'paper/icra/ICRA_DRAFT.pdf'
        with (work / 'package.log').open('x') as log:
            subprocess.run([python, str(root / 'paper/icra/package_review.py'), '--out', str(work / 'H1_REVIEW_BUNDLE.zip'),
                            '--h1-report', str(report)], cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['pdftoppm', '-scale-to', '1400', '-png', str(pdf), str(work / 'page')],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        primary, broad = summary['primary_on_minus_off'], summary['all_panel_on_minus_off']
        proof = json.loads((report / 'verification.json').read_text())
        entry = (f"\n## H1 complete — automatic manuscript handoff, {datetime.now(timezone.utc).isoformat()}\n\n"
                 f"**Measured registered disposition: {summary['status']}.** Ten full training runs, forty evaluation cells, "
                 "five paired seeds. The complete frozen analysis reproduces exactly. "
                 f"Primary on-minus-off mean {primary['mean']:+.10f}, two-sided seed-t 95% CI {primary['seed_t_95ci']}; "
                 f"paired differences {primary['paired_seed_deltas']}. All-panel mean {broad['mean']:+.10f}, "
                 f"interval {broad['seed_t_95ci']}; no H1 all-panel pass/fail guard. "
                 f"Source analysis SHA-256 `{proof['analysis']['sha256']}`.\n\n"
                 f"Paper candidate built with H1 and passed mechanical gates. PDF SHA-256 `{sha(pdf)}`. "
                 "Visual review, claim review and author review remain pending; this is not a submission. "
                 f"Figures, complete mechanism data and replay: `{report.relative_to(root)}`. "
                 f"Build, page images and statistical companion: `{work.relative_to(root)}`. "
                 "The earlier allocation study remains inconclusive; its contract and numbers are unchanged.\n\n")
        for name in ('paper/RESULTS_LOG.md', 'plan/STATUS.md'):
            path = root / name
            first, rest = path.read_text().split('\n', 1)
            path.write_text(first+'\n'+entry+rest)
        save(work / 'terminal.json', {'status': 'H1_manuscript_candidate_ready', 'H1_disposition': summary['status'],
                                     'paper_sha256': sha(pdf), 'analysis_sha256': proof['analysis']['sha256'],
                                     'visual_review_completed': False, 'author_review_completed': False,
                                     'submitted': False, 'finished_at': datetime.now(timezone.utc).isoformat()})
    except Exception as exc:
        if original:
            for path, data in original.items():
                path.write_bytes(data)
            with (work / 'restore_build.log').open('w') as log:
                subprocess.run([str(root / 'paper/icra/build.sh')], cwd=root, stdout=log, stderr=subprocess.STDOUT)
        save(work / 'terminal.json', {'status': 'H1_manuscript_handoff_needs_review', 'reason': str(exc),
                                     'original_manuscript_restored': bool(original), 'submitted': False})
        raise


if __name__ == '__main__':
    main()
