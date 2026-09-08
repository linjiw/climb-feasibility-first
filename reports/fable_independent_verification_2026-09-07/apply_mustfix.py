#!/usr/bin/env python
"""Second repair pass: the MUST FIX items from the adversarial audit synthesis.

Every number below was independently recomputed from the named artifact before being written.
Fail-closed: each target must appear exactly once or nothing is written.
"""
from __future__ import annotations
import argparse
from pathlib import Path

TEX = Path('/home/linjiw/climb-feasibility-first/paper/icra/root.tex')

EDITS = [
    # ---- M1 -------------------------------------------------------------
    # "Every trained policy has zero survival from frame zero" is contradicted by the
    # stratified artifact, and it silently compares two protocols. Verified for the true E1
    # attractor BMLmovi_Subject_64_F_MoSh_Subject_64_F_9 (499 frames @ 50 fps = 9.98 s):
    #   reports/eval_tier_mixed100_fixed.csv : 10 s whole-clip horizon, 16 episodes ->
    #       survival_rate 0.0, mean survival 2.376 s
    #   reports/N3_*_strat.csv, 3 s windows, 7 policies x 8 episodes ->
    #       offset 0 s survival 0.25/0.25/0.25/0.50/0.50/0.75/1.00  (none is zero)
    #       offset 8 s, window 1.96 s -> 1.00 for all seven
    ('m1-frame-zero-survival',
     r"""8.0--8.5\,s rise again becomes unsupported. Every trained policy has zero survival from frame
zero, while the tested late 8\,s offset survives.""",
     r"""8.0--8.5\,s rise again becomes unsupported. Under a whole-clip start with a 10\,s horizon no
trained policy survives the reference, stopping after 2.38\,s on average. Under three-second
stratified windows the picture is protocol-dependent: a frame-zero window survives in 0.25 to
1.00 of episodes across seven evaluated policies, while an 8\,s start completes the remaining
1.96\,s in all seven. We therefore report the horizon with every survival number and do not
read the late-offset result as evidence about the descent."""),

    # ---- M2 -------------------------------------------------------------
    # The 0.05 manipulation gate sits below a learning-free null for this functional form.
    # reports/fable_independent_verification_2026-09-07/noise_only_tv.json (copied from the
    # signal-quality worktree): analytical 0.0604880, finite-unit mean 0.0604043 over 2,000
    # replicates at 1,184 units, fraction above 0.05 = 1.0. The artifact's own limitation
    # forbids subtracting it from observed values, and that caveat is preserved below.
    ('m2-tv-noise-floor',
     r"""acts as a weak-separation comparator rather than a second strong intervention.""",
     r"""acts as a weak-separation comparator rather than a second strong intervention.
A learning-free reference for this functional form, with 1,184 units, equal prior mass, inactive
caps and independent Gaussian progress changes, yields mean total variation 0.0605 over 2,000
replicates and exceeds 0.05 in every replicate. Exposure change above the gate therefore records
that allocation moved, not that it tracked learning progress. The reference is an illustration
under idealized assumptions and is not subtracted from the observed values."""),

    # ---- M3 -------------------------------------------------------------
    # Recomputed from reports/dfrp_policy_validation_2026-09-05/result.json (tracking_score):
    #   all                26 clips / 656 cond  -0.001003 [-0.008588,+0.008020]
    #   qualified_repairs  22 clips / 568 cond  -0.001542 [-0.010535,+0.009050]
    #   unchanged_controls  4 clips /  88 cond  +0.001965 [-0.002501,+0.008543]
    ('m3-dfrp-denominator',
     r"""Deployment / exploratory & One policy, 26 clips, 656 paired conditions per arm: raw 0.3925,
repaired 0.3915; difference $-0.0010$, clip-bootstrap 95\% CI $[-0.0086,+0.0080]$. \\""",
     r"""Deployment / exploratory & One policy, 26 clips (22 qualified repairs plus 4 byte-identical
controls), 656 paired conditions per arm: raw 0.3925, repaired 0.3915; difference $-0.0010$,
clip-bootstrap 95\% CI $[-0.0086,+0.0080]$. On the 22 repaired clips alone the difference is
$-0.0015$ $[-0.0105,+0.0090]$, while the unchanged controls return $+0.0020$
$[-0.0025,+0.0085]$, which bounds evaluator reproducibility at twice the headline magnitude. \\"""),

    # ---- M4a ------------------------------------------------------------
    # reports/N1_gap_sensitivity.json holds two clips x three contact bands plus one
    # single-clip residual triple. No bank-wide sweep of either threshold exists in reports/.
    ('m4a-sensitivity-scope',
     r"""modeling choices. Local sensitivity checks bound the two thresholds on this bank, but a new robot
or retargeter must recalibrate them.""",
     r"""modeling choices. The sensitivity evidence is local: two clips across three contact bands and one
clip across three residual thresholds. Bank-scale sensitivity of either threshold is untested,
and a new robot or retargeter must recalibrate them."""),

    # ---- M4b ------------------------------------------------------------
    # The 3 cm ground-alignment offset is a property measured on this clip, not the bank.
    ('m4b-ground-offset-scope',
     r"""The 6\,cm band is a declared tolerance. At 3\,cm a known feasible control is flagged on 42\% of
frames because the bank carries an approximately 3\,cm ground-alignment offset.""",
     r"""The 6\,cm band is a declared tolerance. At 3\,cm a known feasible control is flagged on 42\% of
its frames because that clip's stance frames sit approximately 3\,cm above the plane, a residual
we attribute to retarget ground alignment but have not measured bank-wide."""),

    # ---- M5 -------------------------------------------------------------
    # Internally inconsistent by 2.1x. reports/feasibility_sonic/hygiene_screen.csv has 4,950
    # clips and 1,818,423 frames = 367.36 frames/clip, so 0.145 CPU-s/clip is 0.395 ms/frame,
    # not 0.84. COMPLETED.json gives wall 179.838 s on 8 workers = 0.291 CPU-s/clip
    # = 0.791 ms/frame, which is the sourced pair.
    ('m5-screen-cost',
     r"""The screen takes approximately one CPU-second per clip in the primary implementation. An
independent implementation processes the production bank at 0.145 CPU-s per clip
(0.84\,ms/frame). The screen therefore runs as an offline bank-ingestion stage rather than in the
policy control loop.""",
     r"""An independent implementation screens the 4,950-clip production bank in 179.8\,s of wall time on
eight workers, or 0.29 CPU-seconds per clip over 1,818,423 screened frames (0.79\,ms per frame).
The screen therefore runs as an offline bank-ingestion stage rather than in the policy control
loop."""),

    # ---- M6 -------------------------------------------------------------
    # "peak joint speed is at most 5.6 rad/s" has no artifact path in RESULTS_LOG.md; its only
    # source is prose in plan/G1_RESULT.md. House rule: paper-bound numbers need an artifact.
    # Taking the edit-only path and dropping the unsourced quantity.
    ('m6-unsourced-joint-speed',
     r"""The reference has no joint-limit violation and peak joint speed is at most 5.6\,rad/s. The""",
     r"""The reference violates no joint limit in the model's declared ranges. The"""),

    # ---- M7 -------------------------------------------------------------
    # The failure criterion underlies the allocator's signal, D's ranking and the evaluator's h,
    # and the -10 terminal cost is an undisclosed departure from stock mjlab rewards.
    # mjlab tracking_env_cfg.py:259-275 (0.25 m anchor height, 0.8 gravity projection, 0.25 m
    # ankle/wrist height); climb/segment_env_cfg.py:37,78-86 (failure_penalty -10, entered as
    # weight = failure_penalty/step_dt on mdp.is_terminated, upstream time_out removed).
    ('m7-failure-definition',
     r"""The runtime samples only legal starts, emits explicit truncation at a segment boundary, never""",
     r"""A trial fails when a non-timeout termination fires: anchor height error above 0.25\,m, anchor
gravity-projection error above 0.8, or height error above 0.25\,m at an ankle or a wrist.
Truncation at a segment boundary is not a failure. Every arm adds the same one-off terminal cost
of $-10$ on failure to the inherited tracking rewards.
The runtime samples only legal starts, emits explicit truncation at a segment boundary, never"""),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--out', type=Path, default=None)
    a = ap.parse_args()
    src = TEX.read_text()
    before = len(src)
    for eid, old, new in EDITS:
        n = src.count(old)
        if n != 1:
            raise SystemExit(f'FAIL {eid}: target found {n} times, expected 1')
        src = src.replace(old, new, 1)
        print(f'  ok    {eid}')
    if a.check:
        print('CHECK ONLY: all targets present, nothing written')
        return
    out = a.out or TEX
    out.write_text(src)
    print(f'wrote {out} ({len(src)} bytes, {len(src)-before:+d})')


if __name__ == '__main__':
    main()
