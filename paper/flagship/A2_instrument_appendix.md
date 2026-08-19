# Appendix A2. Instrument calibration detail (N5)

*All numbers: `reports/G1/run0/g1_v2_summary.json`, `reports/G1/run1_seed1/g1_v2_summary.json`,
`plan/N5_RESULT.md`. Labels as marked.*

**Why the folded statistic fails [measured].** Two integrations of identical physics from
identical states (the §5.1-certified pair) diverge by 2.5–8.4 mm of body-position error within
seconds — closed-loop tracking is chaotic with a ~1–2 s Lyapunov horizon at the millimetre scale.
Mean |φ⁺ − φ⁻| along paired trajectories therefore measures divergence, not mechanism: every G1
intervention effect (3–19 mm) sat at that floor, which is why the sealed 5× rule reported nothing.

**The three calibrated statistics.** **S** = E_replicates[mean_t(φ⁺ − φ⁻)] with paired-bootstrap
95 % CIs (2,000 draws) — signed, so chaos cancels in expectation and shrinks with R;
**D** = W1(pooled φ⁺, pooled φ⁻) − W1(identical-physics pair); **T** = paired first-termination
shift and per-foot contact-onset shift. Resolution rule: |S| > 2× the floor CI half-width with
the CI excluding zero.

**Floor behaviour [measured].** With R = 8 the identical-physics floor is ≈ 0 ± 1 mm on long
clips (−0.1 [−0.9, +0.5] on the attractor; +0.2 [−1.0, +1.5] on the easy control) — the unbiased
noise reference every effect is read against, published per run.

**Resolved effects [exploratory labels; two independent IC-seed sets].** Motor ±15 %: resolved on
5/6 clips, spanning −14.2 mm (helps, high-dynamic clip) to +11.5/+12.8 mm (hurts, the impossible
clip — the sign reversal, airborne-window-localised in both sets: +15.0/+16.0 mm airborne vs
+0.3/−1.4 mm standing). Delay +20 ms: resolved on the dynamic clips (+11.9/+9.8 mm) and advances
the attractor's fall by 0.51 ± 0.14 s. Stiffness/CoM/condim: 2–3 mm class, mostly unresolved.
Contact onsets move ≤ 0.03 s under every intervention — no intervention changes *when* feet land,
only what happens after.

**Replication [measured].** Across seed sets: Pearson r = 0.92 over all 36 (axis, clip) effects;
6/6 sign agreement on every effect above 5 mm; 2–4 mm effects flip sign exactly as their CIs
permit. The instrument is reproducible where it claims resolution and says so where it does not.

**What a future fragility design inherits.** Signed replicate means, R ≥ 8, published per-run
floor, δ sized so target effects clear ~2 mm, and reference-derived (not rollout-derived) windows
for any localisation claim — the exact configuration P-SIGN is sealed under [pending 🕐].
