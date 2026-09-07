"""Wait for the unchanged GPU gate, then run each corrected development cell once."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
WORK = Path('/home/linjiw/climb-icra-evidence-2026-09-06')
OUT = WORK / 'reports/device_lifecycle_optional_sense_reentry_2026-09-06'
PRIOR = WORK / 'reports/device_lifecycle_optional_sense_2026-09-06'
PYTHON = ROOT / 'mjlab-1.6.0/.venv/bin/python'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    prior_terminal = json.loads((PRIOR / 'terminal_status.json').read_text())
    if prior_terminal['completed_cells'] or list(PRIOR.glob('*_launch.json')):
        raise ValueError('resource-stopped predecessor unexpectedly launched a cell')
    OUT.mkdir(exist_ok=False)
    design_path = OUT / 'design.json'
    design_path.write_bytes((PRIOR / 'design.json').read_bytes())
    design = json.loads(design_path.read_text())
    wrapper = WORK / 'tools/device_optional_sense.py'
    for path, digest in design['bindings'].items():
        if sha(Path(path)) != digest:
            raise ValueError(f'bound input changed: {path}')
    record = {'launcher_sha256': sha(Path(__file__)),
              'design_sha256': sha(design_path),
              'prior_stop_sha256': sha(PRIOR / 'terminal_status.json'),
              'graph_verifier_sha256': sha(wrapper),
              'minimum_free_mib': 14000, 'maximum_utilization': 60,
              'maximum_wait_per_cell_seconds': 7200, 'poll_seconds': 45,
              'automatic_cell_retries': 0, 'full_evaluation_enabled': False}
    (OUT / 'execution_binding.json').write_text(json.dumps(record, indent=2) + '\n')
    completed = []
    try:
        for condition in design['conditions']:
            deadline = time.monotonic() + 7200
            while True:
                free, util = map(int, subprocess.check_output(
                    ['nvidia-smi', '--query-gpu=memory.free,utilization.gpu',
                     '--format=csv,noheader,nounits'], text=True).strip().split(','))
                status = {'status': 'waiting_for_gpu', 'next_cell': condition,
                          'completed_cells': completed, 'free_mib': free,
                          'utilization': util,
                          'checked_at': datetime.now().astimezone().isoformat()}
                (OUT / 'queue_status.json').write_text(json.dumps(status, indent=2) + '\n')
                if free >= 14000 and util <= 60:
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError('unchanged GPU gate unavailable for two hours')
                time.sleep(45)
            command = [str(PYTHON), str(wrapper), '--design', str(design_path),
                       '--design-sha256', sha(design_path), '--condition', condition,
                       '--out-dir', str(OUT / condition)]
            status.update(status='running', argv=command)
            (OUT / f'{condition}_launch.json').write_text(json.dumps(status, indent=2) + '\n')
            (OUT / 'queue_status.json').write_text(json.dumps(status, indent=2) + '\n')
            with (OUT / f'{condition}.log').open('x') as log:
                subprocess.run(command, cwd=WORK, stdout=log,
                               stderr=subprocess.STDOUT, check=True)
            completed.append(condition)
            print(condition, 'completed', flush=True)
        sys.path.insert(0, str(WORK / 'tools'))
        import analyze_device_lifecycle as analyzer
        from device_optional_sense import verify_graphs
        analyzer.verify_graphs = verify_graphs
        result = analyzer.analyze(OUT)
        result['graph_verifier_sha256'] = sha(wrapper)
        result['execution_binding_sha256'] = sha(OUT / 'execution_binding.json')
        (OUT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
        terminal = {'status': result['status'], 'completed_cells': completed}
    except Exception as exc:
        terminal = {'status': 'execution_stopped', 'reason': str(exc),
                    'completed_cells': completed, 'automatic_cell_retries': 0}
    terminal['full_evaluation_enabled'] = False
    (OUT / 'terminal_status.json').write_text(json.dumps(terminal, indent=2) + '\n')
    (OUT / 'queue_status.json').write_text(json.dumps(terminal, indent=2) + '\n')
    print(json.dumps(terminal), flush=True)


if __name__ == '__main__':
    main()
