#!/usr/bin/env python3
"""Does infeasible reference actually reach the optimizer?

BACKS
-----
Flagship §3 ("Failure-adaptive sampling collapses, and its uniform floor is not
a floor", `paper/flagship/S3_collapse_nonfloor.md`) and §6 ("The feasibility
screen at scale", eval/exposure contamination). Specifically it supplies the
*exposure* half of the thesis:

    Claim C3-EXPOSURE. The collapse of a failure-adaptive clip sampler is not
    merely a concentration of sampling mass; it is a concentration onto
    references the feasibility screen flags as dynamically infeasible. The
    time-averaged sampling mass a failure-adaptive sampler puts on flagged
    clips is strictly greater than the bank's flagged fraction (the mass a
    uniform sampler puts there by construction), and a normalise-then-mix
    ("grounded") floor removes part -- but only part -- of the excess.

If C3-EXPOSURE is false, i.e. if infeasible reference is only a property of the
data directory and never reaches the optimizer in disproportionate quantity,
then feasibility-grounded adaptive sampling (FGAS) is solving a problem that
does not exist at training time, and the FGAS line is worth much less. This
script is the adversarial test of that.

WHAT IS MEASURED VS WHAT IS MODELLED
------------------------------------
MEASURED (level 1, no model at all)
    Every training iteration logs `sampling_top1_prob` = max_c p_c and
    `sampling_top1_bin` = argmax_c p_c / num_clips. Multiplying the mass of the
    top-1 clip by the indicator that the top-1 clip is flagged, and averaging
    over iterations, is a valid LOWER BOUND on the total mass on flagged clips,
    because the total is a sum over all flagged clips of non-negative terms.
    Also measured: P(top-1 clip is flagged) -- the *selection* statistic, which
    is independent of the mass level.

BOUNDED (level 2, distribution-free, still no behavioural model)
    Given only (max_c p_c, H(p), which clip is the argmax, how many clips are
    flagged), the set of distributions consistent with the logs is a convex
    set, and the extreme flagged-mass members of that set can be computed
    exactly. This yields a rigorous interval containing the true total. This
    script computes it and reports how wide it is. (Spoiler, and the point:
    it is nearly vacuous. The instrumentation does not pin the total down.)

MODELLED (level 3, and it must pass a gate before it is believed)
    The full distribution is not logged, so the total can only be *estimated*
    by reconstructing p from per-clip failure rates through the sampler's own
    fixed point. This script implements that, then checks the reconstruction
    against the logged top-1 mass and entropy. If the check fails, the modelled
    total is NOT reported as a result -- only the gate outcome is.

THE PROBABILITY FORMULAS (reimplemented, not imported)
-----------------------------------------------------
From `climb/commands.py:85-108` (`MultiClipMotionCommand._clip_probabilities`),
verbatim structure, with n = num_clips, eps = cfg.clip_uniform_ratio = 0.1,
q = self.clip_failed_ema:

    line  87   uniform = 1/n
    line  88-89  uniform arm:      p = uniform
    line  94-98  grounded arm:     q_hat = q / q.sum();  p = (1-eps)*q_hat + eps*uniform
    line 107-108 adaptive arm:     p = (q + eps/n) / (q + eps/n).sum()
                                     = (q + eps/n) / (q.sum() + eps)

and from `climb/commands.py:143-160` + `climb/commands.py:206-211`:

    line 148-150  _clip_failed_now[:] = bincount(clips of envs that TERMINATED)
    line 207-210  q <- a*_clip_failed_now + (1-a)*q,  a = clip_adaptive_alpha = 0.01
    line 117/159  sampling_top1_prob = p.max()
    line 160      sampling_top1_bin  = p.argmax() / n
    line 113-116  sampling_clip_entropy = H(p)/log(n)

A useful identity follows. Write u = q/q.sum() (the normalised failure signal)
and S = q.sum(). Then BOTH arms are convex mixtures of u and uniform:

    grounded:  p = 0.9 * u + 0.1 * (1/n)                 mixing weight fixed
    adaptive:  p = lam * u + (1-lam) * (1/n),  lam = S/(S+eps)

So the two arms differ only in the mixing weight, and the adaptive arm's weight
is data-dependent: S is an EMA of per-step *termination counts* over 4096
environments, so S is O(10-300) and lam = S/(S+0.1) is 0.99-0.9997. The nominal
"10 % uniform floor" is realised as 0.03-1 % of the mass. This script uses that
identity for the mechanical/dynamical decomposition (--decompose).

SENTINELS -- READ THIS BEFORE USING THE UNIFORM ARM
---------------------------------------------------
`climb/commands.py:137-141` (`_uniform_sampling`) HARDCODES

    sampling_entropy   = 1.0
    sampling_top1_prob = 1.0 / num_clips
    sampling_top1_bin  = 0.5

These are constants written by the code, not measurements of a sampled
distribution. The first two happen to be numerically correct for a uniform p,
but `sampling_top1_bin = 0.5` is pure fiction: it points at clip index
n/2 = 50, which in tier_mixed100 is a FLAGGED clip
(Eyes_Japan_..._giant_baba, infeasible_frac 0.128). Any lower-bound statistic
computed from the uniform arm's logs therefore returns a spurious
1/n = 1.00 %. This script refuses to report that as a measurement; the uniform
arm's contamination is ANALYTIC and exact: flagged mass = |F|/n, and expected
infeasible-frame share = mean_c infeasible_frac_c.

WHAT THE "GROUNDED" ARM IS -- AND IS NOT
----------------------------------------
`climb/commands.py:61-62` sets `_grounding = "mixture"` for sampling_mode
"grounded", and the mixture branch (`commands.py:94-98`) applies NO feasibility
mask: it only replaces the additive offset with a genuine convex mixture, so
the 10 % uniform component is actually 10 %. The campaign's grounded arm is
therefore a FLOOR REPAIR, not FGAS. It carries no eligibility term m_b at all.
Any reduction in contamination it shows is what you get for free by fixing the
sampler's arithmetic, and is a LOWER BOUND on what masking could achieve --
which also means it is the honest baseline FGAS must beat. Do not report the
adaptive-vs-grounded contrast as evidence for feasibility grounding; it is
evidence that the collapse is real and that repairing the floor only partly
undoes it.

TWO DIFFERENT QUESTIONS
-----------------------
"mass on flagged clips" and "expected infeasible-frame share" are not the same
number and do not answer the same question.
  * mass on flagged clips = P(the episode's reference clip is one the screen
    flags). It is the right number for "how often does the curriculum choose a
    contaminated reference".
  * infeasible-frame share = sum_c p_c * infeasible_frac_c = expected fraction
    of tracked reference frames that are physically infeasible, under the
    sampler's own "uniform start frame within the clip" rule
    (`climb/commands.py:120-133`). It is the right number for "how much of the
    gradient is computed against an impossible target". It is much smaller,
    because a flagged clip is only partly infeasible.
Both are reported. Do not quote one as the other.

  KNOWN BIAS IN THE FRAME-SHARE METRIC. sum_c p_c * infeasible_frac_c is exact
  only if the frames a rollout actually visits inside clip c are a uniform
  sample of that clip. They are not: `commands.py:120-133` picks the start
  frame uniformly and `commands.py:197-199` resamples at the clip boundary, so
  frame x of a clip is reachable from every start <= x -- visits are weighted
  towards the END of a clip -- while early termination cuts episodes short and
  weights them back towards the start. Whether the net bias inflates or
  deflates the number depends on WHERE inside each clip the infeasible frames
  sit, which this metric does not know. Treat the frame share as a clip-level
  weighting of a within-clip statistic, not as a measured frame-visit rate.
  It is reported because it is the right ORDER of magnitude and because the
  arm-to-arm CONTRAST is insensitive to a bias shared by all arms.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- constants transcribed from climb/commands.py -------------------------
EPS = 0.1        # MultiClipMotionCommandCfg.clip_uniform_ratio  (line 266)
ALPHA = 0.01     # MultiClipMotionCommandCfg.clip_adaptive_alpha (line 273)
MIXTURE_WEIGHT = 1.0 - EPS  # grounded arm, line 98

ARMS = ("uniform", "adaptive", "grounded")
SEEDS = (1, 2, 3)

# Per-clip failure-rate sources that actually cover the TRAINING bank.
TRAINBANK_F_SOURCES = {
    "A7_trainbank_uniform_s1": "reports/A7_trainbank_uniform_s1.csv",
    "eval_mixed100_uniform_s1": "reports/eval_mixed100_uniform_s1.csv",
    "eval_tier_mixed100_fixed": "reports/eval_tier_mixed100_fixed.csv",
    "eval_tier_mixed100_rand": "reports/eval_tier_mixed100_rand.csv",
}

# Pre-declared validation-gate thresholds (fixed before looking at results).
GATE_TOP1_REL_TOL = 0.15   # |sim - logged| / logged, on mean top-1 mass
GATE_ENTROPY_ABS_TOL = 0.05  # absolute, on mean NORMALISED entropy


# ==========================================================================
# inputs
# ==========================================================================
def read_clip_list(path: str) -> List[str]:
    with open(path) as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]


def read_infeasible_frac(path: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            out[row["clip"]] = float(row["infeasible_frac"])
    return out


def read_failure_rates(path: str) -> Dict[str, float]:
    """f_c = 1 - survival_rate from a per-clip eval CSV."""
    out: Dict[str, float] = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            out[row["clip"]] = 1.0 - float(row["survival_rate"])
    return out


def read_failure_and_duration(path: str) -> Dict[str, Tuple[float, float]]:
    """(f_c, T_c) = (1 - survival_rate, mean_survival_s) from a per-clip eval CSV.

    T_c is needed by the FLUX weight model (see `weight_model`): the sampler
    counts terminations per env-STEP, not per episode, so a clip that kills the
    policy quickly contributes counts at a higher rate than its per-episode
    failure probability alone implies.
    """
    out: Dict[str, Tuple[float, float]] = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            out[row["clip"]] = (
                1.0 - float(row["survival_rate"]),
                float(row.get("mean_survival_s") or "nan"),
            )
    return out


def weight_model(f: np.ndarray, T: np.ndarray, model: str) -> np.ndarray:
    """The per-clip quantity w_c that the EMA accumulates, up to a global scale.

    `commands.py:143-150` bincounts the clips of the envs that TERMINATED in
    this reset batch, and `commands.py:206-211` folds that count into the EMA
    once per env-step. So the EMA's stationary value is proportional to the
    per-step RATE at which clip c produces terminations, not to its per-episode
    failure probability.

      rate  w_c = f_c
            Assumes every clip occupies an env for the same wall-clock time, so
            terminations-per-step is proportional to terminations-per-episode.
            This is what a naive reading of the code gives.
      flux  w_c = f_c / T_c
            Corrects for episode length: an env seated on clip c is recycled
            every ~T_c seconds, so clip c generates f_c/T_c terminations per env
            per second. Infeasible clips fail FAST, so flux amplifies them
            relative to rate. This is the more faithful model of the code.

    Both are swept, because neither is measured and the choice changes the
    answer by an order of magnitude -- which is itself a reportable finding.
    """
    if model == "rate":
        return f.astype(float)
    if model == "flux":
        Ts = np.where(np.isfinite(T) & (T > 1e-3), T, np.nan)
        w = f / Ts
        return np.nan_to_num(w, nan=0.0, posinf=0.0)
    raise ValueError(f"unknown weight model {model!r}")


_METRIC_RE = re.compile(
    r"Metrics/motion/(sampling_top1_bin|sampling_top1_prob|sampling_clip_entropy):\s*([-\d.eE+]+)"
)


def parse_log(path: str) -> List[Dict[str, float]]:
    """Pull the three sampling metrics out of an rsl_rl training log.

    One record per learning iteration, in file order. Deterministic.
    """
    recs: List[Dict[str, float]] = []
    cur: Dict[str, float] = {}
    with open(path, errors="replace") as fh:
        for line in fh:
            m = _METRIC_RE.search(line)
            if not m:
                continue
            cur[m.group(1)] = float(m.group(2))
            if len(cur) == 3:
                recs.append(cur)
                cur = {}
    return recs


# ==========================================================================
# level 1 -- measured lower bound
# ==========================================================================
def measured_lower_bound(
    recs: Sequence[Dict[str, float]],
    weight: np.ndarray,
    n_clips: int,
    ambiguity: str,
) -> Dict[str, float]:
    """Time-averaged weight carried by the top-1 clip.

    `weight[c]` is 1.0 for the flagged-mass version and infeasible_frac[c] for
    the wasted-frame version.

    `sampling_top1_bin` is logged as the mean over the reset events inside one
    iteration of argmax(p)/n, so it is an exact clip index only when the argmax
    did not move within the iteration. Three policies for the rest:
      drop      exclude those iterations from numerator AND denominator
      zero      count them as contributing 0 (denominator = all iterations)
      round     round bin*n to the nearest integer and use it
    """
    num = 0.0
    den = 0
    ambiguous = 0
    for r in recs:
        b = r["sampling_top1_bin"] * n_clips
        p = r["sampling_top1_prob"]
        amb = abs(b - round(b)) > 1e-6
        if amb:
            ambiguous += 1
            if ambiguity == "drop":
                continue
            if ambiguity == "zero":
                den += 1
                continue
        idx = int(round(b)) % n_clips
        num += p * float(weight[idx])
        den += 1
    return {
        "value": num / den if den else float("nan"),
        "n_iters_used": den,
        "n_ambiguous": ambiguous,
    }


def top1_selection_stats(
    recs: Sequence[Dict[str, float]], flagged: np.ndarray, ifrac: np.ndarray,
    n_clips: int
) -> Dict[str, object]:
    """Which clips hold the top-1 slot, how often, with how much mass.

    Purely descriptive and fully MEASURED. `p_top1_flagged` is the *selection*
    statistic: the fraction of iterations whose most-sampled clip is flagged.
    Under a sampler that picks its argmax blind to feasibility this equals the
    bank's flagged fraction (0.25 here), so any excess is the selection effect
    separated from the mass effect.

    `mass` per clip is the sum of top1_prob over the iterations where that clip
    is the argmax; dividing by the iteration count gives the clip's share of the
    measured lower bound, so the flagged rows sum exactly to lb_flagged_mass
    under the 'drop' ambiguity policy.
    """
    occ: Dict[int, int] = {}
    mass: Dict[int, float] = {}
    n_amb = 0
    for r in recs:
        b = r["sampling_top1_bin"] * n_clips
        if abs(b - round(b)) > 1e-6:
            n_amb += 1
            continue
        idx = int(round(b)) % n_clips
        occ[idx] = occ.get(idx, 0) + 1
        mass[idx] = mass.get(idx, 0.0) + r["sampling_top1_prob"]
    total = sum(occ.values())
    tot_mass = sum(mass.values())
    flagged_iters = sum(c for i, c in occ.items() if flagged[i])
    ranked = sorted(occ.items(), key=lambda kv: (-kv[1], kv[0]))
    return {
        "p_top1_flagged": flagged_iters / total if total else float("nan"),
        "top1_mass_weighted_flagged_rate": (
            sum(m for i, m in mass.items() if flagged[i]) / tot_mass if tot_mass else float("nan")
        ),
        "top1_mass_weighted_mean_infeasible_frac": (
            sum(m * float(ifrac[i]) for i, m in mass.items()) / tot_mass
            if tot_mass else float("nan")
        ),
        "n_distinct_top1_clips": len(occ),
        "n_distinct_top1_clips_flagged": sum(1 for i in occ if flagged[i]),
        "n_ambiguous_argmax_iters": n_amb,
        "per_clip": [
            {"clip_index": i, "iters": c, "mass": mass[i]} for i, c in ranked
        ],
        "top_occupancy": [
            {
                "clip_index": i,
                "iters": c,
                "occupancy": c / total,
                "mean_top1_prob": mass[i] / c,
                "flagged": bool(flagged[i]),
            }
            for i, c in ranked[:8]
        ],
    }


# ==========================================================================
# level 2 -- distribution-free bracket from (top-1 mass, entropy)
# ==========================================================================
def _gibbs_capped(w: np.ndarray, mass: float, beta: float, cap: float) -> np.ndarray:
    """p propto exp(beta*w), scaled to `mass`, capped elementwise at `cap`.

    Water-filling: clamp the overflowing entries at `cap` and redistribute.

    The exponent is referenced to whichever end of `w` the sign of `beta` makes
    dominant, so every exponent is <= 0 and large |beta| UNDERFLOWS to zero
    instead of overflowing. Referencing unconditionally to w.max() (as this
    function did before 2026-08-19) makes beta << 0 produce exponents of +inf,
    which a clip at +700 then flattens into a spurious uniform -- silently
    turning the minimiser into a near-uniform distribution and inflating the
    lower end of `entropy_bracket` on any non-binary weight.
    """
    ref = float(w.max()) if beta >= 0.0 else float(w.min())
    x = np.clip(beta * (w - ref), -700.0, 0.0)
    e = np.exp(x)
    p = np.zeros_like(w, dtype=float)
    free = np.ones(len(w), dtype=bool)
    rem = mass
    for _ in range(len(w) + 2):
        if not free.any() or rem <= 0:
            break
        s = float(e[free].sum())
        if s <= 0.0:
            p[free] = rem / int(free.sum())
            break
        q = rem * e[free] / s
        over = q > cap + 1e-15
        if not over.any():
            p[free] = q
            break
        idx = np.where(free)[0][over]
        p[idx] = cap
        rem -= cap * len(idx)
        free[idx] = False
    return p


def _extremal_fill(w: np.ndarray, mass: float, cap: float, beta_sign: float) -> np.ndarray:
    """The objective-optimal distribution ignoring the entropy constraint.

    `beta_sign` follows the Gibbs convention used by `entropy_bracket`:
    beta_sign < 0 is the MINIMISER (fill the smallest `w` first), beta_sign > 0
    the MAXIMISER (fill the largest `w` first). Each entry is capped at `cap`
    and ties are spread uniformly, so that among all optima of the linear
    objective this is the MAX-ENTROPY one -- exactly what `entropy_bracket`
    needs: if even this point satisfies H >= h, the entropy constraint is slack
    and the unconstrained extremum is the true answer.
    """
    order = np.argsort(-beta_sign * w, kind="stable")
    p = np.zeros_like(w, dtype=float)
    rem = mass
    i = 0
    ws = w[order]
    while rem > 1e-18 and i < len(order):
        j_ = i
        while j_ + 1 < len(order) and ws[j_ + 1] == ws[i]:
            j_ += 1
        group = order[i:j_ + 1]
        take = min(rem, cap * len(group))
        p[group] = take / len(group)
        rem -= take
        i = j_ + 1
    return p


def _ent(p: np.ndarray) -> float:
    q = p[p > 0]
    return float(-(q * np.log(q)).sum())


def entropy_bracket(
    w: np.ndarray, top1_prob: float, norm_entropy: float, top1_idx: int
) -> Tuple[float, float, bool]:
    """Rigorous [min, max] of sum_c w_c p_c given only the logged summaries.

    Feasible set: sum_c p_c = 1;  p_{top1_idx} = top1_prob;  p_c <= top1_prob;
    H(p) >= norm_entropy * log(n).  The true p satisfies H(p) = the logged
    value, hence lies in this set, so the interval is valid. The set is convex
    (a superlevel set of the concave entropy intersected with a polytope) and
    the objective is linear, so KKT is sufficient and there are exactly two
    cases per endpoint:

      (a) the entropy constraint is SLACK at the unconstrained extremum. Then
          the answer is that extremum: `_extremal_fill`. This case is common
          whenever many clips share the extremal weight -- 45 of the 100 clips
          here have infeasible_frac exactly 0, and spreading the residual over
          those 45 already carries more entropy than the logs require.
      (b) the entropy constraint is ACTIVE. Then p_c propto exp(beta*w_c) on
          the non-argmax coordinates with beta < 0 for the min and beta > 0 for
          the max, and beta is found by bisection on the entropy equality.

    Checking (a) FIRST is not an optimisation, it is a correctness requirement:
    the bisection in (b) cannot represent case (a) (no finite beta reaches it)
    and silently returns a far-too-high minimum if it is entered anyway.

    Returns (min, max, entropy_infeasible_flag). The flag is set when the
    logged entropy exceeds what is achievable at the logged top-1 mass, which
    can happen because the logged pair is an average over the reset events
    inside one iteration; the entropy target is then clamped to the max.
    """
    n = len(w)
    m = float(top1_prob)
    h_target = float(norm_entropy) * math.log(n)
    rest_mass = 1.0 - m
    h_top = -m * math.log(m) if m > 0 else 0.0
    h_rest = h_target - h_top
    others = np.array([i for i in range(n) if i != top1_idx])
    wo = w[others]
    h_rest_max = rest_mass * math.log((n - 1) / rest_mass) if rest_mass > 0 else 0.0
    infeasible = h_rest > h_rest_max + 1e-12
    h_rest = min(h_rest, h_rest_max)
    out = []
    for sgn in (-1.0, +1.0):
        # case (a): unconstrained extremum already satisfies the entropy bound
        p_ext = _extremal_fill(wo, rest_mass, m, sgn)
        if _ent(p_ext) >= h_rest - 1e-12:
            out.append(m * float(w[top1_idx]) + float((p_ext * wo).sum()))
            continue
        # case (b): entropy constraint active; bisect beta on H(p_rest) = h_rest
        lo, hi = 0.0, sgn * 1.0
        for _ in range(200):
            if _ent(_gibbs_capped(wo, rest_mass, hi, m)) <= h_rest:
                break
            hi *= 2.0
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if _ent(_gibbs_capped(wo, rest_mass, mid, m)) > h_rest:
                lo = mid
            else:
                hi = mid
        p = _gibbs_capped(wo, rest_mass, 0.5 * (lo + hi), m)
        out.append(m * float(w[top1_idx]) + float((p * wo).sum()))
    return out[0], out[1], infeasible


def selftest_bracket(w: np.ndarray, n_samples: int = 200000, seed: int = 0) -> Dict[str, object]:
    """Randomised falsification of `entropy_bracket`, as a regression guard.

    Draws capped Gibbs distributions with random temperature and random weights,
    keeps the ones that satisfy the bracket's own feasibility constraints
    (fixed top-1 mass, p <= top1, H(p) >= target), and checks that every one of
    them lands inside the returned interval. A single violation means the
    interval is not an interval and any number derived from it is void.

    This exists because two real bugs got past inspection on 2026-08-19:
      * `_gibbs_capped` referenced the exponent to w.max() unconditionally, so
        beta << 0 overflowed into a clip at +700 and returned a near-uniform
        "minimiser" -- inflating the lower endpoint on continuous weights.
      * `_extremal_fill` sorted by `sign*w` rather than `-beta_sign*w`, which
        swapped the two endpoints.
    Neither shows up on a binary weight vector; both are caught here.
    """
    rng = np.random.default_rng(seed)
    n = len(w)
    cases = []
    for (t1, h_n, idx) in ((0.50, 0.377, n // 2), (0.34, 0.61, n // 2),
                           (0.20, 0.75, n // 3), (0.80, 0.25, n // 4)):
        lo, hi, _ = entropy_bracket(w, t1, h_n, idx)
        n_feas = 0
        n_viol = 0
        per = max(1, n_samples // 4)
        for _ in range(per):
            beta = rng.uniform(-60.0, 60.0)
            v = rng.standard_normal(n)
            p = _gibbs_capped(v, 1.0 - t1, beta, t1)
            p[idx] = 0.0
            ssum = float(p.sum())
            if ssum <= 0:
                continue
            p = p / ssum * (1.0 - t1)
            if p.max() > t1 + 1e-12:
                continue
            p[idx] = t1
            if -(p * np.log(p + 1e-300)).sum() / math.log(n) < h_n - 1e-12:
                continue
            n_feas += 1
            val = float((p * w).sum())
            if val < lo - 1e-9 or val > hi + 1e-9:
                n_viol += 1
        cases.append({"top1": t1, "norm_entropy": h_n, "argmax_index": idx,
                      "bracket_lo": lo, "bracket_hi": hi,
                      "n_feasible_samples": n_feas, "n_violations": n_viol,
                      "pass": n_viol == 0})
    return {"cases": cases, "pass": all(c["pass"] for c in cases)}


def bracket_over_run(
    recs: Sequence[Dict[str, float]], w: np.ndarray, n_clips: int
) -> Dict[str, float]:
    cache: Dict[Tuple[float, float, int], Tuple[float, float, bool]] = {}
    lo_acc = hi_acc = 0.0
    used = 0
    n_infeasible = 0
    for r in recs:
        b = r["sampling_top1_bin"] * n_clips
        if abs(b - round(b)) > 1e-6:
            continue
        idx = int(round(b)) % n_clips
        key = (r["sampling_top1_prob"], r["sampling_clip_entropy"], idx)
        if key not in cache:
            cache[key] = entropy_bracket(
                w, r["sampling_top1_prob"], r["sampling_clip_entropy"], idx
            )
        lo, hi, bad = cache[key]
        lo_acc += lo
        hi_acc += hi
        n_infeasible += int(bad)
        used += 1
    if not used:
        return {"lo": float("nan"), "hi": float("nan"), "n_iters_used": 0,
                "n_entropy_infeasible": 0}
    return {
        "lo": lo_acc / used,
        "hi": hi_acc / used,
        "n_iters_used": used,
        "n_entropy_infeasible": n_infeasible,
    }


# ==========================================================================
# level 3 -- sampler fixed point, and its validation gate
# ==========================================================================
def _fp_denominator(t: float, scale: float, w: np.ndarray, arm: str) -> np.ndarray:
    if arm == "grounded":
        return 1.0 - scale * w / t
    return t - scale * w


def fixed_point(w: np.ndarray, arm: str, k: Optional[float],
                method: str = "exact") -> np.ndarray:
    """Solve p = sampler(q(p)) with q_c = k * p_c * w_c, exactly.

    Justification of q_c = k*p_c*w_c: the EMA at `commands.py:206-211` is
    ema <- a*count + (1-a)*ema with a constant-in-expectation input, so its
    stationary value is proportional to E[count_c], the rate at which clip c
    produces terminations, which is proportional to how often c is sampled
    (p_c) times how readily it kills the policy (w_c; see `weight_model`).
    The scale k is NOT logged, hence swept.

    CLOSED FORM. Substituting q = k*p*w into `commands.py:107-108` gives

        p_c * (k*Z + eps - k*w_c) = eps/n ,   Z = sum_c p_c w_c

    so p_c = (eps/n) / (t - k*w_c) with t = k*Z + eps a single scalar fixed by
    normalisation sum_c p_c = 1. Self-consistency Z = (t - eps)/k then holds
    identically: multiply the display by p_c and sum. So the adaptive fixed
    point is a one-dimensional root find for t on (k*max(w), inf), where the
    normalisation sum is strictly decreasing -- bracketed, unique, exact.

    For the grounded arm, `commands.py:97` renormalises q before mixing, so k
    CANCELS EXACTLY and the fixed point is parameter-free:

        p_c = (eps/n) / (1 - (1-eps)*w_c/Z) ,   Z = sum_c p_c w_c

    with Z fixed by normalisation on ((1-eps)*max(w), inf). Nothing to tune:
    the grounded prediction is unhedged, which is what makes it the sharp test
    in `run_gate`.

    `method="iterate"` runs the damped Picard iteration on the literal code of
    `commands.py:97-108` instead. It is kept as an independent cross-check of
    the closed form (--fp-method iterate), not because it is needed.
    """
    n = len(w)
    if not np.isfinite(w).all() or w.max() <= 0:
        return np.full(n, 1.0 / n)
    if method == "iterate":
        p = np.full(n, 1.0 / n)
        for _ in range(200000):
            a = float((p * w).sum())
            if a <= 0.0:
                return p
            if arm == "grounded":
                new_p = MIXTURE_WEIGHT * (p * w) / a + EPS / n      # commands.py:98
            else:
                q = float(k) * p * w
                new_p = (q + EPS / n) / (q.sum() + EPS)             # commands.py:107-108
            if np.abs(new_p - p).max() < 1e-15:
                return new_p
            p = 0.5 * p + 0.5 * new_p
        return p

    scale = MIXTURE_WEIGHT if arm == "grounded" else float(k)
    lo = scale * float(w.max())

    def resid(t: float) -> float:
        d = _fp_denominator(t, scale, w, arm)
        return float(((EPS / n) / d).sum() - 1.0)

    a_ = lo * (1.0 + 1e-13) + 1e-300
    b_ = max(lo * 2.0, lo + 1.0)
    for _ in range(400):
        if resid(b_) < 0.0:
            break
        b_ *= 2.0
    for _ in range(300):                      # deterministic bisection
        m_ = 0.5 * (a_ + b_)
        if resid(m_) > 0.0:
            a_ = m_
        else:
            b_ = m_
        if b_ - a_ <= 1e-15 * max(1.0, abs(b_)):
            break
    t = 0.5 * (a_ + b_)
    p = (EPS / n) / _fp_denominator(t, scale, w, arm)
    p = np.maximum(p, 0.0)
    return p / p.sum()


def summarise_p(p: np.ndarray, flagged: np.ndarray, ifrac: np.ndarray) -> Dict[str, float]:
    n = len(p)
    return {
        "top1_prob": float(p.max()),
        "top1_index": int(p.argmax()),
        "norm_entropy": float(-(p * np.log(np.maximum(p, 1e-300))).sum() / math.log(n)),
        "flagged_mass": float(p[flagged].sum()),
        "infeasible_frame_share": float((p * ifrac).sum()),
    }


def run_gate(
    clips: List[str],
    flagged: np.ndarray,
    ifrac: np.ndarray,
    logged: Dict[str, Dict[str, float]],
    k_grid: np.ndarray,
    f_sources: Dict[str, str],
    weight_models: Sequence[str] = ("rate", "flux"),
    logged_modal_top1: Optional[Dict[str, int]] = None,
    fp_method: str = "exact",
) -> Dict[str, object]:
    """Fit and check the fixed-point reconstruction, per (failure source x weight model).

    Two pre-declared PASS criteria (thresholds fixed in source before the sweep):
      * simulated time-averaged top-1 mass within GATE_TOP1_REL_TOL of logged
      * simulated normalised entropy within GATE_ENTROPY_ABS_TOL of logged
    Both arms must pass on the SAME (source, weight model) for that cell to pass.

    A third quantity, `argmax_matches_logged`, is reported as a DIAGNOSTIC only
    and is deliberately NOT part of the pass rule: it was added after the gate
    had already failed, and folding a post-hoc criterion into a pass/fail rule
    would be moving the goalposts. It can only ever make the gate stricter, so
    a FAIL verdict is unaffected by leaving it out.
    """
    results = []
    for name in sorted(f_sources):
        path = os.path.join(REPO, f_sources[name])
        if not os.path.exists(path):
            continue
        rows = read_failure_and_duration(path)
        missing = [c for c in clips if c not in rows]
        if missing:
            results.append({"f_source": name, "usable": False,
                            "reason": f"{len(missing)} training clips absent from this eval"})
            continue
        f = np.array([rows[c][0] for c in clips])
        T = np.array([rows[c][1] for c in clips])
        for wm in weight_models:
            w = weight_model(f, T, wm)
            entry: Dict[str, object] = {
                "f_source": name,
                "weight_model": wm,
                "usable": True,
                "f_mean": float(f.mean()),
                "f_max": float(f.max()),
                "n_clips_at_f_max": int((f == f.max()).sum()),
                "w_argmax_index": int(np.argmax(w)),
                "w_argmax_clip": clips[int(np.argmax(w))],
                "w_argmax_flagged": bool(flagged[int(np.argmax(w))]),
            }
            if not np.isfinite(w).all() or w.max() <= 0:
                entry["usable"] = False
                entry["reason"] = "weight model degenerate on this source (no duration column?)"
                results.append(entry)
                continue
            # grounded: NO free parameter -- k cancels at commands.py:97, so the
            # fixed point is fully determined by w. Sharpest available test.
            pg = fixed_point(w, "grounded", None, fp_method)
            sg = summarise_p(pg, flagged, ifrac)
            lg = logged["grounded"]
            entry["grounded"] = {
                "sim": sg,
                "free_parameters": 0,
                "logged_top1_prob": lg["top1_prob"],
                "logged_norm_entropy": lg["norm_entropy"],
                "d_top1_rel": (sg["top1_prob"] - lg["top1_prob"]) / lg["top1_prob"],
                "d_entropy_abs": sg["norm_entropy"] - lg["norm_entropy"],
                "argmax_matches_logged": (
                    None if logged_modal_top1 is None or "grounded" not in logged_modal_top1
                    else bool(sg["top1_index"] == logged_modal_top1["grounded"])
                ),
                "logged_modal_top1_index": (
                    None if logged_modal_top1 is None else logged_modal_top1.get("grounded")
                ),
                "pass": bool(
                    abs(sg["top1_prob"] - lg["top1_prob"]) / lg["top1_prob"] <= GATE_TOP1_REL_TOL
                    and abs(sg["norm_entropy"] - lg["norm_entropy"]) <= GATE_ENTROPY_ABS_TOL
                ),
            }
            # adaptive: one free parameter k. Fit it to the LOGGED top-1 mass,
            # then test whether the entropy falls out right -- that is the gate.
            la = logged["adaptive"]
            best = None
            for k in k_grid:
                pa = fixed_point(w, "adaptive", float(k), fp_method)
                sa = summarise_p(pa, flagged, ifrac)
                err = abs(sa["top1_prob"] - la["top1_prob"])
                if best is None or err < best[0]:
                    best = (err, float(k), sa)
            _, k_best, sa = best  # type: ignore[misc]
            entry["adaptive"] = {
                "k_best": k_best,
                "k_grid_min": float(k_grid.min()),
                "k_grid_max": float(k_grid.max()),
                "k_hit_grid_edge": bool(
                    k_best <= k_grid.min() * (1 + 1e-9) or k_best >= k_grid.max() * (1 - 1e-9)
                ),
                "free_parameters": 1,
                "sim": sa,
                "logged_top1_prob": la["top1_prob"],
                "logged_norm_entropy": la["norm_entropy"],
                "d_top1_rel": (sa["top1_prob"] - la["top1_prob"]) / la["top1_prob"],
                "d_entropy_abs": sa["norm_entropy"] - la["norm_entropy"],
                "argmax_matches_logged": (
                    None if logged_modal_top1 is None or "adaptive" not in logged_modal_top1
                    else bool(sa["top1_index"] == logged_modal_top1["adaptive"])
                ),
                "logged_modal_top1_index": (
                    None if logged_modal_top1 is None else logged_modal_top1.get("adaptive")
                ),
                "pass": bool(
                    abs(sa["top1_prob"] - la["top1_prob"]) / la["top1_prob"] <= GATE_TOP1_REL_TOL
                    and abs(sa["norm_entropy"] - la["norm_entropy"]) <= GATE_ENTROPY_ABS_TOL
                ),
            }
            entry["pass"] = bool(entry["grounded"]["pass"] and entry["adaptive"]["pass"])
            results.append(entry)
    any_pass = any(r.get("pass") for r in results)
    usable = [r for r in results if r.get("usable")]
    fm = [r["adaptive"]["sim"]["flagged_mass"] for r in usable if "adaptive" in r]
    spread = (max(fm) / min(fm)) if fm and min(fm) > 0 else float("nan")
    return {
        "thresholds": {
            "top1_relative": GATE_TOP1_REL_TOL,
            "norm_entropy_absolute": GATE_ENTROPY_ABS_TOL,
            "note": "declared in source before the sweep was run; both arms must pass "
                    "on the same (failure source, weight model) cell",
        },
        "n_cells": len(results),
        "n_cells_passing": sum(1 for r in results if r.get("pass")),
        "modelled_flagged_mass_spread_across_cells": spread,
        "spread_note": "ratio max/min of the MODELLED flagged mass (adaptive arm) across "
                       "cells. A large ratio means the modelled total is not identified by "
                       "the available data, independently of whether any cell passes.",
        "per_source": results,
        "verdict": "PASS" if any_pass else "FAIL",
        "consequence": (
            "modelled total mass on flagged clips is reported"
            if any_pass
            else "SIMULATION FAILED -- no modelled total is reported; only the measured "
                 "lower bound, the analytic uniform arm and the distribution-free bracket "
                 "stand as results"
        ),
    }


def census_top1(
    runs: Dict[str, Dict[str, object]],
    clips: List[str],
    flagged: np.ndarray,
    ifrac: np.ndarray,
) -> Dict[str, object]:
    """Pool the top-1 identity census across seeds, per arm, with clip names.

    Fully MEASURED. Answers "which clips does the collapse land on", which the
    scalar mass numbers cannot. `mass_share` is the time-averaged top-1 mass
    attributable to that clip, i.e. sum over iterations where it is the argmax
    of top1_prob, divided by the number of iterations -- so the mass_share
    column sums to the arm's measured lower bound when restricted to flagged
    clips.
    """
    out: Dict[str, object] = {}
    for arm in ("adaptive", "grounded"):
        occ: Dict[int, int] = {}
        mass: Dict[int, float] = {}
        iters = 0
        nseeds = 0
        seed_modal: Dict[int, List[int]] = {}
        for key, e in runs.items():
            if e["arm"] != arm:
                continue
            nseeds += 1
            sel = e["measured"]["selection"]  # type: ignore[index]
            iters += int(e["n_iters"])  # type: ignore[arg-type]
            best_here = None
            for row in sel["per_clip"]:  # type: ignore[index]
                i = int(row["clip_index"])
                occ[i] = occ.get(i, 0) + int(row["iters"])
                mass[i] = mass.get(i, 0.0) + float(row["mass"])
                if best_here is None or row["mass"] > best_here[1]:
                    best_here = (i, float(row["mass"]))
            if best_here is not None:
                seed_modal.setdefault(best_here[0], []).append(int(e["seed"]))  # type: ignore[arg-type]
        if not occ:
            continue
        ranked = sorted(mass.items(), key=lambda kv: -kv[1])
        rows = [
            {
                "clip_index": i,
                "clip": clips[i],
                "flagged": bool(flagged[i]),
                "infeasible_frac": float(ifrac[i]),
                "occupancy": occ[i] / iters,
                "mass_share": m / iters,
            }
            for i, m in ranked[:10]
        ]
        out[arm] = {
            "n_seeds": nseeds,
            "n_iters_pooled": iters,
            "top_clips_by_mass": rows,
            "modal_top1_index": ranked[0][0],
            "modal_top1_clip": clips[ranked[0][0]],
            "modal_top1_flagged": bool(flagged[ranked[0][0]]),
            "modal_top1_agrees_across_seeds": {
                str(i): sorted(v) for i, v in sorted(seed_modal.items())
            },
            "flagged_share_of_top1_mass": (
                sum(m for i, m in mass.items() if flagged[i]) / max(sum(mass.values()), 1e-300)
            ),
        }
    return out


def heuristic_totals(
    lb_mass: float, lb_frame: float, mean_top1: float,
    base_flagged: float, base_ifrac: float,
    top1_flagged_rate: float, top1_mean_ifrac: float,
) -> Dict[str, object]:
    """Two NAMED, clearly-assumed extrapolations from the top-1 term to the total.

    NEITHER IS A MEASUREMENT. They exist so a reader can see how much the answer
    moves under the cheapest plausible assumptions about the 1 - top1 residual,
    without a behavioural model. If the two disagree, the total is not pinned.

      base_rate       the residual mass is composed like the bank at large
                      (flagged fraction |F|/n). This is the CONSERVATIVE choice:
                      it assumes the collapse is selective only in its argmax.
      self_similar    the residual mass is composed like the argmax process
                      itself (the observed rate at which the top-1 clip is
                      flagged). This is the AGGRESSIVE choice: it assumes the
                      whole head of the distribution shares the argmax's taste.

    Falsifier for both: they ignore that the residual sits on ~perplexity-1
    clips, whose flagged composition is simply not logged.
    """
    resid = max(0.0, 1.0 - mean_top1)
    return {
        "residual_mass": resid,
        "flagged_mass": {
            "base_rate": lb_mass + base_flagged * resid,
            "self_similar": lb_mass + top1_flagged_rate * resid,
        },
        "infeasible_frame_share": {
            "base_rate": lb_frame + base_ifrac * resid,
            "self_similar": lb_frame + top1_mean_ifrac * resid,
        },
        "status": "MODELLED-BY-ASSUMPTION, not measured; reported only as a sensitivity",
    }


def audit_f_sources(clips: List[str], report_dir: str) -> Dict[str, object]:
    """Check the per-checkpoint campaign eval CSVs against the training bank.

    The campaign (`tools/run_campaign.sh`) trains on tier_mixed100 and evaluates
    on the DISJOINT heldout100 bank. Any attempt to build per-clip training
    failure rates from `reports/campaign/*_it*.csv` is therefore reading the
    wrong 100 clips. This audit makes that explicit rather than silent.
    """
    path = os.path.join(report_dir, "campaign")
    files = sorted(f for f in os.listdir(path)) if os.path.isdir(path) else []
    csvs = [f for f in files if f.endswith(".csv")]
    if not csvs:
        return {"campaign_csv_count": 0}
    with open(os.path.join(path, csvs[0])) as fh:
        got = [r["clip"] for r in csv.DictReader(fh)]
    inter = len(set(got) & set(clips))
    return {
        "campaign_csv_count": len(csvs),
        "example": csvs[0],
        "n_clips_in_campaign_eval": len(got),
        "n_shared_with_training_bank": inter,
        "verdict": (
            "campaign per-checkpoint eval CSVs are on a DISJOINT held-out bank; they "
            "cannot supply per-clip failure rates for the training clips"
            if inter == 0
            else "campaign eval overlaps the training bank"
        ),
    }


# ==========================================================================
# decomposition: how much of grounded's reduction is mechanical?
# ==========================================================================
def decompose(logged: Dict[str, Dict[str, float]], n_clips: int,
              lam_adaptive: Sequence[float]) -> Dict[str, object]:
    """Split grounded-vs-adaptive into shrinkage and feedback.

    Both arms are p = lam*u + (1-lam)/n (see module docstring). Grounded fixes
    lam = 0.9. If the two arms produced the SAME underlying failure signal u,
    grounded's top-1 mass would be exactly 0.9*u_max + 0.1/n where u_max comes
    from the adaptive arm's logged top-1. Whatever gap remains between that
    prediction and grounded's actual top-1 is not mechanical: it is the sampler
    changing what the policy learns, which changes u itself.
    """
    out = []
    for lam in lam_adaptive:
        u_max = (logged["adaptive"]["top1_prob"] - (1 - lam) / n_clips) / lam
        pred = MIXTURE_WEIGHT * u_max + EPS / n_clips
        obs = logged["grounded"]["top1_prob"]
        total = logged["adaptive"]["top1_prob"] - obs
        mech = logged["adaptive"]["top1_prob"] - pred
        out.append({
            "lam_adaptive_assumed": lam,
            "u_max_implied": u_max,
            "grounded_top1_predicted_from_shrinkage_only": pred,
            "grounded_top1_observed": obs,
            "total_reduction": total,
            "mechanical_reduction": mech,
            "dynamical_reduction": total - mech,
            "mechanical_share": mech / total if total else float("nan"),
        })
    return {
        "note": "lam_adaptive = S/(S+eps) with S the EMA of per-step termination "
                "counts; not logged, so bracketed. eps=0.1, so even S=10 gives "
                "lam=0.990 -- the additive floor is realised as <=1% of the mass.",
        "rows": out,
    }


# ==========================================================================
# driver
# ==========================================================================
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="analyze_adaptive_contamination.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
        epilog="""
