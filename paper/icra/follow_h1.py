"""Wait for H1's terminal record, then run one CPU manuscript replay/export."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: dict) -> None:
    with path.open('x') as handle:
        handle.write(json.dumps(value, indent=2)+'\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    if digest(args.design) != args.sha256:
        raise ValueError('reporting handoff design changed')
    design = json.loads(args.design.read_text())
    for path, sha in design['sources'].items():
        if digest(Path(path)) != sha:
            raise ValueError('reporting source changed')
    out = Path(design['work'])
    write(out / 'started.json', {'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat(),
                                'design_sha256': args.sha256})
    campaign = Path(design['campaign'])
    terminal = campaign / 'terminal_status.json'
    while not terminal.exists():
        if (out / 'STOP').exists():
            raise RuntimeError('reporting STOP requested')
        if datetime.now(timezone.utc) > datetime.fromisoformat(design['cutoff']):
            write(out / 'terminal.json', {'status': 'reporting_cutoff_without_completed_H1'})
            return
        time.sleep(30)
    result = json.loads(terminal.read_text())
    if result['status'] != 'completed':
        write(out / 'terminal.json', {'status': 'no_H1_manuscript_result', 'campaign_terminal': result})
        return
    for path, sha in design['sources'].items():
        if digest(Path(path)) != sha:
            raise ValueError('reporting source changed while waiting')
    with (out / 'report.log').open('x') as log:
        child = subprocess.run(design['argv'], stdout=log, stderr=subprocess.STDOUT,
                               cwd=design['root'], env=dict(os.environ, CUDA_VISIBLE_DEVICES='',
                               OMP_NUM_THREADS='1', MKL_NUM_THREADS='1'))
    write(out / 'terminal.json', {'status': 'report_ready' if child.returncode == 0 else 'report_failed',
                                 'exit_code': child.returncode, 'finished_at': datetime.now(timezone.utc).isoformat(),
                                 'campaign_terminal_sha256': digest(terminal), 'output': design['output'],
                                 'scope': 'CPU replay/report only; manuscript integration and review remain separate'})


if __name__ == '__main__':
    main()
