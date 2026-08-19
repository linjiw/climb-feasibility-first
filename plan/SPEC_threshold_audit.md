# SPEC — TASK threshold-audit: justifying |Δq̇| ≤ 3×10⁻⁵ (v6; DO NOT RUN without approval)

*Status: spec only. No outcomes exist. Artifact paths touched: this file;
frozen analysis code `tools/analyze_threshold_audit.py` (companion to this spec, dry-run only).*

## Question

The conformance certificate's threshold (per-substep |Δq̇| ≤ 3×10⁻⁵ rad/s,
`reports/S1_KIT1226_n32_absorb.json` context) is currently *descriptive* — it is what the fixed
harness achieves. The audit makes it *outcome-anchored*: *at what per-substep divergence do
per-seed survival distributions become statistically distinguishable on the sealed primary?*

## Design (GPU: ~12 runs × 3 min = ~40 min, gap capacity; requires approval)

**Divergence injector.** In the certified harness, add a per-substep perturbation of magnitude λ
to Newton's post-step q̇ (zero-mean, isotropic over actuated dofs, fixed RNG stream per world) —
the smallest intervention that emulates "a coupling residual of size λ" without touching the
model. λ grid (log-spaced, rad/s): 0 (certificate), 1e-5, 3e-5 (the threshold), 1e-4, 3e-4, 1e-3,
3e-3, 1e-2, 3e-2, 0.1, 0.3, 0.64 (the magnitude of original bug #6's free-joint frame error).

**Protocol.** KIT_1226 (the clip that forked), n = 32 episodes × 3 IC seeds per λ, stratified
starts off (frame-0, as in S1), stock-mjlab arm as the reference distribution (3 seeds already
exist as by-products of S1 re-runs; re-use, do not re-run).

**Outcome and statistics (frozen before any run).**
- Primary: per-seed survival (3 values per λ) vs the mjlab reference per-seed survivals.
- **TOST equivalence** at the sealed-primary scale: equivalence bounds ±Δ_eq = 1/32 (one episode
  of 32 — the same seed-noise bound the S1 verdict used, `tools/s1_newton_conformance.py`
  criterion line). λ is *certified-equivalent* if TOST rejects both one-sided hypotheses at
  α = 0.05 with the 3-seed paired t (reported with its low-n caveat) **and** a permutation test
  over the 6 per-seed values agrees.
- λ* = the largest λ still certified-equivalent; the certificate's margin = λ*/3e-5.
- Secondary: same for mean tracking error (±10 % bound, the S1 secondary).

**Negative framing (computed from existing artifacts, no new runs needed).** The four original
bugs expressed as per-substep q̇ residuals, against the threshold:
| bug | residual scale | ×(3e-5) |
|---|---|---|
| #6 free-joint frame (pre-architecture) | 0.64 rad/s at substep 0 (`plan/S1_RESULT.md`) | ~21,000× |
| #8 DR not mirrored | qacc residual ≈ 8e-3 → q̇ step ≈ 4e-5–8e-3 per substep window (`g0_bias` logs) | 1.3–270× |
| #9 float32 contact flip | 0.05–3.3 rad/s at flip substeps (`plan/S1_RESULT.md` fix 9) | 1,700–110,000× |
| #11 one-directional coupling | not a q̇ residual — a state *event* (teleport overwrite); caught only by class-1 detection | n/a — motivates why the threshold alone is insufficient |
All three q̇-expressible bugs sit ≥ 1.3× (and mostly ≫ 10×) above the threshold at their active
substeps; #11 documents that a threshold on q̇ cannot replace the bidirectionality check.

**Deliverable.** `reports/threshold_audit/` with sentinel; a one-figure result
(λ → per-seed survival, TOST band, λ* marked, the four bugs' λ-equivalents as vertical lines).
Frozen analysis code written and dry-run on synthetic per-seed tables *before* approval to run.
