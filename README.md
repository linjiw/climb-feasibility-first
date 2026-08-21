# CLIMB — feasibility × support × intrinsic: an audit of humanoid motion-tracking RL

**Project page:** https://linjiw.github.io/climb-feasibility-first/ ·
**Tool:** [refeas](https://github.com/linjiw/refeas) (dynamic-feasibility screen, Apache-2.0) ·
**Companion note (draft):** [`paper/companion/companion_note_draft.md`](paper/companion/companion_note_draft.md) ·
**Flagship draft (with slots):** [`paper/flagship/DRAFT_full.md`](paper/flagship/DRAFT_full.md)

Generalist humanoid motion tracking (BeyondMimic/mjlab lineage, Unitree G1) trains on tens of
thousands of retargeted clips, steered by failure-adaptive curricula, scored by averaged survival.
This repository is an end-to-end audit of that chain. Its central finding: apparent per-clip
**difficulty conflates three things** — *feasibility* (can any controller supply the forces the
reference demands with the contacts it offers?), *support* (does the bank contain anything like
it?), and *intrinsic* hardness — and samplers, harnesses, and benchmarks that cannot tell them
apart silently optimise the wrong objective. Headline results (each labelled and artifact-pathed
in the drafts): failure-adaptive sampling collapses onto a single clip whose retargeted descent
is *physically impossible* (median 329 N unsupported vs a 327 N robot); a one-line
normalise-then-mix repairs the sampler; **22.8 % of one 10,705-clip AMASS→G1 corpus/pipeline is
dynamically infeasible for > 10 % of frames** (0.1 %→100 % by source under one retargeter, versus
0.14 % in a second production corpus/pipeline); and feasibility
features are the first that make difficulty labels transfer across policies (Spearman
0.567 → 0.609 on the headline pair, permutation p = 0.010).

## For reviewers — start here, in this order

1. **[`paper/RESULTS_LOG.md`](paper/RESULTS_LOG.md)** — every paper-bound number → artifact path.
   The drafts are not the ground truth; this log and the `reports/` files it points to are.
2. **[`paper/flagship/preregistration_table.md`](paper/flagship/preregistration_table.md)** — the
   sealed record: every pre-registration (hash, date, prediction, outcome), including the failed
   G1 gate, the withdrawn S1 verdict, and three kept nulls. Hash manifests: `plan/*.sha256`.
3. **[`paper/companion/companion_note_draft.md`](paper/companion/companion_note_draft.md)** (v0.2,
   submit candidate) and its adversarial review
   [`paper/companion/REVIEW_2026-08-20.md`](paper/companion/REVIEW_2026-08-20.md) — two majors
   found and fixed same day, dispositions logged.
4. **[`paper/RED_TEAM.md`](paper/RED_TEAM.md)** — the standing audit ("what exposure, harness, or
   data artifact could explain this instead?") with open items marked.
5. **[`plan/STATUS.md`](plan/STATUS.md)** — the live ledger: done / sealed / pending / scheduled.
   Directives: `plan/RESEARCH_PLAN_v5.md`, `plan/ADVISOR_DIRECTIVE_2026-08-20_v6.md`.

House rules (v6): sealed files are never edited (corrections by addendum); analysis code for
sealed experiments is frozen and dry-run on synthetic data before outcomes exist
(`tools/analyze_n3.py`, `tools/analyze_p_sign.py`, both with `--synthetic`); every claim carries
exactly one status label — **sealed ✓ / sealed ✗ (kept) / measured / exploratory / pending 🕐** —
and pending results never do load-bearing work.

## Layout

| path | contents |
|---|---|
| `plan/` | research plans, sealed pre-registrations + hashes, result logs (S1/G1/N1/N2/N5/P-TAX…), preflights, specs |
| `paper/` | flagship sections + assembled draft, companion note + review, results log, red-team audit, figure scripts + outputs |
| `reports/` | measurement artifacts: conformance runs, gate outputs, feasibility screens (`feasibility_all/` = 10,705-clip prevalence), audits, completion sentinels |
| `tools/` | instruments: conformance harness (`s1_newton_conformance.py`), gates + frozen analyses, feasibility screen (`n1_knee_id.py`), stratified evaluation (`eval_stratified.py`) |
| `climb/` | the mjlab task extension (multi-clip motion bank, samplers) |
| `docs/` | this project's page (GitHub Pages) |
| `WORKSPACE.md` | operational notes for reproducing the bank build (body order, fps inference, ground alignment) |

Not in the repo (size/licensing): the retargeted motion bank (~14 GB; AMASS-derived — obtain
AMASS and the whole_body_tracking retarget output separately, then follow `WORKSPACE.md`),
training logs/checkpoints, and the mjlab/Newton environments.

## Engine pins (the conformance certificate is version-pinned)

MuJoCo 3.11.0 (C) · MuJoCo Warp 3.11.0 · mjlab v1.6.0 · Newton commit `7bb6d02d` · warp-lang
1.16.0 · Unitree G1 `g1.xml` sha `febdcbef…` (`plan/PREREGISTRATION_G1_clip44.md` §Pins).
The closed conformance certificate remains tied to that historical commit. New work targets a
fresh isolated Newton v1.5.0 environment; the existing bridge currently reports a 1.6.0.dev0
package and is not the recertification environment (`plan/NEWTON_SEGMENT_DIRECTION_2026-08-21.md`).

## Status (2026-08-21)

Done: sampler collapse + non-floor (sealed ✓; upstream mjlab #1153 / whole_body_tracking #73),
grounded repair (sealed ✓), dual-stack conformance |Δq̇| ≤ 3×10⁻⁵ (measured, four coupling errors
documented incl. one withdrawn verdict), G1 physics gate (sealed ✗, kept), airborne-reference
verdict (measured), 10.7k-clip prevalence (measured), atlas v2.1 transfer (sealed ✓/✗ split),
calibrated instrument + replication (exploratory label), P-TAX (sealed null), N3 (mixed: targeted
endpoints pass, regression stop), E-HYG (sealed pruning null), P-SIGN (sealed fail), soft FGAS
(primary not confirmed; implementation gate failed), and N7 (positive +0.0397 deployment contrast,
but benefit/coverage gates fail and raw-reference policy transfer is null). DFRP v1 now has a
fail-closed, source-motion-bound exact contract: a frozen CPU panel admits 22/26 flagged repairs
and 4/4 byte-identical controls, yielding 36 units and 10,561 legal starts; four failures remain
excluded, and this is not a bank-wide recovery or policy claim. Pending 🕐: Newton v1.5 isolated
recertification and its no-training predictive gate, a separately sealed segment-native follow-up
under the corrected lifecycle/evaluator, and E3 support moderation. Results
freeze Dec 1; RSS 2027 target.
