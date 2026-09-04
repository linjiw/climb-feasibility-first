# CLIMB — feasibility-gated humanoid motion tracking

**Project page:** https://linjiw.github.io/climb-feasibility-first/ ·
**Tool:** [refeas](https://github.com/linjiw/refeas) (dynamic-feasibility screen, Apache-2.0) ·
**Feasibility table:** [`datasets/README.md`](datasets/README.md) (internal candidate; public release blocked) ·
**Harness guide:** [`paper/PRACTITIONERS_GUIDE_HARNESS_TRAPS.md`](paper/PRACTITIONERS_GUIDE_HARNESS_TRAPS.md) ·
**Phase-G table shell:** [`paper/PHASE_G_RESULT_TABLE_SHELL.md`](paper/PHASE_G_RESULT_TABLE_SHELL.md) ·
**Paper completion plan:** [`plan/PAPER_COMPLETION_2026-09-04.md`](plan/PAPER_COMPLETION_2026-09-04.md) ·
**Method reframe + next research:** [`plan/METHOD_REFRAME_2026-09-04.md`](plan/METHOD_REFRAME_2026-09-04.md) ·
**Companion note (draft):** [`paper/companion/companion_note_draft.md`](paper/companion/companion_note_draft.md) ·
**Flagship draft (with slots):** [`paper/flagship/DRAFT_full.md`](paper/flagship/DRAFT_full.md)

Generalist humanoid motion tracking (BeyondMimic/mjlab lineage, Unitree G1) trains on large
retargeted motion banks and reallocates updates from policy outcomes. CLIMB addresses
**reference--physics misalignment**: persistent error can mean either useful control difficulty or
a final robot-space reference whose demanded wrench has no admissible source under the declared
robot/scene model. The method screens contact and actuator capacity, routes intervals to admit /
contextualize / repair / quarantine, constructs exact non-wrapping legal starts, and applies
learning progress only inside a hard feasibility gate.

Measured evidence (each number is status-labelled and artifact-pathed in the drafts): a shared
unsupported kneel/crawl attractor recurs in 3/3 adaptive seeds while campaign peak top-1 mass
reaches 0.870–0.893; its descent has median 329 N unsupported demand against a 327 N robot.
**2,442/10,705 clips (22.8%) cross the fixed threshold in one AMASS→G1 corpus/pipeline**, versus
7/4,950 (0.14%) in a separately filtered production pairing. The two implementations agree on
39/40 strict decisions in a flag-enriched same-clip panel. An exact-support repair panel qualifies
22/26 flagged candidates and preserves 4/4 feasible controls byte-identically. Whether calibrated
ALP improves policy performance inside the 1,184-unit gate remains the endpoint-blind Phase-G
experiment; no improvement is claimed before that result exists.

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

## Status (2026-09-04)

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
excluded, and this is not a bank-wide recovery or policy claim. Newton v1.5 isolated
recertification passed on two hash-bound units, but its sealed no-training predictive gate failed
on valid data (adaptive partial ρ = 0.141, p = 0.158; LOCO lift −0.006), so Newton remains an
instrument and G3 must never run. Pending 🕐: the unsealed exact-support G2−G1 segment-native
follow-up (the exploratory pilot was only 0.014 TV from control, so adaptive allocation remains
untested) and E3 support moderation. The durable BONES-SEED screen is now
`reports/feasibility_sonic/{hygiene_screen.csv,COMPLETED.json}`. The current machine audit and
next-direction brief are in `plan/NEXT_RESEARCH_2026-09-03.md`; the current citation boundary
and eight-page completion path are in `paper/CITATION_CHECK_2026-09-04.md` and
`plan/PAPER_COMPLETION_2026-09-04.md`. Results freeze Dec 1; ICRA 2027 is the immediate
eight-page decision, with the full draft retained as the RSS-scale source.
