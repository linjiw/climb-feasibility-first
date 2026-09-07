"""Single-attempt, fail-closed H1 scheduler with prospective calendar/resource gates."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import protocol as p


def now() -> datetime:
    return datetime.now(timezone.utc)


def write_status(path: Path, value: dict) -> None:
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(dict(value, updated_at=now().isoformat()), indent=2) + '\n')
    tmp.replace(path)


def deadline(contract: dict, stage: str, first_training: bool) -> None:
    spec = contract['specification']
    cutoff = spec['training_cutoff'] if stage in ('smoke', 'train') else spec['evidence_cutoff']
    if now() > datetime.fromisoformat(cutoff):
        raise RuntimeError(f'{stage} calendar cutoff reached; no partial H1 paper result')
    if not first_training and now() > datetime.fromisoformat(spec['launch_cutoff']):
        raise RuntimeError('first full training launch cutoff reached')


def free_gpu(contract: dict, stage: str, first_training: bool, root: Path) -> None:
    start = time.monotonic()
    while True:
        deadline(contract, stage, first_training)
        if (root / 'STOP').exists():
            raise RuntimeError('STOP sentinel requested')
        output = subprocess.check_output(['nvidia-smi', '--id=0', '--query-gpu=memory.free,utilization.gpu',
                                          '--format=csv,noheader,nounits'], text=True)
        memory, utilization = map(int, output.strip().split(','))
        gate = contract['specification']['resource_gate']
        write_status(root / 'status.json', {'status': 'waiting_for_gpu', 'free_mib': memory,
                                          'utilization_percent': utilization, 'next_stage': stage})
        if memory >= gate['free_mib'] and utilization <= gate['max_utilization_percent']:
            return
        if time.monotonic() - start >= gate['wait_seconds']:
            raise RuntimeError('GPU resource wait exceeded frozen two-hour limit')
        time.sleep(30)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    contract = p.verify_contract(args.contract, args.sha256, smoke=True)
    root = Path(contract['campaign'])
    root.mkdir(exist_ok=True)
    lock = (root / 'campaign.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    # A restart is a new attempt and must not silently resume this sealed campaign.
    p.dump(root / 'started.json', {'pid': os.getpid(), 'started_at': now().isoformat(), 'contract': p.record(args.contract)})
    first_training = False
    child = None
    current = None
    try:
        jobs = [*contract['schedule'], {'id': 'aggregate', 'stage': 'aggregate'}]
        for job in jobs:
            current = job['id']
            deadline(contract, job['stage'], first_training)
            if job['stage'] != 'aggregate':
                free_gpu(contract, job['stage'], first_training, root)
            if (root / 'STOP').exists():
                raise RuntimeError('STOP sentinel requested')
            argv = [str(p.PYTHON), str(p.ROOT / 'paper/h1/job.py'), '--contract', str(args.contract),
                    '--sha256', args.sha256, '--job-id', current]
            start = now().isoformat()
            p.dump(root / f'{current}.started.json', {'job': job, 'argv': argv, 'started_at': start})
            with (root / f'{current}.log').open('x') as log:
                child = subprocess.Popen(argv, cwd=p.ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                if job['stage'] == 'train':
                    first_training = True
                write_status(root / 'status.json', {'status': 'running', 'job': job, 'pid': child.pid})
                while child.poll() is None:
                    deadline(contract, job['stage'], first_training)
                    if (root / 'STOP').exists():
                        raise RuntimeError('STOP sentinel requested')
                    time.sleep(10)
                code = child.returncode
                child = None
            result_path = root / ('analysis.json' if current == 'aggregate' else f'{current}/result.json')
            if code or not result_path.exists():
                raise RuntimeError(f'{current} failed with exit code {code}; no automatic retry')
            p.dump(root / f'{current}.completed.json', {'job': job, 'started_at': start, 'completed_at': now().isoformat(),
                                                       'exit_code': code, 'result': p.record(result_path)})
        p.dump(root / 'terminal_status.json', {'status': 'completed', 'completed_at': now().isoformat(),
                                              'analysis': p.record(root / 'analysis.json'), 'contract': p.record(args.contract)})
        write_status(root / 'status.json', {'status': 'completed'})
    except BaseException as exc:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        p.dump(root / 'terminal_status.json', {'status': 'stopped_without_complete_H1', 'job': current,
                                              'reason': str(exc), 'completed_at': now().isoformat(),
                                              'contract': p.record(args.contract)})
        write_status(root / 'status.json', {'status': 'stopped_without_complete_H1', 'reason': str(exc)})
        raise


if __name__ == '__main__':
    main()
