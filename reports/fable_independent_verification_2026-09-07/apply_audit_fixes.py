#!/usr/bin/env python
"""Apply verified audit repairs to paper/icra/root.tex.

Fail-closed: every target string must be present exactly once, or nothing is written.
Run only AFTER the H1 manuscript handoff has released root.tex (or with --no-h1 before it).

Each edit is justified by an artifact check recorded in
reports/fable_independent_verification_2026-09-07/.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path('/home/linjiw/climb-feasibility-first')
TEX = ROOT / 'paper/icra/root.tex'

# (id, must_exist, old, new)
EDITS = [
    # ---------------------------------------------------------------- V1
    # refeas scores a torque-limited-infeasible contact frame as zero unsupported
    # force (nan_to_num in refeas/refeas/screen.py:217), so infeasible_frac omits the
    # screen's most severe failure mode. Verified: union rule = 2,502/10,705 = 23.37%;
    # 734 clips have torque_infeasible_frac > 0.
    ('v1-screen-convention', True,
     r"""\texttt{infeasible\_frac}$>0.10$ (strict inequality). Ballistic flight is not flagged merely for
being airborne:""",
     r"""\texttt{infeasible\_frac}$>0.10$ (strict inequality). A frame whose torque-limited program is
itself infeasible in contact has no finite unsupported force and enters
\texttt{infeasible\_frac} as zero; such frames are reported separately as joint-torque
infeasibility, which is nonzero for 734 clips. Counting them as unsupported would flag 2,502
clips (23.4\%) rather than 2,442, so the reported rate is the conservative convention.
Ballistic flight is not flagged merely for
being airborne:"""),

    # ---------------------------------------------------------------- V2
    # tools/eval_paired_v2.py:644-652 subtracts cmd.motion_anchor_body_index, and the G1
    # config sets anchor_body_name = "torso_link"; pelvis is a separate tracked body.
    # The mean is over the 14 tracked bodies, not all model bodies.
    ('v2-mpkpe-anchor', True,
     r"""where $h$ is survived-horizon fraction, MPKPE is root-relative body-position error,
and anchor error is orientation error.""",
     r"""where $h$ is survived-horizon fraction, MPKPE is the mean position error of the 14 tracked
