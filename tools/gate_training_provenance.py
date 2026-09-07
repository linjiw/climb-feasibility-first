"""Verify every scheduled H1 checkpoint and its exact sampler state."""
from __future__ import annotations

import json
from pathlib import Path

import torch

from climb.gate_ablation import file_digest, rejection_telemetry, sampler_for
from climb.gate_study import PROTOCOL
from gate_study_setup import configuration_digest, configs, record


def scheduled_iterations(smoke: bool) -> list[int]:
    return [0, 19] if smoke else [*range(0, 4000, 100), 3999]


def verify_training(run: Path, contract: dict, digest: str, arm: str, seed: int, *, smoke: bool) -> dict:
    cfg, agent = configs(contract, arm, seed, smoke=smoke, digest=digest)
    config_hash = configuration_digest(cfg, agent)
    design = json.loads((run.parent / 'design.json').read_text())
    execution = json.loads((run.parent / 'execution.json').read_text())
    identity = {'admission': arm, 'seed': seed, 'smoke': smoke, 'configuration_sha256': config_hash,
                'contract_sha256': digest, 'num_envs': cfg.scene.num_envs}
    if any(design.get(k) != v or execution.get(k) != v for k, v in identity.items()):
        raise ValueError('run identity/configuration mismatch')
    if execution.get('status') != 'completed' or execution['device'] != design['device']:
        raise ValueError('training did not complete on its declared device')
    if execution['device'] not in (('cpu', 'cuda:0') if smoke else ('cuda:0',)):
        raise ValueError('invalid training device')
    if design['sources'] != contract['sources']:
        raise ValueError('run source binding differs from contract')
    if any(file_digest(Path(p)) != h for p, h in design['sources'].items()):
        raise ValueError('bound training source changed')
    expected = scheduled_iterations(smoke)
    paths = sorted(run.glob('model_*_gate.json'), key=lambda p: int(p.stem.split('_')[1]))
    if [int(p.stem.split('_')[1]) for p in paths] != expected:
        raise ValueError('missing or extra scheduled checkpoint ledger')
    sampler = sampler_for(Path(contract['support'][arm]['path']), seed)
    previous_attempts = torch.zeros(sampler.num_units, dtype=torch.int64)
    previous_failures = previous_attempts.clone()
    records = []
    for path, iteration in zip(paths, expected, strict=True):
        row = json.loads(path.read_text())
        if row.get('iteration') != iteration or any(row.get(k) != v for k, v in identity.items()):
            raise ValueError('checkpoint identity mismatch')
        checkpoint, state_path = run / f'model_{iteration}.pt', run / f'model_{iteration}_sampler.pt'
        if file_digest(checkpoint) != row['checkpoint_sha256'] or file_digest(state_path) != row['sampler_sha256']:
            raise ValueError('checkpoint or sampler file changed')
        saved = torch.load(checkpoint, map_location='cpu', weights_only=False)
        steps = 24 * (iteration + 1)
        if (saved['iter'] != iteration or saved['infos']['env_state']['common_step_counter'] != steps
                or row['common_step_counter'] != steps):
            raise ValueError('checkpoint training clock mismatch')
        sampler.load_state_dict(torch.load(state_path, map_location='cpu', weights_only=True))
        telemetry = row['segment']
        if sampler.clock != steps // 50 or telemetry['sampler_clock'] != sampler.clock:
            raise ValueError('sampler clock mismatch')
        for key in ('invalid_start_count', 'invalid_reference_frame_count', 'censored_resets'):
            if telemetry[key] != 0:
                raise ValueError('invalid or censored event at checkpoint')
        if (telemetry['sampler_seed'] != seed or telemetry['training_seed'] != seed
                or telemetry['unit_table_sha256'] != sampler.manifest['unit_table_sha256']
                or telemetry['horizon_steps'] != 50):
            raise ValueError('sampler identity mismatch')
        for name in ('lifetime_attempts', 'lifetime_failures', 'probabilities'):
            tensor = getattr(sampler, name)
            if not torch.equal(tensor, torch.tensor(telemetry[name], dtype=tensor.dtype)):
                raise ValueError('sampler telemetry does not replay')
        if (torch.any(sampler.lifetime_attempts < previous_attempts)
                or torch.any(sampler.lifetime_failures < previous_failures)
                or torch.any(sampler.lifetime_failures > sampler.lifetime_attempts)):
            raise ValueError('invalid cumulative event counts')
        previous_attempts, previous_failures = sampler.lifetime_attempts.clone(), sampler.lifetime_failures.clone()
        if (telemetry['completed_trials'] != int(previous_attempts.sum())
                or telemetry['failed_trials'] != int(previous_failures.sum())):
            raise ValueError('completed-event totals mismatch')
        gate = rejection_telemetry(sampler)
        gate.update(protocol=PROTOCOL, full_training_enabled=not smoke,
                    stage='entrypoint_smoke' if smoke else 'confirmation', campaign_contract_sha256=digest)
        if gate != telemetry['gate_ablation']:
            raise ValueError('rejected-support telemetry does not replay')
        base = sampler.deployment_mass.double() / sampler.deployment_mass.sum()
        if (torch.any(sampler.probabilities < .8 * base - 1e-12)
                or float(sampler.probabilities.max()) > .05 + 1e-12 or gate['max_clip_mass'] > .25 + 1e-12):
            raise ValueError('floor or probability cap violation')
        r, mass = gate['uncapped_prior_rejected_mass'], gate['post_cap_rejected_mass']
        if not .8 * r - 1e-12 <= mass <= .8 * r + .2 + 1e-12:
            raise ValueError('rejected probability mass outside declared bounds')
        if arm == 'on' and (mass or gate['rejected_completed_trials']):
            raise ValueError('admission leaked rejected support')
        records.append({'iteration': iteration, 'checkpoint': record(checkpoint),
                        'sampler': record(state_path), 'ledger': record(path)})
    if int(previous_attempts.sum()) <= 0 or (arm == 'off' and gate['rejected_completed_trials'] <= 0):
        raise ValueError('run did not exercise required support')
    return {'status': 'gate_training_pass', 'classification': 'training integrity; no held-out policy benefit',
            **identity, 'device': execution['device'], 'run_dir': str(run.resolve()),
            'contract': design['contract'], 'transitions': 24 * agent.max_iterations * cfg.scene.num_envs,
            'checkpoints': records, 'final_allocation': gate,
            'completed_trials': int(previous_attempts.sum()), 'failed_trials': int(previous_failures.sum()),
            'initial_actor': json.loads((run / 'initial_actor.json').read_text()),
            'execution': record(run.parent / 'execution.json'), 'design': record(run.parent / 'design.json')}
