"""Export verified allocation records; never open held-out policy outcomes."""
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from run_relative_confirmation import training_record
from analyze_relative_campaign import verify_training
from relative_confirmation_setup import runtime_inventory

BASE = ROOT / 'reports/relative_progress_2026-09-05/confirmation_freeze'
CAMPAIGN = BASE / 'campaign_gpu_reentry_2026-09-06'
OUT = ROOT / 'docs/assets/progress-2026-09-06'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

contract = json.loads((BASE / 'contract.json').read_text())
contract_hash = digest(BASE / 'contract.json')
assert contract_hash == '8f2192a9b937060a9ba6aa4fbd1b4a6aed8a7da183abf1c64fa9db557a5af013'
assert runtime_inventory() == json.loads((BASE.parent / 'confirmation_preparation_adapter/runtime_inventory.json').read_text())
jobs = json.loads((CAMPAIGN / 'schedule.json').read_text())['jobs']
runs, states, pending = [], [], []
for job in jobs:
    if job['stage'] != 'train':
        continue
    arm, seed = job['arm'], job['seed']
    gate = CAMPAIGN / f'{arm}_s{seed}_training_gate.json'
    if not gate.exists():
        checkpoints = list(Path(job['run_dir']).glob('model_*.pt'))
        pending.append({'arm': arm, 'seed': seed, 'latest_saved_iteration': max((int(p.stem.split('_')[1]) for p in checkpoints), default=None)})
        continue
    checked = verify_training(training_record(job), contract, contract_hash, arm=arm, seed=seed)
    checked.pop('checkpoint_links')
    assert checked == json.loads(gate.read_text())
    runs.append({'arm': arm, 'seed': seed, 'mean_tv': checked['mean_tv'], 'snapshots': len(checked['snapshots']),
                 'completed_trials': checked['snapshots'][-1]['completed_trials'],
                 'source': str(gate.relative_to(ROOT)), 'source_sha256': digest(gate),
                 'finished': checked['execution_cost']['finished']})
    states.extend(dict(arm=arm, seed=seed, **s) for s in checked['snapshots'])
    print(arm, seed, 'verified', flush=True)
now = datetime.now(ZoneInfo('America/New_York')).isoformat()
data = {'schema_version': 'climb_public_progress/1', 'snapshot_time': now,
        'classification': 'measured simulation training integrity and allocation; policy utility pending',
        'campaign_contract_sha256': contract_hash, 'training_jobs_complete': len(runs), 'training_jobs_total': 12,
        'verified_checkpoint_states': len(states), 'evaluation_cells_total': 48,
        'endpoint_access_exists': (CAMPAIGN / 'endpoint_access.json').exists(),
        'policy_outcomes_read_by_exporter': False, 'completed_runs': runs, 'pending_training': pending,
        'unit_of_replication': 'training seed; checkpoint states and evaluation conditions are correlated',
        'mean_tv_window': '37 saved states at iterations 400 through 3999 inclusive',
        'limitations': ['TV measures changed exposure, not policy utility.', 'Incomplete arms are not imputed.',
                       'This dated export is not a live monitor.', 'No hardware or Sim2Real outcome is established.']}
(OUT / 'research_snapshot.json').write_text(json.dumps(data, indent=2)+'\n')
with (OUT / 'allocation_snapshots.csv').open('w', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(states[0]), lineterminator="\n"); writer.writeheader(); writer.writerows(states)
(ROOT / 'reports/pages_update_2026-09-06/export_verification.json').write_text(json.dumps({'snapshot_sha256':digest(OUT/'research_snapshot.json'), 'csv_sha256':digest(OUT/'allocation_snapshots.csv'), 'training_jobs_replayed':len(runs), 'checkpoint_states_replayed':len(states), 'runtime_files_unchanged':376, 'exporter_sha256':digest(Path(__file__))},indent=2)+'\n')
print(json.dumps({k:v for k,v in data.items() if k not in ('completed_runs','limitations')}))