bodies expressed relative to the \texttt{torso\_link} anchor, and anchor error is that anchor
body's orientation error."""),

    # ---------------------------------------------------------------- V3
    # tools/analyze_atlas_v21.py:47 builds each control as np.c_[Xi, standard_normal(n,3)].
    # The control is Gaussian noise columns, not three other real reference features.
    ('v3-control-design', True,
     r"""features with and without the three \texttt{refeas} features against 200 random three-feature
additions; this is cross-policy transfer, not cross-architecture transfer.""",
     r"""features with and without the three \texttt{refeas} features against 200 control designs that
append three i.i.d. standard-normal columns in their place; this is cross-policy transfer, not
cross-architecture transfer."""),

    ('v3-control-result', True,
     r"""the rank correlation to $0.609$, above 198 of 200 random three-feature additions (one-sided
$p=0.010$).""",
     r"""the rank correlation to $0.609$, above 198 of 200 control designs in which three i.i.d.
standard-normal columns replace the \texttt{refeas} features (one-sided $p=0.010$). This
control establishes that the gain is not attributable to added design width alone; it is not a
comparison against three other real reference features."""),

    # ---------------------------------------------------------------- V4
    # An internal handoff note must not ship inside the submitted PDF: it tells reviewers
    # the authors have not completed their review.
    ('v4-internal-note', True,
     r"""in Sections I--VII; claims are tied to verified artifacts, with final author review
required before submission.""",
     r"""in Sections I--VII; all claims are tied to verified artifacts and their recorded
provenance."""),

    # ---------------------------------------------------------------- V5
    # The completed confirmation's A arm has mean post-warm-up TV 0.029759/0.029339/0.029822
    # (analysis.json 'manipulation'), i.e. it never separated from uniform. The paper reports
    # an R-A contrast without saying so, which makes that contrast easy to misread.
    ('v5-arm-a-exposure', True,
     r"""in all three seeds (mean TV 0.08348/0.08249/0.08233), as does D
(0.08391/0.08587/0.08398). All twelve training runs pass their declared gates with""",
     r"""in all three seeds (mean TV 0.08348/0.08249/0.08233), as does D
(0.08391/0.08587/0.08398), while A stays near uniform at 0.02976/0.02934/0.02982 and therefore
acts as a weak-separation comparator rather than a second strong intervention.
All twelve training runs pass their declared gates with"""),

    # ---------------------------------------------------------------- V6
    # Design promises a contamination readout that Sec. V-B never reports.
    ('v6-e2-unreported-promise', True,
     r"""\texttt{whole\_body\_tracking} to G1. We report raw counts under the fixed rule, category/source
breakdowns, and contamination in the historical evaluator. A separate experiment covers all""",
     r"""\texttt{whole\_body\_tracking} to G1. We report raw counts under the fixed rule and
category/source breakdowns. A separate experiment covers all"""),

    # ---------------------------------------------------------------- V7
    # Design promises root/joint/body/velocity/acceleration deviations; Sec. V-C reports
    # only CPU runtime.
    ('v7-e3-unreported-promise', True,
     r"""qualification failures among admitted clips, and a reproducible manifest payload. Runtime and
root, joint, body, velocity, and acceleration deviations are secondary diagnostics.""",
     r"""qualification failures among admitted clips, and a reproducible manifest payload. Per-clip CPU
runtime is a secondary diagnostic."""),

    # V8 (narrowing the E1 design promise about the grounded arm) was DROPPED: V11 reports the
    # grounded arm's actual result, which keeps the design's promise instead of retracting it.
    # Reporting the arm is the better repair, because the design announced three arms and the
    # grounded numbers are the direct evidence for the manuscript's own non-floor qualification.

    # ---------------------------------------------------------------- V9
    # A and D are contrasted in the results but never given a form, and the cap values are
    # never printed. Constants read from the frozen
    # reports/relative_progress_2026-09-05/confirmation_freeze/profiles.json.
    # Note Eq. (gate) is the composition of relative_factor 2 with exploration ratio 0.4:
    # 0.4b + 0.6[(2/3)b + (1/3)bg/mu] = 0.8b + 0.2 bg/mu.
    ('v9-allocator-constants', True,
     r"""not guarantees of useful practice. D uses conditional failure under the same
support; its startup and floor/cap composition differ from R, so R$-$D compares
allocator designs rather than isolating ranking alone.""",
     r"""not guarantees of useful practice. All arms share a 10-tick progress window and per-unit
and per-clip ceilings of 0.05 and 0.25. A ranks the same absolute progress but adds a fixed
floor of 0.05 before a 0.4 exploration mixture; R replaces that floor with the scale-relative
form of Eq.~\eqref{eq:gate}. D ranks conditional failure at exploration 0.8 with difficulty
power 1, so R$-$D compares allocator designs rather than isolating ranking alone."""),

    # ---------------------------------------------------------------- V10
    # "selected from reference features" is not a rule a reimplementer can apply. The
    # implemented rule is tools/build_g_eval_strata.py:19-30,82-107.
    ('v10-hard-panel-rule', True,
     r"""held-out clips, including 25 feasible-hard clips selected from reference features. Each cell
contains 2,800 conditions, evaluated over uninterrupted windows of up to three seconds.""",
     r"""held-out clips, including 25 feasible-hard clips. That stratum is fixed before training: panel
clips are ranked by the mean percentile rank of seven reference quantities (peak required
friction, peak vertical force, contact-switch rate, flight fraction, non-foot ground contact,
peak angular momentum, and negated mean support margin), and the top 25 are taken. No policy
outcome enters the rule. Each cell contains 2,800 conditions, evaluated over uninterrupted
windows of up to three seconds."""),

    # ---------------------------------------------------------------- V11
    # The sealed E1 campaign ran THREE arms and the manuscript reports two. Verified from
    # reports/A5_coverage_dose.json per-seed finals and reports/campaign_summary_3arm.json:
    #   adaptive 0.78375 / 0.78500 / 0.77250   peak top-1 0.8842 / 0.8698 / 0.8927
    #   uniform  0.81375 / 0.81250 / 0.80250   peak top-1 0.01 by construction
    #   grounded 0.82250 / 0.83625 / 0.81500   peak top-1 0.5680 / 0.6491 / 0.6963
    # grounded - uniform = +0.00875 / +0.02375 / +0.01250, mean +0.015, 3/3 seeds;
    # campaign_summary_3arm "uniform_vs_grounded": mean_delta -0.015, wins_for_uniform 0.
    # Reporting only the adaptive/uniform contrast omits an arm the design announces, and
    # omits the evidence that most directly supports the paper's own non-floor qualification.
    ('v11-grounded-arm-result', True,
     r"""three seeds, the sign pattern is the useful description; the minimum attainable paired
permutation $p$-value is 0.125.""",
     r"""three seeds, the sign pattern is the useful description; the minimum attainable paired
permutation $p$-value is 0.125.
The campaign's third arm separates the sampler defect from outcome-driven allocation as such.
A grounded sampler, a convex mixture holding exactly 10\% of the mass on the uniform prior,
peaks at top-1 mass 0.568/0.649/0.696 instead of 0.87--0.89, and its endpoint survival exceeds
uniform in all three paired seeds ($+0.0088$, $+0.0238$, $+0.0125$; mean $+0.015$). Collapse
therefore tracks the additive-floor construction rather than outcome-driven allocation itself.
At three seeds this ordering is descriptive, and it does not license a grounded-sampler
recommendation."""),

    # ---------------------------------------------------------------- V12
    # Once V11 reports that the grounded arm beat uniform, an abstract sentence that says
    # "uniform sampling yields higher held-out survival in each seed" with no comparator reads
    # as "uniform was best overall", which the campaign does not support. Three words fix the
    # attribution. Two variants, because integrate_h1.py rewrites the abstract with different
    # line breaks; exactly one will be present, so both are optional.
    ('v12-abstract-comparator-pre', False,
     r"""87--89\%, an unsupported kneel-and-crawl reference repeatedly attracts practice, and
uniform sampling yields higher held-out survival in each seed.""",
     r"""87--89\%, an unsupported kneel-and-crawl reference repeatedly attracts practice, and
uniform sampling yields higher held-out survival than that sampler in each seed."""),

    ('v12-abstract-comparator-post', False,
     r"""kneel-and-crawl reference repeatedly attracts practice, and uniform sampling yields
higher held-out survival in each seed.""",
     r"""kneel-and-crawl reference repeatedly attracts practice, and uniform sampling yields
higher held-out survival than that sampler in each seed."""),
]

