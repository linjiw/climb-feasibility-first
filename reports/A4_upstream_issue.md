# A4 — Upstream issue draft: `adaptive_uniform_ratio` is not a uniform floor

**Status: drafted, NOT filed.** Filing is an outward-facing action; say the word
and I'll open it against `mujocolab/mjlab`. A near-identical report applies to
`whole_body_tracking` (BeyondMimic) — see Scope.

---

## Title

`adaptive_uniform_ratio` does not provide a uniform floor; its effective strength scales with `num_envs` and failure rate

## Summary

In the tracking task's adaptive sampler, the uniform prior is combined with the
failure statistic **additively**, and the failure statistic is an EMA of raw
*counts*. The uniform term's share of the sampling distribution is therefore
`ε / (Σq + ε)` — a quantity that shrinks as failures accumulate and as
`num_envs` grows, rather than the fixed `ε` the parameter name implies.

Consequence: the same `adaptive_uniform_ratio=0.1` behaves very differently at
1024 envs and at 4096 envs, and provides no lower bound on any bin's sampling
probability. In our runs the distribution collapsed to a single unit holding
87–89% of all sampling mass despite the nominal "10% uniform floor".

## Where

`src/mjlab/tasks/tracking/mdp/commands.py`, in `MotionCommand._adaptive_sampling`:

```python
sampling_probabilities = (
    self.bin_failed_count + self.cfg.adaptive_uniform_ratio / float(self.bin_count)
)
...
sampling_probabilities = sampling_probabilities / sampling_probabilities.sum()
```

with, in `_update_command`:

```python
self.bin_failed_count = (
    self.cfg.adaptive_alpha * self._current_bin_failed
    + (1 - self.cfg.adaptive_alpha) * self.bin_failed_count
)
```

and `self._current_bin_failed[:] = torch.bincount(fail_bins, minlength=self.bin_count)`
— so `bin_failed_count` carries units of *episodes failed per update*, not a
normalised distribution.

## Derivation

Let `q` be the failure EMA over `N` bins, `ε = adaptive_uniform_ratio`. Then

```
p_i = (q_i + ε/N) / (Σq + ε)
```

Total mass contributed by the uniform term:

```
Σ_i (ε/N) / (Σq + ε)  =  ε / (Σq + ε)
```

This equals `ε` only when `Σq ≈ 1`. Since `q` is an EMA of counts, `Σq`
approaches the mean number of failing episodes per update, which grows with
`num_envs`:

| Σq (mean failures/update) | uniform share at ε = 0.1 |
|---:|---:|
| 0.1 | 50% |
| 1 | 9.1% |
| 10 | 1.0% |
| 50 | 0.2% |

A convex mixture holds the uniform share at `ε` unconditionally:

```
p = (1 - ε) * q / Σq  +  ε / N
```

## Minimal reproduction

No simulator needed — the sampler arithmetic alone shows it:

```python
import torch

N, eps = 100, 0.1
for scale in (0.1, 1.0, 10.0, 50.0):
    q = torch.zeros(N)
    q[0] = scale                      # failures concentrated on one bin
    additive = (q + eps / N) / (q + eps / N).sum()
    mixture  = (1 - eps) * (q / q.sum()) + eps / N
    print(f"Sum(q)={scale:5.1f}  additive: top1={additive.max():.3f}, "
          f"uniform share={eps/(q.sum()+eps):.3%}   "
          f"mixture: top1={mixture.max():.3f}, uniform share={eps:.1%}")
```

```
Sum(q)=  0.1  additive: top1=0.505, uniform share=50.000%   mixture: top1=0.901, uniform share=10.0%
Sum(q)=  1.0  additive: top1=0.910, uniform share=9.091%   mixture: top1=0.901, uniform share=10.0%
Sum(q)= 10.0  additive: top1=0.990, uniform share=0.990%   mixture: top1=0.901, uniform share=10.0%
Sum(q)= 50.0  additive: top1=0.998, uniform share=0.200%   mixture: top1=0.901, uniform share=10.0%
```

The additive form's behaviour swings from 0.50 to 0.998 top-1 mass across a
plausible range of failure rates; the mixture is invariant.

## Empirical evidence

Measured in a clip-level port of this sampler (100 units instead of time bins,
G1 tracking, 4096 envs, `ε = 0.1`, `adaptive_alpha = 0.01`), 3 seeds:

| arm | min normalised entropy | max top-1 mass |
|---|---:|---:|
| uniform control | 1.000 | 0.010 (= 1/100) |
| additive (this formulation) | 0.120 – 0.153 | **0.870 – 0.893** |
| convex mixture | 0.754 | 0.186 |

Held-out survival on 100 unseen clips, 3 seeds paired: additive 0.780 ± 0.006 vs
uniform 0.810 ± 0.005; the adaptive arm's entropy minimum (iterations 1500–2500)
coincides with the peak performance deficit (Δ = 0.145 at iteration 2500).

## Suggested fix

Normalise before mixing, so `ε` is a scale-invariant coverage floor:

```python
q = self.bin_failed_count
q = q / q.sum() if float(q.sum()) > 0 else torch.full_like(q, 1.0 / self.bin_count)
sampling_probabilities = (1.0 - eps) * q + eps / self.bin_count
```

This is behaviour-changing for existing configs, so it may warrant a flag
(`uniform_mixing: {"additive", "mixture"}`) defaulting to the current behaviour
for one release, with the docstring stating the scale dependence either way.

Minimal alternative if a behaviour change is unwanted: document that
`adaptive_uniform_ratio` is an additive pseudo-count, not a floor, and that its
effective weight depends on `num_envs` and the failure rate — so it must be
retuned when either changes.

## Scope

The same expression appears in BeyondMimic / `whole_body_tracking`:

- `source/whole_body_tracking/.../tasks/tracking/mdp/commands.py:289`
- `source/whole_body_tracking/.../tasks/tracking/mdp/atlas_motion_command.py:471`

both with `adaptive_uniform_ratio: float = 0.1` and a `bincount`-derived EMA, and
that repo exposes `--adaptive_uniform_ratio` as a tuning flag — so anyone who
tuned it at one `num_envs` and scaled up has silently changed the sampler.

We have not checked other downstream forks.
