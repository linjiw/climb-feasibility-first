"""One-time manuscript revision from the completed, independently replayed result."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'paper/icra/root.tex'
text = path.read_text()


def section(first: str, last: str, replacement: str) -> None:
    global text
    start, stop = text.index(first), text.index(last, text.index(first))
    text = text[:start] + replacement + '\n\n' + text[stop:]


section(r'\title{', r'\author{', r'''\title{\LARGE \bf
When Failure Is Not Difficulty: Screening Reference--Physics Misalignment\\
and Testing Adaptive Allocation on Exact Support for Humanoid Motion Tracking
}''')
section(r'\begin{abstract}', r'\section{Introduction}', r'''\begin{abstract}
Persistent tracking failure need not identify useful practice: a retargeted reference may
demand support unavailable under the declared robot and scene. We study this
reference--physics misalignment (RPM) through model-relative screening and controlled
allocation experiments. In a three-seed Unitree G1 campaign, top-1 exposure peaks at
87--89\%, an unsupported kneel-and-crawl reference repeatedly attracts practice, and
uniform sampling yields higher held-out survival in each seed. A final-trajectory
contact-capacity screen flags 2,442 of 10,705 AMASS-derived references in one retargeting
pipeline and 7 of 4,950 in a separate production pairing; two implementations agree on
39 of 40 enriched-panel decisions. Feasibility features improve cross-policy difficulty
transfer from Spearman correlation 0.567 to 0.609 over 100 held-out clips. We then bind
training to 1,184 exact temporal units and compare four allocators at equal support and
49.2 million transitions per policy. Relative-progress allocation changes exposure but
does not establish the registered tracking benefit: feasible-hard R$-$U TrackingScore
is $-0.0151$, with paired seed-level 95\% interval $[-0.0944,+0.0642]$. The broad
non-regression criterion also fails, and exploratory learning curves favor uniform.
These results separate reference admission, sampling intervention, and policy utility;
they establish neither allocation equivalence nor a general advantage of gating.
\end{abstract}''')
section('Under RPM, policy failure conflates three distinct', 'We observed the consequence', r'''Under RPM, failures can reflect reference inadmissibility as well as limited
experience or control capability. Our implemented screen addresses the first distinction.
A coverage floor cannot create a behavior absent from the bank, and a progress estimate
does not identify intrinsic difficulty or forgetting. The experimental question is therefore:
given fixed reference support and a training budget, does learner-dependent allocation
produce better tracking on the same held-out objective?

''')
section(r'\method{} closes the interface', r'\section{Related Work}', r'''\method{} makes reference admission and practice allocation separately testable
(Fig.~\ref{fig:interface}). The \texttt{refeas} screen evaluates final robot-space references
under a declared model; temporal units enforce support throughout each trial. A bounded
allocator may use policy outcomes to change exposure within that support. Whether this
feedback improves control is an empirical question, not a property of the interface.

Our contributions are:
\begin{enumerate}
  \item an RPM diagnosis and model-relative contact-capacity screen, evaluated at bank
  scale and across implementations, with feasibility features that transfer difficulty
  information between policies sharing a learner;
  \item an exact temporal-support interface and a matched four-arm, three-seed allocation
  study with a complete, inconclusive policy result and explicit exposure measurements.
\end{enumerate}
We also report a bounded repair alternative: 22/26 screened candidates qualify, yet a
one-policy paired deployment comparison does not establish an aggregate tracking gain.
Admission's learning value requires a separate on/off experiment under a common allocator;
the present allocation comparison cannot answer it.''')
text = text.replace(r'\section{\method{}: Data-to-Policy Framework}',
                    r'\section{Screening and Exact Temporal Support}')
section(r'\subsection{DFRP: contact-manifold repair}',
        r'\subsection{Exact-support gated allocation}', r'''\subsection{Repair as a routing alternative}
DFRP applies a bounded contact projection to qualified floating-reference cases. It lowers
and smooths root clearance, then adjusts supporting-leg joints with damped contact inverse
kinematics and joint-limit projection. The changed trajectory is re-screened and must
satisfy residual infeasibility at most 5\%, root displacement at most 8\,cm, valid joint
limits, contact-IK residual at most 10\,mm, and at least one legal 50-step start. Missing-scene
cases bypass projection. This is an implemented routing option, not a guarantee of usable
control: repair changes the tracking target and needs its own paired policy evaluation.''')
section('Let $\\mathcal U$ contain candidate units', 'Intervals do not all receive', r'''For an admitted interval $\mathcal A_u$, define legal starts by every reference
frame accessed during horizon $H$ and lookahead configuration $\mathcal L$:
\begin{equation}
\mathcal S_u=\{s:s+\mathcal K(H,\mathcal L)\subseteq\mathcal A_u\}.
\end{equation}
The current interface includes the terminal observation and uses current-frame reference
observations. ``Exact'' denotes membership relative to this screen and access contract;
it is not a certificate of physical feasibility.

Let $b_u$ be the normalized legal-start prior over admitted units and
$g_u=|s_u(k)-s_u(k-10)|$ the nonnegative change of Beta-smoothed conditional success
at sampler clock $k$. Uniform U uses $b$. Absolute-progress A retains the earlier
fixed additive floor. Relative-progress R, before active caps and for complete
history with $\mu=\sum_u b_ug_u>0$, is exactly
\begin{equation}
p_u=0.8b_u+0.2\frac{b_ug_u}{\mu}.
\label{eq:gate}
\end{equation}
The implemented prior/cap fallback covers incomplete history or zero $\mu$.
Common positive rescaling of $g$ leaves Eq.~\eqref{eq:gate} unchanged, and its
pre-cap total variation from $b$ is at most 0.2. These are exposure properties,
not guarantees of useful practice. D uses conditional failure under the same
support; its startup and floor/cap composition differ from R, so R$-$D compares
allocator designs rather than isolating ranking alone.''')
section(r'\begin{figure*}[t]', r'\section{Experimental Design}', r'''\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{f1_evidence_interface.pdf}
  \caption{\textbf{Admission, allocation and policy utility are separate tests.}
  The screen supplies model-relative support; the temporal interface enforces legal
  reference access; independent evaluation measures the resulting policy. The tested
  outcome-to-allocation feedback changed exposure but did not establish the registered
  tracking benefit. Neither screen qualification nor exact support implies hardware
  feasibility. Repair is a separate, target-changing route.}
  \label{fig:interface}
\end{figure*}''')
text = text.replace('E4 separately isolates the exact-support allocator.',
                    'the later four-arm study separately compares exact-support allocators.')
section(r'\subsection{E4: feasibility-gated allocation ablation}', r'\section{Results}', r'''\subsection{Four-arm allocation on unchanged exact support}
An earlier two-arm E4 protocol selected absolute-progress settings using allocation-only
calibration. Its long-run manipulation check subsequently failed, leaving policy endpoints
closed. A separate prospective confirmation retained A as a declared comparator and added
relative progress R and conditional failure D alongside uniform U.

The completed study uses seeds 21, 22 and 23, 512 environments, 4,000 PPO iterations and
24 rollout steps: 49,152,000 simulator transitions per policy. Support, learner, rewards
and reference targets are common. All twelve training gates passed before any held-out
cell opened. Checkpoints 1000, 2000, 3000 and 3999 give 48 evaluation cells on 100 unchanged
held-out clips, including 25 feasible-hard clips selected from reference features. Each cell
contains 2,800 conditions, evaluated over uninterrupted windows of up to three seconds.

The primary score is liveness-weighted reference tracking:
\begin{equation}
h\exp\!\left(-\frac{\mathrm{MPKPE}}{0.30\,\mathrm{m}}
             -\frac{\mathrm{anchor\ error}}{0.40\,\mathrm{rad}}\right),
\end{equation}
where $h$ is survived-horizon fraction, MPKPE is root-relative body-position error,
and anchor error is orientation error. We average conditions within clip, clips within
panel and paired differences across training seeds. Independent replication is the
trained seed pair, not the number of conditions.

The frozen primary decision requires final hard R$-$U mean at least $+0.02$, a positive
lower two-sided 95\% paired seed t bound (df=2), and all-panel lower bound above $-0.01$.
A pass would establish a positive effect with a target-reaching point estimate, not a
true effect of at least $+0.02$. Paired hierarchical bootstrap intervals are supplementary.
Learning curves, normalized area under the observed curve (AULC), and attainment of the
paired U final score are exploratory; non-attainment is retained. No seeds are appended
to the completed decision.''')
section('Reference continuity remains a separate diagnostic.', r'\section{Limitations}', r'''\begin{table}[t]
\centering
\caption{Repair qualification and deployment answer different questions.}
\label{tab:repair}
\begin{tabularx}{\columnwidth}{lX}
\toprule
Evidence / status & Result and scope \\
\midrule
Qualification / measured & 22/26 flagged candidates; 4/4 feasible controls byte-identical. \\
Deployment / exploratory & One policy, 26 clips, 656 paired conditions per arm: raw 0.3925,
repaired 0.3915; difference $-0.0010$, clip-bootstrap 95\% CI $[-0.0086,+0.0080]$. \\
\bottomrule
\end{tabularx}
\end{table}
The fixed-policy deployment result (Table~\ref{tab:repair}) does not establish an
aggregate gain, safety, or equivalence. It compares tracking of raw and repaired targets;
it is not a retraining effect or improved tracking of the unchanged original reference.

\subsection{Completed allocation result: inconclusive}
\label{sec:e4results}

The earlier E4 absolute-progress arm reaches mean post-warm-up TV 0.0297, below its
0.05 gate. Its disposition is \texttt{not\_tested}; it supplies no policy null.
The newer confirmation retains A under its own comparator rule. R changes exposure
in all three seeds (mean TV 0.08348/0.08249/0.08233), as does D
(0.08391/0.08587/0.08398). All twelve training runs pass their declared gates with
zero recorded invalid or censored events. Across 492 saved states, exact sampler
and checkpoint replay establishes intervention integrity.

\begin{table}[t]
\centering
\caption{Final TrackingScore differences. Three paired trained seeds;
two-sided seed t intervals, df=2.}
\label{tab:confirmation}
\begin{tabular}{lrr}
\toprule
R$-$U & Feasible-hard & All-panel \\
\midrule
Seed 21 & $-0.03400$ & $-0.04892$ \\
Seed 22 & $-0.03299$ & $-0.01402$ \\
Seed 23 & $+0.02178$ & $+0.03500$ \\
Mean & $-0.01507$ & $-0.00932$ \\
95\% lower & $-0.09436$ & $-0.11405$ \\
95\% upper & $+0.06422$ & $+0.09542$ \\
\bottomrule
\end{tabular}
\end{table}

The frozen primary result is \emph{inconclusive} (Table~\ref{tab:confirmation}). Neither
the primary rule nor the broad non-regression guard passes. Two hard-panel seeds favor U
and one favors R. The interval spans both meaningful harm and benefit; it does not establish
either, nor does failure of the guard prove regression. The supplementary paired bootstrap
hard interval is $[-0.04417,+0.02532]$ and cannot override this decision.
Descriptive final hard R$-$D is $-0.00675$ with interval $[-0.02189,+0.00840]$;
R$-$A is $-0.00668$ with interval $[-0.07243,+0.05907]$. These contrasts do not
establish equivalence or progress-specific superiority.

\begin{figure*}[t]
\centering
\includegraphics[width=\textwidth]{paired_results_and_learning_curves.pdf}
\caption{Completed allocation confirmation. Seed pairs, means and two-sided 95\% t
intervals appear at left and center. Dashed lines are the hard point-estimate target and
all-panel lower-bound margin. Thin learning curves are seeds, thick curves are means;
the cost axis is simulator transitions. Curves and attainment are exploratory.}
\label{fig:confirmation}
\end{figure*}

Exploratory normalized hard AULC R$-$U is negative in all three seeds:
$-0.03978$, $-0.03042$, $-0.01676$ (mean $-0.02898$; descriptive 95\% t interval
$[-0.05774,-0.00023]$). Two R seeds never attain their paired U final score on the
observed grid. These data do not support an efficiency-accelerator claim; sparse checkpoints
do not identify a precise crossover. The secondary interval is not a new confirmatory
harm test. Figure~\ref{fig:confirmation} reports the complete curves.

\paragraph{Earlier controls remain separate}
Table~\ref{tab:controls} separates prior protocol statuses. None is pooled with the
completed four-arm result or substituted for a matched admission on/off test.
\begin{table}[t]
\centering
\caption{Earlier controls, with their original scope and status.}
\label{tab:controls}
\begin{tabularx}{\columnwidth}{lX}
\toprule
Study / status & Bounded finding \\
\midrule
E-HYG / sealed & Whole-clip pruning: feasible-panel survival $0.918\to0.907$;
$\Delta=-0.0101$, one-sided permutation $p=0.951$. \\
Soft weighting / failed gate & Hard-rejected mass 0.199; this does not implement exact admission. \\
E4 / not tested & Mean TV 0.0297 below 0.05; policy endpoint unopened. \\
Repair-all / exploratory & Deployment contrast $+0.0397$ misses $+0.05$ target and coverage gate. \\
\bottomrule
\end{tabularx}
\end{table}
Segmentation retained 12.5 of the 20.2 minutes in 99 flagged training clips and
lost only three whole clips at zero guard. Retained duration is not demonstrated
retained skill. A matched on/off admission comparison under D is the next distinct test;
no incomplete result enters this manuscript.''')
section('The exact-support ALP sampler and its matched multi-seed protocol', r'\section{Conclusion}', r'''The allocation study has only three independent seed pairs. Its observed hard-panel
standard deviation 0.03192 yields a 95\% t half-width 0.07929, much larger than the
$+0.02$ point target. This is an observed precision limitation, not a retrospective
power guarantee or evidence of equivalence. Thousands of evaluation conditions cannot
replace independent training. The current result neither establishes benefit nor rules
out a target-sized benefit; a future replication requires its own fixed sample size.

The current simulator has knee effort clamps of approximately $\pm139$\,N\,m,
zero added command delay and plane terrain; physical G1 transfer is untested. Numerical
parity remains unresolved in a separate physical-sensitivity development check, so
its perturbation scores are not reported as evidence. A continuous adapter traverses
8.58-second training references, but comparative full-motion execution is untested.
The frozen-policy instrumentation pilot does not establish a noise floor; its planned
17.6-million-transition burn-in makes it a separate study. Practice interventions,
reliability-calibrated progress and hardware evaluation remain future work, not
explanations established by the current allocation result.''')
section(r'\section{Conclusion}', r'\bibliographystyle', r'''\section{Conclusion}
RPM makes persistent failure an ambiguous instruction for practice. The diagnosed
campaign, bank-scale screen and cross-policy difficulty transfer motivate explicit
measurement of reference admissibility. Exact temporal support then permits a controlled
allocation test: relative progress changes exposure, but the completed three-seed
comparison does not establish its registered tracking benefit. A qualified repair likewise
does not establish a fixed-policy gain. Reference qualification, exposure and control
utility therefore need separate evidence. The learning value of admission under a common
allocator remains the next direct experiment.

\section*{Reproducibility and Acknowledgments}
The stack uses mjlab v1.6.0 at commit \texttt{0fb8a681136b} and MuJoCo 3.11.0.
Motion, sidecar, unit-table, task, checkpoint, evaluator, condition and output identities
are SHA-256 bound. Licensed motion payloads cannot be redistributed; release requires
reconstruction instructions and permitted aggregate metadata. OpenAI Codex and
Anthropic Claude assisted with code, analysis tooling, figures and manuscript drafting
in Sections I--VII; claims are tied to verified artifacts, with final author review
required before submission.''')
path.write_text(text)
print('Revised title, claims, repair scope, completed results and limitations')