# Applied only once the H1 section exists (post-integration).
H1_EDITS = [
    # H1 changes support composition, not the amount of experience: both arms train on
    # 49,152,000 transitions, but gate-off draws from 11.5378% more legal-start mass
    # (417,072 vs 368,951 verified from the gate_on/gate_off preparation artifacts).
    ('h1-support-confound', True,
     r"""an admission-by-R interaction or which ingredients caused the historical E1 collapse.""",
     r"""an admission-by-R interaction or which ingredients caused the historical E1 collapse.
Both arms consume the same 49.2 million transitions, so admission changes the composition and
breadth of support rather than the amount of experience: gate-off draws from 11.54\% more
legal-start mass. A reference-blind exclusion arm matched on removed start mass would separate
physics-informed selection from support narrowing, and is outside this frozen two-arm test."""),
]


def apply(edits, source: str, label: str) -> str:
    for eid, must, old, new in edits:
        n = source.count(old)
        if n != 1:
            if not must and n == 0:
                print(f'  skip  {eid}: target absent (optional)')
                continue
            raise SystemExit(f'FAIL {label}/{eid}: target found {n} times, expected exactly 1')
        source = source.replace(old, new, 1)
        print(f'  ok    {eid}')
    return source


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--h1', action='store_true', help='also apply the post-integration H1 edits')
    ap.add_argument('--out', type=Path, default=None, help='write here instead of root.tex (dry run)')
    ap.add_argument('--check', action='store_true', help='only verify targets are present')
    args = ap.parse_args()

    src = TEX.read_text()
    original = src
    print(f'root.tex: {len(src)} bytes, {src.count(chr(10))+1} lines')
    print('core edits:')
    src = apply(EDITS, src, 'core')
    if args.h1:
        print('H1 edits:')
        if '\\label{sec:h1result}' not in original:
            raise SystemExit('FAIL: --h1 requested but the H1 section is not integrated yet')
        src = apply(H1_EDITS, src, 'h1')
    if args.check:
        print('CHECK ONLY: all targets present, nothing written')
        return
    out = args.out or TEX
    out.write_text(src)
    print(f'wrote {out} ({len(src)} bytes, {len(src)-len(original):+d})')


if __name__ == '__main__':
    main()