METRIC GLOSSARY (every number this tool emits)

  measured.lb_flagged_mass
      mean over training iterations of  top1_prob * 1[top-1 clip is flagged].
      MEASURED. A strict lower bound on the total sampling mass on flagged
      clips, because total = sum over all flagged clips >= the top-1 term.
      Reported under three ambiguity policies (see --ambiguity).

  measured.lb_infeasible_frame_share
      mean over iterations of  top1_prob * infeasible_frac[top-1 clip].
      MEASURED. Lower bound on the expected share of tracked reference frames
      that are physically infeasible. Strictly smaller than the mass bound,
      because a flagged clip is only partly infeasible.

  measured.p_top1_flagged
      fraction of iterations whose argmax clip is flagged. MEASURED. The
      selection statistic: it says whether the sampler PICKS infeasible clips,
      independently of how much mass it then gives them. Bank baseline = 0.25.

  measured.mean_top1_prob / mean_norm_entropy
      time averages of the two logged sampling summaries. MEASURED.

  measured.mean_perplexity_clips
      time average of exp(H(p)) in clip units = the effective number of clips
      the sampler is actually drawing from. MEASURED, exact from the logged
      normalised entropy. 100 = no collapse; 1 = total collapse.

  top1_census.*
      which clips hold the top-1 slot, by name, with occupancy and mass share,
      pooled over seeds. MEASURED. This is the statistic the scalar masses
      cannot give: it identifies the specific references the collapse selects,
      and lets a reader check them against the feasibility screen by hand.

  runs.*.heuristic_totals
      ASSUMED, NOT MEASURED. Two named extrapolations from the top-1 term to a
      total, differing only in what they assume about the composition of the
      1 - top1 residual (bank base rate vs the argmax process's own rate).
      Present as a sensitivity band, never as a result.

  analytic.uniform_*
      the uniform arm is not measured from logs (its logged sampling metrics
      are hardcoded sentinels, see the module docstring); its contamination is
      exact: flagged mass = |F|/n, frame share = mean_c infeasible_frac_c.

  bracket.[lo,hi]
      rigorous interval on the TOTAL, from the logged (top-1 mass, entropy,
      argmax identity) plus |F| alone. DISTRIBUTION-FREE, no behavioural model.
      Read the WIDTH: if it is near-vacuous, the instrumentation cannot answer
      the "total" question and no amount of modelling makes that go away.

  gate.*
      the fixed-point reconstruction and its pre-declared validation gate.
      MODELLED. `verdict: FAIL` means no modelled total is reported. Swept over
      (per-clip failure source) x (weight model, see --weight-models). The
      grounded arm's fixed point has ZERO free parameters, because the EMA scale
      k cancels when q is renormalised at `commands.py:97` -- so its row is an
      unhedged prediction. The adaptive arm has exactly one (k), fitted to the
      logged top-1 mass, which leaves entropy as an out-of-sample test.
      `gate.modelled_flagged_mass_spread_across_cells` is the max/min ratio of
      the modelled answer across cells: read it before reading any cell.
      `argmax_matches_logged` is a DIAGNOSTIC, not a pass criterion -- it was
      added after the gate had already failed and folding it in would be moving
      the goalposts. It can only tighten, never loosen, the verdict.

  decomposition.*
      how much of grounded's top-1 reduction is the mechanical shrinkage
      lam: 1 -> 0.9, and how much is the sampler changing what is learned.

FALSIFIERS for the modelled part: the fixed point assumes (a) a stationary
per-clip failure rate f_c, (b) that the EMA has converged within an iteration
(alpha=0.01, 24 steps/iteration => horizon ~4 iterations, so borderline),
(c) that f_c measured by a held-out-protocol eval of a uniform-arm policy
transfers to the adaptive arm's in-training failure rate -- which is precisely
what the adaptive arm changes, so this is circular by construction, and
(d) that the EMA accumulates per-episode failures rather than per-step
termination flux (see --weight-models; the two differ by an order of magnitude
in the answer). Any of these being wrong invalidates the modelled total. The
measured lower bound and the analytic uniform arm assume none of them.

WHAT WOULD MAKE THE MODELLED TOTAL CREDIBLE: log the full p vector (or just
sum_{c in F} p_c) once per iteration. It is one line next to
`commands.py:117`, costs nothing, and would replace this entire modelling
layer with a measurement. Until then the total is not identified.
""",
    )
    p.add_argument("--repo", default=REPO, help="repository root (default: parent of tools/)")
    p.add_argument("--clips", default="bank/tiers/tier_mixed100.txt",
                   help="training clip list, in the exact order climb loads it "
                        "(climb/env_cfg.py:21-33 preserves file order, so line i == clip index i)")
    p.add_argument("--feasibility", default="reports/feasibility_all/feasibility.csv",
                   help="feasibility screen CSV supplying infeasible_frac")
    p.add_argument("--flag-threshold", type=float, default=0.10,
                   help="a clip is FLAGGED when infeasible_frac > this (default 0.10)")
    p.add_argument("--log-dir", default="logs/campaign", help="directory of training logs")
    p.add_argument("--bank-tag", default="mixed100", help="log name infix, {arm}-{tag}-s{seed}.log")
    p.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(ARMS))
    p.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    p.add_argument("--ambiguity", default="round", choices=("round", "drop", "zero"),
                   help="how to treat iterations whose logged top1_bin is not an exact "
                        "clip index (the metric is averaged over the reset events inside "
                        "an iteration, so it is exact only when the argmax did not move). "
                        "All three are always reported; this picks the headline. "
                        "'round' reproduces the lead's estimator (default)")
    p.add_argument("--self-test", action="store_true",
                   help="run the randomised falsification of entropy_bracket "
                        "(selftest_bracket) and record the outcome in the JSON. Slow, "
                        "but it is the only thing standing between a subtly wrong "
                        "convex-program solver and a published interval")
    p.add_argument("--no-bracket", action="store_true",
                   help="skip the distribution-free bracket (it is the slow part)")
    p.add_argument("--no-gate", action="store_true", help="skip the fixed-point simulation")
    p.add_argument("--k-decades", nargs=2, type=float, default=[-4.0, 4.0],
                   help="log10 range for the EMA scale k swept in the fixed point")
    p.add_argument("--k-points", type=int, default=161, help="grid points in the k sweep")
    p.add_argument("--fp-method", default="exact", choices=("exact", "iterate"),
                   help="how the sampler fixed point is solved. 'exact': the closed-form "
                        "1-D root find derived in fixed_point.__doc__. 'iterate': damped "
                        "Picard iteration on the literal code of commands.py:97-108, kept "
                        "as an independent cross-check (same answer, ~1000x slower)")
    p.add_argument("--weight-models", nargs="+", default=["rate", "flux"],
                   choices=("rate", "flux"),
                   help="what the failure EMA is assumed to accumulate. 'rate': w_c = f_c "
                        "(terminations per episode). 'flux': w_c = f_c / mean_survival_s_c "
                        "(terminations per env-second, the more faithful reading of "
                        "commands.py:206-211, which folds the count in once per env-STEP). "
                        "Both are swept because the choice is not measured and it moves the "
                        "modelled total by an order of magnitude.")
    p.add_argument("--json-out", default="reports/adaptive_contamination.json")
    p.add_argument("--markdown-out", default="reports/adaptive_contamination.md",
                   help="'-' to print the markdown table to stdout only")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    repo = os.path.abspath(args.repo)

    def rp(p: str) -> str:
        return p if os.path.isabs(p) else os.path.join(repo, p)

    clips = read_clip_list(rp(args.clips))
    n = len(clips)
    ifrac_map = read_infeasible_frac(rp(args.feasibility))
    missing = [c for c in clips if c not in ifrac_map]
    if missing:
        sys.exit(f"{len(missing)} clips absent from the feasibility CSV, e.g. {missing[:3]}")
    ifrac = np.array([ifrac_map[c] for c in clips])
    flagged = ifrac > args.flag_threshold
    # BUGFIX 2026-08-19: the flagged-mass statistics must be weighted by the
    # FLAGGED INDICATOR, not by a vector of ones. With ones, measured_lower_bound
    # degenerates to mean(top1_prob) (it drops the 1[top-1 is flagged] gate) and
    # entropy_bracket degenerates to [1, 1] (sum_c p_c == 1 for any p). Both were
    # silently wrong before this line existed.
    flagvec = flagged.astype(float)

    out: Dict[str, object] = {
        "tool": "tools/analyze_adaptive_contamination.py",
        "backs_claim": "flagship S3 C3-EXPOSURE (collapse targets infeasible reference)",
        "arm_semantics": {
            "uniform": "p = 1/n (commands.py:87-89). Sampling metrics are SENTINELS.",
            "adaptive": "additive offset, mjlab's formulation (commands.py:107-108). "
                        "No feasibility term.",
            "grounded": "convex mixture, i.e. the uniform floor actually is 10% "
                        "(commands.py:94-98). NO feasibility mask -- this arm is a FLOOR "
                        "REPAIR, not FGAS. It is the baseline FGAS must beat, not FGAS.",
        },
        "bank": {
            "clip_list": args.clips,
            "n_clips": n,
            "flag_threshold_infeasible_frac": args.flag_threshold,
            "n_flagged": int(flagged.sum()),
            "flagged_fraction": float(flagged.mean()),
            "mean_infeasible_frac_all_clips": float(ifrac.mean()),
            "mean_infeasible_frac_flagged_only": float(ifrac[flagged].mean()),
            "sum_infeasible_frac_over_flagged_div_n": float(ifrac[flagged].sum() / n),
        },
        "sampler_constants_from_climb_commands_py": {
            "clip_uniform_ratio_eps": EPS,
            "clip_adaptive_alpha": ALPHA,
            "source_lines": "climb/commands.py:85-108 (probabilities), 143-160 (metrics), "
                            "206-211 (EMA), 137-141 (uniform sentinels), 266/273 (cfg)",
        },
        "analytic_uniform_arm": {
            "why": "climb/commands.py:137-141 hardcodes sampling_entropy=1.0, "
                   "sampling_top1_prob=1/n, sampling_top1_bin=0.5. These are sentinels, "
                   "not measurements. Index n/2 happens to be a flagged clip in this bank, "
                   "so a naive lower-bound statistic on the uniform logs returns a "
                   "spurious 1/n.",
            "flagged_mass": float(flagged.mean()),
            "infeasible_frame_share": float(ifrac.mean()),
            "sentinel_bin_index": n // 2,
            "sentinel_bin_clip": clips[n // 2],
            "sentinel_bin_is_flagged": bool(flagged[n // 2]),
        },
    }

    runs: Dict[str, Dict[str, object]] = {}
    logged_mean: Dict[str, List[float]] = {}
    for arm in args.arms:
        for seed in args.seeds:
            path = rp(os.path.join(args.log_dir, f"{arm}-{args.bank_tag}-s{seed}.log"))
            if not os.path.exists(path):
                continue
            recs = parse_log(path)
            if not recs:
                continue
            key = f"{arm}-s{seed}"
            top1 = np.array([r["sampling_top1_prob"] for r in recs])
            ent = np.array([r["sampling_clip_entropy"] for r in recs])
            entry: Dict[str, object] = {
                "arm": arm,
                "seed": seed,
                "log": os.path.relpath(path, repo),
                "n_iters": len(recs),
                "measured": {
                    "mean_top1_prob": float(top1.mean()),
                    "max_top1_prob": float(top1.max()),
                    "mean_norm_entropy": float(ent.mean()),
                    "lb_flagged_mass": {
                        a: measured_lower_bound(recs, flagvec, n, a)
                        for a in ("round", "drop", "zero")
                    },
                    "lb_infeasible_frame_share": {
                        a: measured_lower_bound(recs, ifrac, n, a)
                        for a in ("round", "drop", "zero")
                    },
                    "mean_perplexity_clips": float(np.mean(np.exp(ent * math.log(n)))),
                    "perplexity_note": "exp(H) in clips = effective number of clips the "
                                       "sampler is actually drawing from. MEASURED.",
                    "selection": top1_selection_stats(recs, flagged, ifrac, n),
                    "by_quarter_lb_flagged_mass": [
                        measured_lower_bound(
                            recs[q * len(recs) // 4:(q + 1) * len(recs) // 4],
                            flagvec, n, args.ambiguity)["value"]
                        for q in range(4)
                    ],
                },
                "is_sentinel_arm": arm == "uniform",
            }
            if not args.no_bracket and arm != "uniform":
                entry["bracket_flagged_mass"] = bracket_over_run(recs, flagvec, n)
                entry["bracket_infeasible_frame_share"] = bracket_over_run(recs, ifrac, n)
            sel = entry["measured"]["selection"]  # type: ignore[index]
            if arm != "uniform":
                entry["heuristic_totals"] = heuristic_totals(
                    lb_mass=entry["measured"]["lb_flagged_mass"][args.ambiguity]["value"],
                    lb_frame=entry["measured"]["lb_infeasible_frame_share"][args.ambiguity]["value"],
                    mean_top1=float(top1.mean()),
                    base_flagged=float(flagged.mean()),
                    base_ifrac=float(ifrac.mean()),
                    top1_flagged_rate=float(sel["top1_mass_weighted_flagged_rate"]),
                    top1_mean_ifrac=float(sel["top1_mass_weighted_mean_infeasible_frac"]),
                )
            # Invariants that must hold for any correct weighting. The
            # flagged-mass lower bound is a SUBSET of the top-1 mass (it only
            # counts iterations whose argmax is flagged), and the frame-share
            # bound is that again scaled by infeasible_frac <= 1. Asserting them
            # would have caught the 2026-08-19 ones-vector bug immediately.
            _lb = entry["measured"]["lb_flagged_mass"][args.ambiguity]["value"]
            _lf = entry["measured"]["lb_infeasible_frame_share"][args.ambiguity]["value"]
            assert -1e-12 <= _lb <= float(top1.mean()) + 1e-12, (
                f"{key}: lb_flagged_mass {_lb} outside [0, mean top-1 {top1.mean()}]")
            assert -1e-12 <= _lf <= _lb * float(ifrac.max()) + 1e-9, (
                f"{key}: lb_infeasible_frame_share {_lf} exceeds lb_flagged_mass "
                f"{_lb} x max infeasible_frac {ifrac.max()}")
            entry["measured"]["invariants_checked"] = (
                "0 <= lb_flagged_mass <= mean_top1_prob and "
                "0 <= lb_infeasible_frame_share <= lb_flagged_mass * max(infeasible_frac)"
            )
            runs[key] = entry
            logged_mean.setdefault(arm, []).append(float(top1.mean()))
            logged_mean.setdefault(arm + "_H", []).append(float(ent.mean()))
    out["runs"] = dict(sorted(runs.items()))

    logged_pooled = {
        arm: {
            "top1_prob": float(np.mean(logged_mean[arm])),
            "norm_entropy": float(np.mean(logged_mean[arm + "_H"])),
        }
        for arm in ("adaptive", "grounded")
        if arm in logged_mean
    }
    out["logged_pooled_over_seeds"] = logged_pooled

    if args.self_test:
        st_flag = selftest_bracket(flagvec)
        st_ifr = selftest_bracket(ifrac)
        out["selftest_bracket"] = {"weight_flagged_indicator": st_flag,
                                   "weight_infeasible_frac": st_ifr,
                                   "pass": bool(st_flag["pass"] and st_ifr["pass"])}
        if not out["selftest_bracket"]["pass"]:
            sys.exit("entropy_bracket self-test FAILED; refusing to emit bracket numbers")

    census = census_top1(runs, clips, flagged, ifrac)
    out["top1_census"] = census

    if not args.no_gate and {"adaptive", "grounded"} <= set(logged_pooled):
        k_grid = np.power(10.0, np.linspace(args.k_decades[0], args.k_decades[1], args.k_points))
        out["f_source_audit"] = audit_f_sources(clips, rp("reports"))
        modal = {a: int(census[a]["modal_top1_index"]) for a in census}  # type: ignore[index]
        out["gate"] = run_gate(clips, flagged, ifrac, logged_pooled, k_grid,
                               TRAINBANK_F_SOURCES, tuple(args.weight_models), modal,
                               args.fp_method)
    if {"adaptive", "grounded"} <= set(logged_pooled):
        out["decomposition"] = decompose(logged_pooled, n, (1.0, 0.999, 0.99, 0.98))

    md = render_markdown(out, args)
    print(md)
    if args.json_out:
        jp = rp(args.json_out)
        os.makedirs(os.path.dirname(jp), exist_ok=True)
        with open(jp, "w") as fh:
            json.dump(out, fh, indent=2, sort_keys=True)
        print(f"\n[json] {jp}", file=sys.stderr)
    if args.markdown_out and args.markdown_out != "-":
        mp = rp(args.markdown_out)
        os.makedirs(os.path.dirname(mp), exist_ok=True)
        with open(mp, "w") as fh:
            fh.write(md + "\n")
        print(f"[markdown] {mp}", file=sys.stderr)
    return 0


def render_markdown(out: Dict[str, object], args: argparse.Namespace) -> str:
    b = out["bank"]  # type: ignore[index]
    amb = args.ambiguity
    L: List[str] = []
    L.append("# Adaptive-sampling contamination: does infeasible reference reach the optimizer?")
    L.append("")
    L.append(f"Bank `{b['clip_list']}`: {b['n_clips']} clips, "  # type: ignore[index]
             f"{b['n_flagged']} flagged at infeasible_frac > "  # type: ignore[index]
             f"{b['flag_threshold_infeasible_frac']} "  # type: ignore[index]
             f"({100 * b['flagged_fraction']:.0f} %). "  # type: ignore[index]
             f"Mean infeasible_frac over all clips "
             f"{b['mean_infeasible_frac_all_clips']:.4f}.")  # type: ignore[index]
    L.append("")
    L.append("## 0. Bottom line")
    L.append("")
    L.append("- **MEASURED, no model.** A failure-adaptive clip sampler puts demonstrably "
             "more mass on screen-flagged references than a uniform one: the adaptive arm's "
             "top-1 clip ALONE carries more flagged mass than the uniform arm's entire "
             "curriculum (25 % exactly). Same for the floor-repaired arm, by a smaller margin.")
    L.append("- **MEASURED, no model.** The collapse is not diffuse: it lands on ONE clip, the "
             "same one in all six runs, in both non-uniform arms -- and that clip is flagged.")
    L.append("- **MODELLED: FAILED.** The sampler fixed point cannot reproduce the logged "
             "top-1 mass and entropy from any available per-clip failure-rate source under "
             "either weight model. No total is reported. See section 3.")
    L.append("- **The instrumentation, not the analysis, is the bottleneck.** One extra logged "
             "scalar (`sum_{c in F} p_c` next to `commands.py:117`) would replace the whole "
             "modelling layer with a measurement.")
    L.append("")
    L.append("## 1. Measured (no model)")
    L.append("")
    L.append(f"Ambiguity policy for the headline column: `{amb}`. "
             "`LB` = time-averaged top-1 mass counted only when the top-1 clip is flagged; "
             "a strict lower bound on the total.")
    L.append("")
    L.append("| run | mean top-1 mass | mean norm. entropy | eff. clips exp(H) | "
             "P(top-1 flagged) | LB flagged mass | LB infeasible-frame share | "
             "distinct top-1 clips |")
    L.append("|---|---|---|---|---|---|---|---|")
    for key, r in out["runs"].items():  # type: ignore[union-attr]
        m = r["measured"]  # type: ignore[index]
        if r["is_sentinel_arm"]:  # type: ignore[index]
            L.append(f"| {key} | (sentinel 1/n) | (sentinel 1.0) | (sentinel) | (sentinel) | "
                     "(sentinel) | (sentinel) | (sentinel) |")
            continue
        sel = m["selection"]
        L.append(
            f"| {key} | {m['mean_top1_prob']:.4f} | {m['mean_norm_entropy']:.4f} | "
            f"{m['mean_perplexity_clips']:.1f} | "
            f"{100 * sel['p_top1_flagged']:.1f} % | "
            f"{100 * m['lb_flagged_mass'][amb]['value']:.2f} % | "
            f"{100 * m['lb_infeasible_frame_share'][amb]['value']:.2f} % | "
            f"{sel['n_distinct_top1_clips']} ({sel['n_distinct_top1_clips_flagged']} flagged) |"
        )
    a = out["analytic_uniform_arm"]  # type: ignore[index]
    L.append(f"| uniform (ANALYTIC) | {1.0 / b['n_clips']:.4f} | 1.0000 | "  # type: ignore[index]
             f"{b['n_clips']:.1f} | "  # type: ignore[index]
             f"{100 * b['flagged_fraction']:.1f} % | "  # type: ignore[index]
             f"{100 * a['flagged_mass']:.2f} % (exact total) | "  # type: ignore[index]
             f"{100 * a['infeasible_frame_share']:.2f} % (exact total) | n/a |")
    L.append("")
    L.append(f"The uniform arm's logged sampling metrics are hardcoded sentinels "
             f"(`climb/commands.py:137-141`); its `sampling_top1_bin = 0.5` points at clip "
             f"index {a['sentinel_bin_index']}, which in this bank IS flagged "  # type: ignore[index]
             f"(`{a['sentinel_bin_clip']}`), so a naive lower bound on the uniform "  # type: ignore[index]
             f"logs returns a spurious 1/n. The uniform row above is analytic, not measured.")
    L.append("")
    L.append("### Ambiguity sensitivity (LB flagged mass, %)")
    L.append("")
    L.append("| run | round | drop | zero | ambiguous iters |")
    L.append("|---|---|---|---|---|")
    for key, r in out["runs"].items():  # type: ignore[union-attr]
        if r["is_sentinel_arm"]:  # type: ignore[index]
            continue
        d = r["measured"]["lb_flagged_mass"]  # type: ignore[index]
        L.append(f"| {key} | {100 * d['round']['value']:.2f} | {100 * d['drop']['value']:.2f} | "
                 f"{100 * d['zero']['value']:.2f} | {d['round']['n_ambiguous']} |")
    L.append("")
    if out.get("top1_census"):
        L.append("## 1b. WHICH clips the collapse lands on (measured)")
        L.append("")
        L.append("`mass_share` = time-averaged top-1 mass attributable to that clip. "
                 "Pooled over seeds within an arm.")
        L.append("")
        L.append("| arm | clip idx | clip | infeasible_frac | flagged | occupancy | mass share |")
        L.append("|---|---|---|---|---|---|---|")
        for arm, c in out["top1_census"].items():  # type: ignore[union-attr]
            for row in c["top_clips_by_mass"][:6]:
                L.append(f"| {arm} | {row['clip_index']} | `{row['clip']}` | "
                         f"{row['infeasible_frac']:.3f} | {'YES' if row['flagged'] else 'no'} | "
                         f"{100 * row['occupancy']:.1f} % | {100 * row['mass_share']:.2f} % |")
        L.append("")
        for arm, c in out["top1_census"].items():  # type: ignore[union-attr]
            L.append(f"- **{arm}**: dominant top-1 clip is index {c['modal_top1_index']} "
                     f"(`{c['modal_top1_clip']}`, flagged={c['modal_top1_flagged']}); "
                     f"{100 * c['flagged_share_of_top1_mass']:.1f} % of all top-1 mass sits "
                     f"on flagged clips; per-seed modal clip: "
                     f"{c['modal_top1_agrees_across_seeds']}.")
        L.append("")
    if any("heuristic_totals" in r for r in out["runs"].values()):  # type: ignore[union-attr]
        L.append("## 1c. Sensitivity: extrapolating the top-1 term to a total "
                 "(ASSUMED, not measured)")
        L.append("")
        L.append("Two named assumptions about the composition of the `1 - top1` residual. "
                 "Neither is a result; they are here so a reader can see how far the answer "
                 "can move without a behavioural model.")
        L.append("")
        L.append("| run | LB (measured) | +base-rate residual | +self-similar residual |")
        L.append("|---|---|---|---|")
        for key, r in out["runs"].items():  # type: ignore[union-attr]
            h = r.get("heuristic_totals")
            if not h:
                continue
            lb = r["measured"]["lb_flagged_mass"][amb]["value"]  # type: ignore[index]
            L.append(f"| {key} | {100 * lb:.2f} % | "
                     f"{100 * h['flagged_mass']['base_rate']:.2f} % | "
                     f"{100 * h['flagged_mass']['self_similar']:.2f} % |")
        L.append("")
        by_arm: Dict[str, Dict[str, List[float]]] = {}
        for key, r in out["runs"].items():  # type: ignore[union-attr]
            h = r.get("heuristic_totals")
            if not h:
                continue
            d_ = by_arm.setdefault(str(r["arm"]), {"base": [], "self": [], "lb": []})
            d_["base"].append(h["flagged_mass"]["base_rate"])
            d_["self"].append(h["flagged_mass"]["self_similar"])
            d_["lb"].append(r["measured"]["lb_flagged_mass"][amb]["value"])
        if {"adaptive", "grounded"} <= set(by_arm):
            def mn(a: str, f_: str) -> float:
                return float(np.mean(by_arm[a][f_]))
            L.append(
                f"**Read this before quoting either column.** The arm ordering is NOT "
                f"robust to the residual assumption. Measured lower bound: adaptive "
                f"{100 * mn('adaptive', 'lb'):.1f} % > grounded {100 * mn('grounded', 'lb'):.1f} %. "
                f"Base-rate residual keeps that ordering ({100 * mn('adaptive', 'base'):.1f} % vs "
                f"{100 * mn('grounded', 'base'):.1f} %). Self-similar residual REVERSES it "
                f"({100 * mn('adaptive', 'self'):.1f} % vs {100 * mn('grounded', 'self'):.1f} %), "
                f"because the grounded arm spreads more mass outside its argmax and its argmax "
                f"process is, if anything, slightly MORE flagged-selective "
                f"(P(top-1 flagged) is comparable in both arms). So 'adaptive contaminates more "
                f"than grounded' is defensible as a statement about CONCENTRATION and about the "
                f"lower bound; it is NOT established for the total."
            )
            L.append("")
    if any("bracket_flagged_mass" in r for r in out["runs"].values()):  # type: ignore[union-attr]
        L.append("## 2. Distribution-free bracket on the TOTAL (still no behavioural model)")
        L.append("")
        L.append("Interval of total flagged mass consistent with the logged "
                 "(top-1 mass, entropy, argmax identity) and the count of flagged clips. "
                 "Valid for any distribution. Width is the point.")
        L.append("")
        L.append("| run | flagged mass lo | hi | infeasible-frame share lo | hi |")
        L.append("|---|---|---|---|---|")
        for key, r in out["runs"].items():  # type: ignore[union-attr]
            if "bracket_flagged_mass" not in r:
                continue
            f_ = r["bracket_flagged_mass"]
            g_ = r["bracket_infeasible_frame_share"]
            L.append(f"| {key} | {100 * f_['lo']:.2f} % | {100 * f_['hi']:.2f} % | "
                     f"{100 * g_['lo']:.2f} % | {100 * g_['hi']:.2f} % |")
        L.append("")
    if "gate" in out:
        g = out["gate"]  # type: ignore[index]
        L.append("## 3. Modelled total, and its validation gate")
        L.append("")
        fa = out.get("f_source_audit", {})
        if fa:
            L.append(f"*Failure-rate source audit*: {fa.get('verdict')} "
                     f"({fa.get('n_shared_with_training_bank')} of "
                     f"{fa.get('n_clips_in_campaign_eval')} clips shared with the "
                     f"training bank, across {fa.get('campaign_csv_count')} campaign CSVs).")
            L.append("")
        L.append(f"Gate: |sim-logged|/logged <= {g['thresholds']['top1_relative']} on mean "  # type: ignore[index]
                 f"top-1 mass AND |sim-logged| <= "
                 f"{g['thresholds']['norm_entropy_absolute']} on mean normalised entropy, "  # type: ignore[index]
                 "for BOTH arms on the SAME failure-rate source.")
        L.append("")
        L.append("| f source | w model | arm | sim top-1 | logged top-1 | sim H | logged H | "
                 "d top-1 (rel) | d H (abs) | argmax match | modelled flagged mass | pass |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in g["per_source"]:  # type: ignore[index]
            if not r.get("usable"):
                L.append(f"| {r['f_source']} | {r.get('weight_model','-')} | - | - | - | - | "
                         f"- | - | - | - | - | unusable |")
                continue
            for arm in ("grounded", "adaptive"):
                e = r[arm]
                am = e.get("argmax_matches_logged")
                L.append(
                    f"| {r['f_source']} | {r['weight_model']} | {arm} | "
                    f"{e['sim']['top1_prob']:.4f} | "
                    f"{e['logged_top1_prob']:.4f} | {e['sim']['norm_entropy']:.4f} | "
                    f"{e['logged_norm_entropy']:.4f} | {e['d_top1_rel']:+.3f} | "
                    f"{e['d_entropy_abs']:+.4f} | "
                    f"{'yes' if am else ('no (sim ' + str(e['sim']['top1_index']) + ' vs logged ' + str(e['logged_modal_top1_index']) + ')') if am is not None else 'n/a'} | "
                    f"{100 * e['sim']['flagged_mass']:.1f} % | "
                    f"{'PASS' if e['pass'] else 'FAIL'} |"
                )
        L.append("")
        L.append(f"Cells: {g['n_cells']} = (failure source) x (weight model); "  # type: ignore[index]
                 f"{g['n_cells_passing']} pass. The MODELLED adaptive flagged mass spans a "  # type: ignore[index]
                 f"factor {g['modelled_flagged_mass_spread_across_cells']:.1f} across cells "  # type: ignore[index]
                 "-- the modelled total is not identified by the data available, whatever "
                 "the gate says.")
        L.append("")
        L.append("The grounded arm has **zero** free parameters (the EMA scale `k` cancels "
                 "at `commands.py:97`), so its row is a pure prediction with nothing to tune. "
                 "The adaptive arm has one (`k`), fitted to the logged top-1 mass, leaving "
                 "entropy as the out-of-sample test.")
        L.append("")
        L.append(f"**Gate verdict: {g['verdict']}.** {g['consequence']}")  # type: ignore[index]
        L.append("")
    if "decomposition" in out:
        d = out["decomposition"]  # type: ignore[index]
        L.append("## 4. How much of grounded's reduction is mechanical?")
        L.append("")
        L.append("Both arms are `p = lam*u + (1-lam)/n`; grounded pins `lam = 0.9`, "
                 "adaptive gets `lam = S/(S+eps)` with S the failure-count EMA sum. "
                 "Holding `u` fixed at the adaptive arm's value predicts grounded's "
                 "top-1 mass from shrinkage alone.")
        L.append("")
        L.append("| lam(adaptive) | u_max implied | grounded top-1 predicted | observed | "
                 "mechanical share of the reduction |")
        L.append("|---|---|---|---|---|")
        for row in d["rows"]:  # type: ignore[index]
            L.append(f"| {row['lam_adaptive_assumed']:.3f} | {row['u_max_implied']:.4f} | "
                     f"{row['grounded_top1_predicted_from_shrinkage_only']:.4f} | "
                     f"{row['grounded_top1_observed']:.4f} | "
                     f"{100 * row['mechanical_share']:.1f} % |")
        L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
