#!/usr/bin/env python3
"""Train a fixed H1 arm only under a verified prospective launch contract."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

import torch

from gate_study_setup import configuration_digest, configs, record, verify_contract
from gate_training_provenance import verify_training
from climb.gate_ablation import file_digest
from mjlab.scripts.train import TrainConfig, run_train
from mjlab.tasks.registry import register_mjlab_task
from mjlab.tasks.tracking.rl import MotionTrackingOnPolicyRunner
from relative_confirmation_setup import canonical
from train_gate_smoke import actor_digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--admission', choices=('on', 'off'), required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--device', choices=('cpu', 'cuda:0'), default='cuda:0')
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    if not args.smoke and args.device != 'cuda:0':
        raise ValueError('full H1 study requires the declared GPU device')
    contract = verify_contract(args.contract, args.contract_sha256, smoke=args.smoke)
    cfg, agent = configs(contract, args.admission, args.seed, smoke=args.smoke, digest=args.contract_sha256)
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    run = out / 'run'
    run.mkdir()
    os.environ.update(CUDA_VISIBLE_DEVICES='' if args.device == 'cpu' else '0', MUJOCO_GL='egl', WANDB_MODE='offline')
    identity = {'admission': args.admission, 'seed': args.seed, 'smoke': args.smoke,
                'num_envs': cfg.scene.num_envs, 'contract_sha256': args.contract_sha256,
                'configuration_sha256': configuration_digest(cfg, agent)}
    task = f'Climb-Tracking-Flat-Unitree-G1-Gate-Study-{args.admission.title()}'
    design = {**identity, 'contract': record(args.contract), 'device': args.device, 'task': task,
              'sources': contract['sources'], 'config': canonical(cfg), 'agent': canonical(agent)}
    (out / 'design.json').write_text(json.dumps(design, indent=2)+'\n')

    class GateStudyRunner(MotionTrackingOnPolicyRunner):
        def __init__(self, *runner_args, **kwargs):
            super().__init__(*runner_args, **kwargs)
            if str(self.env.unwrapped.device) != args.device:
                raise ValueError('actual simulator device differs from declared device')
            (run / 'initial_actor.json').write_text(json.dumps(
                {'sha256': actor_digest(self.alg.get_policy()), 'seed': args.seed}, indent=2)+'\n')

        def save(self, path, infos=None):
            super().save(path, infos)
            command = self.env.unwrapped.command_manager.get_term('motion')
            checkpoint = Path(path)
            state = checkpoint.with_name(f'{checkpoint.stem}_sampler.pt')
            torch.save(command.sampler.state_dict(), state)
            ledger = {**identity, 'iteration': int(self.current_learning_iteration),
                      'common_step_counter': int(self.env.unwrapped.common_step_counter),
                      'segment': command.segment_telemetry(), 'checkpoint_sha256': file_digest(checkpoint),
                      'sampler_sha256': file_digest(state)}
            checkpoint.with_name(f'{checkpoint.stem}_gate.json').write_text(json.dumps(ledger, indent=2)+'\n')

    register_mjlab_task(task_id=task, env_cfg=cfg, play_env_cfg=cfg, rl_cfg=agent, runner_cls=GateStudyRunner)
    start = time.monotonic()
    try:
        run_train(task, TrainConfig(env=cfg, agent=agent, log_root=str(out)), run)
        (out / 'execution.json').write_text(json.dumps({**identity, 'device': args.device,
            'status': 'completed', 'elapsed_seconds': time.monotonic()-start}, indent=2)+'\n')
        result = verify_training(run, contract, args.contract_sha256, args.admission, args.seed, smoke=args.smoke)
        (out / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({'status': result['status'], 'admission': args.admission,
                          'completed_trials': result['completed_trials']}), flush=True)
    except Exception as exc:
        (out / 'failure.json').write_text(json.dumps({'status': 'gate_study_failed', 'reason': str(exc)}, indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
