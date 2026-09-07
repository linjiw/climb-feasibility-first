"""Integrate a fully replayed H1 result into the unsealed manuscript once."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil

from report_h1 import CONTRACT_SHA256, digest, terminal_input

ROOT = Path(__file__).resolve().parents[2]


def signed(value: float, digits: int = 4) -> str:
    return f'{value:+.{digits}f}'


def interval(panel: dict) -> str:
    return '[' + ','.join(signed(v) for v in panel['seed_t_95ci']) + ']'


def integrate(report: Path) -> None:
    verification = json.loads((report / 'verification.json').read_text())
    if verification['status'] != 'exact_H1_replay_pass' or verification['contract']['sha256'] != CONTRACT_SHA256:
        raise ValueError('H1 manuscript requires a complete exact replay receipt')
    campaign = Path(verification['terminal']['path']).parent
    terminal, result = terminal_input(campaign)
    for name in ('terminal', 'analysis', 'reporter', 'analyzer'):
        bound = verification[name]
        if digest(Path(bound['path'])) != bound['sha256']:
            raise ValueError(f'H1 verified {name} changed')
    summary = json.loads((report / 'summary.json').read_text())
    for key in ('primary_on_minus_off', 'all_panel_on_minus_off', 'status', 'contract'):
        if summary[key] != result[key]:
            raise ValueError('H1 report differs from frozen result')
    primary, broad = summary['primary_on_minus_off'], summary['all_panel_on_minus_off']
    status = summary['status']
    if status not in ('positive', 'negative', 'inconclusive'):
        raise ValueError('unknown frozen H1 disposition')
    meanings = {
        'positive': 'Admission improves feasible-hard tracking under D in this comparison.',
        'negative': 'Admission reduces feasible-hard tracking under D in this comparison.',
        'inconclusive': 'The interval spans zero; admission benefit, harm and equivalence remain unestablished.',
    }
    off = [r for r in summary['mechanism'] if r['arm'] == 'off']
    shares = [r['rejected_share_of_positive_excess'] for r in off]
    if len(off) != 5 or any(v is None for v in shares):
        raise ValueError('undefined mechanism share requires an explicit manuscript qualification')
    mean_share = sum(shares) / 5
    share_range = (min(shares), max(shares))
    prior = off[0]['prior_rejected_mass']
    seeds = '/'.join(signed(primary['paired_seed_deltas'][str(s)]) for s in (1041,1042,1043,1044,1045))
    file = ROOT / 'paper/icra/root.tex'
    source = file.read_text()
    if '\\label{sec:h1result}' in source:
        raise ValueError('H1 already integrated; do not reapply the migration')
    backup = report / 'no_h1_root.tex'
    with backup.open('x') as handle:
        handle.write(source)
    title = r'''\title{\LARGE \bf
Feasibility-First Humanoid Motion Tracking:\\
Screening Reference--Physics Misalignment and a Matched Test of Admission and Allocation
}'''
    source = re.sub(r'\\title\{.*?\n\}', lambda _: title, source, count=1, flags=re.S)
    abstract = r'''\begin{abstract}
Persistent tracking failure need not identify useful practice: a retargeted reference
may demand support unavailable under the declared robot and scene. We study this
reference--physics misalignment through model-relative screening and matched training
experiments. In a three-seed G1 campaign, exposure peaks at 87--89\%, an unsupported
kneel-and-crawl reference repeatedly attracts practice, and uniform sampling yields
higher held-out survival in each seed. A contact-capacity screen flags 2,442/10,705
AMASS-derived references in one pipeline and 7/4,950 in a separate production pairing;
two implementations agree on 39/40 enriched-panel decisions. Feasibility features
improve cross-policy difficulty correlation from 0.567 to 0.609 on 100 held-out clips.
Exact temporal support then separates two interventions at 49.2 million transitions
per policy. The completed three-seed allocation comparison is inconclusive:
feasible-hard relative-progress minus uniform TrackingScore is $-0.0151$ with paired
95\% seed-t interval $[-0.0944,+0.0642]$, and its broad non-regression guard fails.
A separate five-seed admission on/off comparison under conditional-failure allocation
is \emph{STATUS}: feasible-hard on-minus-off is $MEAN$, interval $INTERVAL$.
These tests distinguish model-relative qualification, changed exposure and measured
control utility; none alone establishes physical feasibility or general transfer.
\end{abstract}'''.replace('STATUS', status).replace('MEAN', signed(primary['mean'])).replace('INTERVAL', interval(primary))
    source = re.sub(r'\\begin\{abstract\}.*?\\end\{abstract\}', lambda _: abstract, source, count=1, flags=re.S)
    source = source.replace('study with a complete, inconclusive policy result and explicit exposure measurements.',
        'study with a complete, inconclusive policy result and explicit exposure measurements;\n  \\item a separately frozen five-pair admission on/off test under conditional-failure\n  allocation, reporting its effect and rejected-support exposure without conflating\n  admission with the allocation comparison.')
    source = source.replace("Admission's learning value requires a separate on/off experiment under a common allocator;\nthe present allocation comparison cannot answer it.",
        'The separate admission comparison changes the admission mask under a common allocator;\nit does not test an admission-by-relative-progress interaction.')
    design = r'''
\subsection{H1: matched admission under conditional failure}
The separately frozen H1 study compares D with admission on/off over a common
candidate partition: 1,184 admitted and 465 rejected units, with 368,951 of 417,072
legal starts admitted. On renormalizes the legal-start prior over the admitted
subset; off retains all candidate units. Both retain non-wrapping 50-step trials,
the common learner, budget and unit/clip caps. Five fresh paired seeds (1041--1045)
yield ten training runs; all training gates precede forty evaluations on the same
100-clip panel and checkpoint grid. This panel is reused from the allocation study.
The final hard on-minus-off two-sided seed-t interval (df=4) determines positive
(lower $>0$), negative (upper $<0$), or inconclusive. The $+0.02$ line is descriptive;
all-panel and bootstrap intervals carry no additional decision rule. The mechanism
endpoint attributes positive excess above the prior to rejected units using equal-weight
saved checkpoints 1000--3900 by 100 and 3999; it also records top-1 identity.

'''
    source = source.replace('\\section{Results}', design + '\\section{Results}', 1)
    result_text = r'''
\subsection{H1: admission under D}
\label{sec:h1result}
All ten full-budget training runs and forty held-out cells pass their gates:
410 saved training states replay exactly, and 112,000 evaluation rows preserve
paired initial conditions and unchanged inference tensors. Admission on has zero
rejected trials; off has positive rejected exposure and respects the declared
0.0923 probability floor. Both have zero invalid or censored events.

The registered disposition is \emph{STATUS}. Final hard on-minus-off seed differences
are $SEEDS$; mean $MEAN$, 95\% seed-t interval $INTERVAL$.
MEANING All-panel mean is $BROADMEAN$, interval $BROADINTERVAL$;
this descriptive result has no non-regression pass/fail guard.

Gate-off's rejected share of positive excess allocation averages SHARE\% across
seeds (range LOW--HIGH\%), compared with PRIOR\% of legal starts in its prior.
This is a ratio of checkpoint-summed positive excess, not the fraction of all
training samples and not a causal estimate of wasted practice. Figure~\ref{fig:h1}
shows every seed. The intervention estimates admission under D; it cannot identify
an admission-by-R interaction or which ingredients caused the historical E1 collapse.

\begin{figure*}[t]
\centering
\includegraphics[width=\textwidth]{h1_paired_and_allocation.pdf}
\caption{H1 admission on/off under D: five paired trained seeds and their mean with
two-sided 95\% seed-t interval (df=4). The hard-panel dashed line is a reference,
not a pass/fail target. At right, rejected share of positive excess above the prior
uses the frozen post-warm-up checkpoint grid; its dashed line is the rejected
legal-start prior share. Allocation attribution is distinct from policy utility.}
\label{fig:h1}
\end{figure*}

'''
    replacements = {'STATUS':status, 'SEEDS':seeds, 'MEANING':meanings[status],
                    'BROADINTERVAL':interval(broad), 'BROADMEAN':signed(broad['mean']),
                    'INTERVAL':interval(primary), 'MEAN':signed(primary['mean']),
                    'SHARE':f'{100*mean_share:.1f}', 'LOW':f'{100*share_range[0]:.1f}',
                    'HIGH':f'{100*share_range[1]:.1f}', 'PRIOR':f'{100*prior:.2f}'}
    for key in sorted(replacements, key=len, reverse=True):
        result_text = result_text.replace(key, replacements[key])
    source = source.replace('\\section{Limitations}', result_text + '\\section{Limitations}', 1)
    source = source.replace('A matched on/off admission comparison under D is the next distinct test;\nno incomplete result enters this manuscript.',
                            'The separate H1 comparison below estimates admission under D on a common candidate partition.')
    source = source.replace('The learning value of admission under a common\nallocator remains the next direct experiment.',
                            'The separate five-pair admission test under D is '+status+'; its claim\nis limited to that intervention, model and held-out panel.')
    source = source.replace('The allocation study has only three independent seed pairs.',
                            'The allocation study has three independent seed pairs; H1 has five separate pairs.\nNeither the shared held-out panel nor the number of evaluation conditions increases these counts.')
    # Preserve the measured figure bytes; build staging only, never edit published data.
    for suffix in ('pdf', 'png'):
        shutil.copyfile(report / f'h1_paired_and_allocation.{suffix}', ROOT / f'paper/icra/figures/h1_paired_and_allocation.{suffix}')
    file.write_text(source)
    build = ROOT / 'paper/icra/build.sh'
    text = build.read_text()
    needle = 'cp "$SCRIPT_DIR/figures/f1_evidence_interface.pdf"'
    replacement = 'cp "$SCRIPT_DIR/figures/h1_paired_and_allocation.pdf" "$BUILD_DIR/"\n\n' + needle
    if 'cp "$SCRIPT_DIR/figures/h1_paired_and_allocation.pdf"' not in text:
        if needle not in text:
            raise ValueError('unknown manuscript build staging')
        build.write_text(text.replace(needle, replacement))
    print(json.dumps({'status': status, 'source': str(file), 'next': 'Build and review all pages before final handoff'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    integrate(args.report.resolve())
