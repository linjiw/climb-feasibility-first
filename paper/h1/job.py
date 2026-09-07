"""Execute one assigned H1 job; authenticate all training before held-out reads."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import sys

import protocol as p


def evaluation(contract: dict, digest: str, job: dict, out: Path) -> None:
    import torch
    from audit_policy_immutability import observe_policy
    from eval_gate_development import count_steps, verify_loaded_actor
    from eval_natural_lifecycle import verify_policy
    from h1_evaluation_provenance import expectations, verify_cell
    import eval_paired_v2

    training = p.all_training(contract, digest)
    out.mkdir(exist_ok=False)
    arm, seed, iteration = job['arm'], job['seed'], job['iteration']
    design = {'evaluator_arguments': contract['evaluator_arguments'], 'gate_worktree': str(p.ROOT),
              'gate_contract': contract['self_record']}
    expected = expectations(design, training[(arm, seed)], arm, seed, iteration)
    args = argparse.Namespace(**contract['evaluator_arguments'])
    for key in ('clips', 'bank', 'common_reference_bank', 'conditions'):
        setattr(args, key, Path(getattr(args, key)))
    args.checkpoint = Path(expected['checkpoint']['path'])
    args.out = out / 'evaluation.csv'
    policy, lifecycle = {}, {}
    with observe_policy(policy), count_steps(lifecycle):
        code = eval_paired_v2.evaluate(args)
    if code:
        raise ValueError(f'evaluator failed: {code}')
    if lifecycle['steps'] != 150:
        raise ValueError('expected exactly 150 unmodified evaluation steps')
    result = verify_policy(policy, lifecycle['steps'])
    verify_loaded_actor(policy, args.checkpoint)
    torch.save(policy, out / 'policy.pt')
    cell = {'csv': p.record(args.out), 'metadata': p.record(out / 'evaluation.csv.meta.json'),
            'checkpoint': expected['checkpoint'], 'ledger': expected['ledger']}
    checked = verify_cell(cell, expected)
    p.dump(out / 'result.json', {'status': 'h1_evaluation_pass', 'job': job, 'contract_sha256': digest,
                              'cell': cell, 'verified_cell': checked, 'policy': p.record(out / 'policy.pt'),
                              'policy_check': result, 'steps': lifecycle['steps']})


def aggregate(contract: dict, digest: str) -> dict:
    import numpy as np
    import torch
    from analyze_relative_policy import aggregate_rows
    from eval_gate_development import verify_loaded_actor
    from eval_natural_lifecycle import verify_policy
    from h1_evaluation_provenance import expectations, verify_cell, verify_pairing

    training = p.all_training(contract, digest)  # No CSV opened before this completes.
    design = {'evaluator_arguments': contract['evaluator_arguments'], 'gate_worktree': str(p.ROOT),
              'gate_contract': contract['self_record']}
    receipts, checked = [], []
    for job in p.schedule()[12:]:
        out = Path(contract['campaign']) / job['id']
        row = json.loads((out / 'result.json').read_text())
        if row['status'] != 'h1_evaluation_pass' or row['job'] != job or row['contract_sha256'] != digest:
            raise ValueError('evaluation receipt identity mismatch')
        expected = expectations(design, training[(job['arm'], job['seed'])], job['arm'], job['seed'], job['iteration'])
        replay = verify_cell(row['cell'], expected)
        if replay != row['verified_cell']:
            raise ValueError('evaluation receipt does not replay')
        policy = torch.load(p.verified(row['policy']), map_location='cpu', weights_only=True)
        verify_loaded_actor(policy, Path(expected['checkpoint']['path']))
        if row['steps'] != 150 or verify_policy(policy, row['steps']) != row['policy_check']:
            raise ValueError('policy inference integrity mismatch')
        receipts.append(row)
        checked.append(replay)
    verify_pairing(checked, {(a, s, i) for a in p.ARMS for s in p.SEEDS for i in p.CHECKPOINTS})
    args = contract['evaluator_arguments']
    clips = Path(args['clips']).read_text().splitlines()
    conditions = json.loads(Path(args['conditions']).read_text())['conditions']
    scores = {i: {a: np.zeros((5, 100)) for a in p.ARMS} for i in p.CHECKPOINTS}
    for receipt in receipts:
        job = receipt['job']
        with p.verified(receipt['cell']['csv']).open() as handle:
            rows = list(csv.DictReader(handle))
        scores[job['iteration']][job['arm']][p.SEEDS.index(job['seed'])] = aggregate_rows(rows, conditions, clips, window_s=3.)
    hard = np.array(contract['hard_indices'])
    result = p.analyze(scores[3999], hard)
    result.update(schema_version='h1_fable_result/2', classification='measured five-paired-seed H1 under D',
                  contract=contract['self_record'], evaluated_cells=40, episode_rows=40 * len(conditions),
                  training_transitions_per_policy=49152000,
                  checkpoint_results_descriptive={str(i): p.analyze(scores[i], hard) for i in p.CHECKPOINTS},
                  clip_order=clips, hard_indices=hard.tolist(),
                  clip_scores={str(i): {a: v.tolist() for a, v in arms.items()} for i, arms in scores.items()},
                  training={f'{a}_s{s}': v for (a, s), v in training.items()},
                  evaluation_receipts=[p.record(Path(contract['campaign']) / j['id'] / 'result.json') for j in p.schedule()[12:]],
                  limitations=['All-panel intervals and bootstrap do not override the primary decision.',
                               'Admission effect under D does not establish an admission-by-R interaction.',
                               'The held-out panel is reused from the completed allocation study; H1 seeds and comparison are new.',
                               'An interval spanning zero establishes neither equivalence nor absence of harm.'])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--job-id', required=True)
    args = parser.parse_args()
    selected = [j for j in p.schedule() if j['id'] == args.job_id]
    if not selected and args.job_id != 'aggregate':
        raise ValueError('job outside frozen schedule')
    smoke = bool(selected and selected[0]['stage'] == 'smoke')
    contract = p.verify_contract(args.contract, args.sha256, smoke=smoke)
    if args.job_id == 'aggregate':
        contract['self_record'] = p.record(args.contract)
        p.dump(Path(contract['campaign']) / 'analysis.json', aggregate(contract, args.sha256))
        return
    job = selected[0]
    out = Path(contract['campaign']) / job['id']
    if job['stage'] in ('train', 'smoke'):
        import train_gate_study
        train_gate_study.verify_contract = p.verify_contract
        train_gate_study.verify_training = p.verify_training
        sys.argv = [sys.argv[0], '--contract', str(args.contract), '--contract-sha256', args.sha256,
                    '--admission', job['arm'], '--seed', str(job['seed']), '--device', 'cuda:0', '--out-dir', str(out)]
        if smoke:
            sys.argv.append('--smoke')
        train_gate_study.main()
    else:
        contract['self_record'] = p.record(args.contract)
        evaluation(contract, args.sha256, job, out)


if __name__ == '__main__':
    os.environ.update(CUDA_VISIBLE_DEVICES='0', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', WANDB_MODE='offline', MUJOCO_GL='egl')
    import torch
    torch.set_num_threads(1)
    main()
