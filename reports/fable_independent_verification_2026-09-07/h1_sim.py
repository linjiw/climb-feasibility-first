"""Simulate integrate_h1.py's edits on a given root.tex (worst-case 'inconclusive' branch)."""
import re, sys
from pathlib import Path
f=Path(sys.argv[1]); src=f.read_text()
src=re.sub(r'\\title\{.*?\n\}',lambda _:r'''\title{\LARGE \bf
Feasibility-First Humanoid Motion Tracking:\\
Screening Reference--Physics Misalignment and a Matched Test of Admission and Allocation
}''',src,count=1,flags=re.S)
src=re.sub(r'\\begin\{abstract\}.*?\\end\{abstract\}',lambda _:r'''\begin{abstract}
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
is \emph{inconclusive}: feasible-hard on-minus-off is $+0.0121$, interval $[-0.0184,+0.0426]$.
These tests distinguish model-relative qualification, changed exposure and measured
control utility; none alone establishes physical feasibility or general transfer.
\end{abstract}''',src,count=1,flags=re.S)
src=src.replace('study with a complete, inconclusive policy result and explicit exposure measurements.',
 'study with a complete, inconclusive policy result and explicit exposure measurements;\n  \\item a separately frozen five-pair admission on/off test under conditional-failure\n  allocation, reporting its effect and rejected-support exposure without conflating\n  admission with the allocation comparison.')
src=src.replace("Admission's learning value requires a separate on/off experiment under a common allocator;\nthe present allocation comparison cannot answer it.",
 'The separate admission comparison changes the admission mask under a common allocator;\nit does not test an admission-by-relative-progress interaction.')
src=src.replace('\\section{Results}',r'''
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

'''+'\\section{Results}',1)
src=src.replace('\\section{Limitations}',r'''
\subsection{H1: admission under D}
\label{sec:h1result}
All ten full-budget training runs and forty held-out cells pass their gates:
410 saved training states replay exactly, and 112,000 evaluation rows preserve
paired initial conditions and unchanged inference tensors. Admission on has zero
rejected trials; off has positive rejected exposure and respects the declared
0.0923 probability floor. Both have zero invalid or censored events.

The registered disposition is \emph{inconclusive}. Final hard on-minus-off seed differences
are $+0.0300/-0.0100/+0.0200/+0.0050/+0.0150$; mean $+0.0121$, 95\% seed-t interval $[-0.0184,+0.0426]$.
The interval spans zero; admission benefit, harm and equivalence remain unestablished. All-panel mean is $+0.0098$, interval $[-0.0210,+0.0406]$;
this descriptive result has no non-regression pass/fail guard.

Gate-off's rejected share of positive excess allocation averages 31.4\% across
seeds (range 28.0--35.0\%), compared with 11.54\% of legal starts in its prior.
This is a ratio of checkpoint-summed positive excess, not the fraction of all
training samples and not a causal estimate of wasted practice. Figure~\ref{fig:h1}
shows every seed. The intervention estimates admission under D; it cannot identify
an admission-by-R interaction or which ingredients caused the historical E1 collapse.
Both arms consume the same 49.2 million transitions, so admission changes the composition and
breadth of support rather than the amount of experience: gate-off draws from 11.54\% more
legal-start mass. A reference-blind exclusion arm matched on removed start mass would separate
physics-informed selection from support narrowing, and is outside this frozen two-arm test.

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

'''+'\\section{Limitations}',1)
src=src.replace('A matched on/off admission comparison under D is the next distinct test;\nno incomplete result enters this manuscript.',
 'The separate H1 comparison below estimates admission under D on a common candidate partition.')
src=src.replace('The learning value of admission under a common\nallocator remains the next direct experiment.',
 'The separate five-pair admission test under D is inconclusive; its claim\nis limited to that intervention, model and held-out panel.')
src=src.replace('The allocation study has only three independent seed pairs.',
 'The allocation study has three independent seed pairs; H1 has five separate pairs.\nNeither the shared held-out panel nor the number of evaluation conditions increases these counts.')
f.write_text(src); print('h1 sim applied')
