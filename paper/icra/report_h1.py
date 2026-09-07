"""Replay a terminal H1 campaign and export its registered result for the paper."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
H1 = Path('/home/linjiw/climb-gate-ablation-2026-09-06')
CONTRACT_SHA256 = 'fdc5354045bb848fb982822d5ebd6d9b40ca88cb14209acc6b880579eed4b474'
SEEDS = (1041, 1042, 1043, 1044, 1045)
ITERATIONS = (1000, 2000, 3000, 3999)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path: Path) -> dict:
    return {'path': str(path.resolve()), 'sha256': digest(path)}


def write_json(path: Path, value: dict) -> None:
    with path.open('x') as handle:
        handle.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def terminal_input(campaign: Path) -> tuple[dict, dict]:
    """Reject partial campaigns before opening their analysis or any outcomes."""
    terminal_path = campaign / 'terminal_status.json'
    terminal = json.loads(terminal_path.read_text())
    if terminal.get('status') != 'completed':
        raise ValueError('no manuscript outcome from a non-complete H1 campaign')
    binding = terminal['contract']
    if binding['sha256'] != CONTRACT_SHA256 or digest(Path(binding['path'])) != CONTRACT_SHA256:
        raise ValueError('unexpected or changed H1 contract')
    result = terminal['analysis']
    expected = campaign / 'analysis.json'
    if Path(result['path']).resolve() != expected.resolve() or digest(expected) != result['sha256']:
        raise ValueError('analysis differs from terminal binding')
    return terminal, json.loads(expected.read_text())


def replay(campaign: Path) -> tuple[dict, dict]:
    terminal, saved = terminal_input(campaign)
    sys.path.insert(0, str(H1 / 'paper/h1'))
    import protocol
    import job

    binding = terminal['contract']
    contract = protocol.verify_contract(Path(binding['path']), CONTRACT_SHA256, smoke=False)
    if Path(contract['campaign']).resolve() != campaign.resolve():
        raise ValueError('campaign path differs from contract')
    contract['self_record'] = binding
    result = job.aggregate(contract, CONTRACT_SHA256)
    normalized = json.loads(json.dumps(result, allow_nan=False))
    if normalized != saved:
        raise ValueError('full frozen analysis does not reproduce exactly')
    starts, completions = {}, {}
    for item in contract['schedule']:
        started = json.loads((campaign / f"{item['id']}.started.json").read_text())
        completed = json.loads((campaign / f"{item['id']}.completed.json").read_text())
        if started['job'] != item or completed['job'] != item or completed['exit_code'] != 0:
            raise ValueError('job sentinels differ from schedule')
        bound = completed['result']
        if digest(Path(bound['path'])) != bound['sha256']:
            raise ValueError('completed job artifact changed')
        starts[item['id']] = started['started_at']
        completions[item['id']] = completed['completed_at']
    if max(t for k, t in completions.items() if k.startswith('train_')) >= min(t for k, t in starts.items() if k.startswith('evaluate_')):
        raise ValueError('held-out evaluation began before all training completed')
    return saved, {'status': 'exact_H1_replay_pass', 'classification': 'measured complete campaign replay',
                   'contract': binding, 'terminal': record(campaign / 'terminal_status.json'),
                   'analysis': record(campaign / 'analysis.json'), 'analyzer': record(H1 / 'paper/h1/job.py'),
                   'reporter': record(Path(__file__)), 'training_runs': 10, 'full_training_states': 410,
                   'evaluation_cells': 40, 'episode_rows': saved['episode_rows'], 'numeric_tolerance': 0,
                   'training_before_evaluation': True}


def mechanism(training: dict) -> list[dict]:
    rows = []
    for seed in SEEDS:
        for arm in ('on', 'off'):
            value = training[f'{arm}_s{seed}']
            snapshots = value['mechanism']
            if [r['iteration'] for r in snapshots] != [*range(1000, 4000, 100), 3999]:
                raise ValueError('post-warm-up checkpoint grid changed')
            excess = sum(row['positive_excess_total'] for row in snapshots)
            rejected = sum(row['positive_excess_rejected'] for row in snapshots)
            final = snapshots[-1]
            rows.append({'arm': arm, 'seed': seed, 'postwarmup_states': len(snapshots),
                         'prior_rejected_mass': value['final_allocation']['uncapped_prior_rejected_mass'],
                         'rejected_share_of_positive_excess': rejected / excess if excess else None,
                         'zero_excess_states': sum(row['positive_excess_total'] == 0 for row in snapshots),
                         'final_rejected_probability': value['final_allocation']['post_cap_rejected_mass'],
                         'rejected_completed_trials': value['final_allocation']['rejected_completed_trials'],
                         'all_completed_trials': value['completed_trials'],
                         'top1_rejected_state_fraction': sum(row['top1_rejected'] for row in snapshots) / len(snapshots),
                         'final_top1_unit': final['top1_unit'], 'final_top1_rejected': final['top1_rejected']})
    return rows


def export(result: dict, out: Path) -> dict:
    """Present frozen estimates without changing decisions or pooling seed units."""
    import matplotlib
    matplotlib.use('Agg')
    matplotlib.rcParams.update({'pdf.fonttype': 42, 'ps.fonttype': 42, 'font.size': 9})
    import matplotlib.pyplot as plt

    if result.get('schema_version') != 'h1_fable_result/2' or result.get('evaluated_cells') != 40:
        raise ValueError('requires the complete frozen H1 result schema')
    primary = result['primary_on_minus_off']
    broad = result['all_panel_on_minus_off']
    if primary['independent_units'] != 5 or primary['df'] != 4:
        raise ValueError('independent seed count changed')
    out.mkdir(parents=True, exist_ok=False)
    allocation = mechanism(result['training'])
    summary = {k: result[k] for k in ('status', 'classification', 'contract', 'primary_on_minus_off',
                                      'all_panel_on_minus_off', 'reference_effect', 'all_panel_pass_fail_guard',
                                      'evaluated_cells', 'episode_rows', 'training_transitions_per_policy', 'limitations')}
    summary['mechanism'] = allocation
    summary['mechanism_scope'] = ('Ratio of equal-weight checkpoint sums of rejected/all positive excess above the prior, '
                                 'iterations 1000..3900 by 100 and 3999. Not a fraction of all training samples or a causal waste estimate.')
    write_json(out / 'summary.json', summary)
    with (out / 'paired_final.csv').open('x') as handle:
        writer = csv.writer(handle)
        writer.writerow(['seed', 'feasible_hard_on_minus_off', 'all_panel_on_minus_off'])
        for seed in SEEDS:
            writer.writerow([seed, primary['paired_seed_deltas'][str(seed)], broad['paired_seed_deltas'][str(seed)]])
    fig, axes = plt.subplots(1, 3, figsize=(10.6, 3.25), constrained_layout=True)
    for axis, panel, title in zip(axes[:2], (primary, broad), ('Feasible-hard', 'All-panel')):
        y = [panel['paired_seed_deltas'][str(seed)] for seed in SEEDS]
        axis.scatter(range(5), y, color='#2c6874', s=25)
        mean, (lo, hi) = panel['mean'], panel['seed_t_95ci']
        axis.errorbar(5.3, mean, yerr=[[mean-lo], [hi-mean]], color='#26343b', fmt='D', capsize=4)
        axis.axhline(0, color='#444444', lw=.7)
        if title == 'Feasible-hard':
            axis.axhline(.02, color='#b97929', ls='--', lw=.8)
        axis.set(xticks=[*range(5), 5.3], xticklabels=[*map(str, SEEDS), 'Mean\n+ CI'],
                 title=title + ' · on − off', ylabel='TrackingScore difference')
        axis.tick_params(axis='x', labelsize=7)
        axis.spines[['top', 'right']].set_visible(False)
    off = [r for r in allocation if r['arm'] == 'off']
    shares = [np.nan if r['rejected_share_of_positive_excess'] is None else r['rejected_share_of_positive_excess'] for r in off]
    axes[2].bar(range(5), shares, color='#b97929', alpha=.8)
    axes[2].axhline(off[0]['prior_rejected_mass'], color='#444444', ls='--', label='Rejected share of legal starts')
    axes[2].set(xticks=range(5), xticklabels=list(map(str, SEEDS)), ylim=(0, 1),
                title='Gate-off allocation attribution', ylabel='Rejected share of positive excess')
    axes[2].tick_params(axis='x', labelsize=7)
    axes[2].legend(fontsize=6.5, loc='upper left')
    axes[2].spines[['top', 'right']].set_visible(False)
    label = 'SYNTHETIC — ' if result['classification'].startswith('SYNTHETIC') else ''
    fig.suptitle(f"{label}H1 admission under D: {result['status']} · five independent seed pairs", fontsize=11)
    for ext in ('pdf', 'png'):
        fig.savefig(out / f'h1_paired_and_allocation.{ext}', dpi=180)
    plt.close(fig)
    curve_rows = []
    for iteration in ITERATIONS:
        arrays = result['clip_scores'][str(iteration)]
        for arm in ('on', 'off'):
            values = np.asarray(arrays[arm])
            if values.shape != (5, 100) or not np.isfinite(values).all():
                raise ValueError('invalid complete learning curve array')
            for index, seed in enumerate(SEEDS):
                curve_rows.append({'iteration': iteration, 'transitions': (iteration+1)*24*512,
                                   'arm': arm, 'seed': seed, 'all_panel': float(values[index].mean()),
                                   'feasible_hard': float(values[index, result['hard_indices']].mean())})
    with (out / 'learning_curves.csv').open('x') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(curve_rows[0]))
        writer.writeheader()
        writer.writerows(curve_rows)
    lines = [f"# H1 admission under D: {result['status']}", '',
             ('SYNTHETIC fixture only; no measured policy outcome.' if label else
              'Measured complete five-paired-seed comparison. Ten full training runs; 40 evaluation cells.'), '',
             '| Seed | Feasible-hard on−off | All-panel on−off |', '| --- | ---: | ---: |']
    lines += [f"| {seed} | {primary['paired_seed_deltas'][str(seed)]:+.6f} | {broad['paired_seed_deltas'][str(seed)]:+.6f} |" for seed in SEEDS]
    lines += [f"| Mean | {primary['mean']:+.6f} | {broad['mean']:+.6f} |",
              f"| Two-sided t 95% CI, df=4 | [{primary['seed_t_95ci'][0]:+.6f}, {primary['seed_t_95ci'][1]:+.6f}] | [{broad['seed_t_95ci'][0]:+.6f}, {broad['seed_t_95ci'][1]:+.6f}] |", '',
              'The +0.02 line is descriptive. There is no all-panel pass/fail guard. Bootstrap and intermediate checkpoints are supplementary.', '',
              summary['mechanism_scope'], '',
              'This estimates admission under D, not an admission-by-R interaction. The held-out panel is reused from the earlier allocation comparison. An interval spanning zero does not establish equivalence or absence of harm.', '']
    (out / 'README.md').write_text('\n'.join(lines))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    result, verification = replay(args.campaign.resolve())
    export(result, args.out_dir)
    write_json(args.out_dir / 'verification.json', verification)
    print(json.dumps({'status': result['status'], 'verification': verification['status'], 'out_dir': str(args.out_dir)}))


if __name__ == '__main__':
    os.environ.update(CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    main()
