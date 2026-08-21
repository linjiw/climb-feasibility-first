# TASK consistency-sweep — 2026-08-20

*Status labels used: measured, sealed ✓, exploratory. Artifact paths touched: listed per row.
UNVERIFIED: none remaining after fixes below.*

Cross-check of the preview page (`docs/index.html`), flagship sections, and companion draft
against `paper/RESULTS_LOG.md`. The four named discrepancies plus one found in the sweep.

| # | discrepancy | artifact truth | proposed (now applied) wording | files fixed |
|---|---|---|---|---|
| a | "positive on all six transfer pairs" (page §03) vs "4/6 pairs (p = .010–.045)" (page §04) | `reports/N_atlas_v21.json` F2: **direction +ve on 6/6 pairs; 4/6 clear the 200-draw random-3-feature permutation baseline** (p = 0.010 / 0.030 / 0.045 / 0.015); →grounded pairs +0.015/+0.018 n.s. (p = 0.235 / 0.160) | "direction positive on 6/6 transfer pairs; 4/6 significant beyond a random-feature permutation baseline (p = 0.010–0.045); the two →grounded pairs move +0.015/+0.018 but do not clear it" — the direction/significance split stated wherever either number appears | `docs/index.html` §03 callout; `paper/flagship/S7_transfer.md` (already split — sentence sharpened) |
| b | "d_z = 20" without per-seed values | per-seed it3999 endpoints (recomputed from `reports/campaign/*_it3999.csv`): uniform 0.8137/0.8125/0.8025, adaptive 0.7837/0.7850/0.7725 → **per-seed Δ(uniform−adaptive) = +0.0300/+0.0275/+0.0300** (mean +0.0292, sd 0.0014); `reports/campaign_summary_3arm.json` cohens_dz 20.207 | report the three per-seed deltas; footnote the d_z as an artefact of near-zero seed variance ("d_z = 20.2 reflects sd 0.0014 across 3 seeds; per-seed deltas are the meaningful statistic; sign test 3/3, permutation floor p = 0.125 at n = 3") | `paper/flagship/S3_collapse_nonfloor.md`; `docs/index.html` Act 1 |
| c | "two runs of the same physics engine" (page) vs "dual-engine" (page, S1 intro) — stack identity vague | S1/G0 compares **the same engine through two integration stacks**: mjlab v1.6.0 driving MuJoCo Warp 3.11.0 directly, vs Newton (repo commit `7bb6d02d`, pip version 1.6.0.dev0) driving MuJoCo Warp 3.11.0 through `SolverMuJoCo`; **classic MuJoCo 3.11.0 (C)** as third referee; warp-lang 1.16.0; pins recorded in `plan/PREREGISTRATION_G1_clip44.md` §Pins | standardise on **"dual-stack, same-engine conformance (third-engine referee)"**; name all three stacks + versions at first use; never "dual-engine" unqualified | `docs/index.html` (3 sites); `paper/flagship/S1_intro.md`; `S5_anatomy.md` §5.1 already names them — pins added |
| d | 327 N vs ~329 N phrasing drift | `reports/N1_clip44_knee_id.json`: descent-window (0.75–1.75 s) unconstrained unsupported force **median 328.6 N, p90 348.5 N**; robot weight **327.1 N** (33.3 kg) | canonical sentence: "median unsupported force 329 N (artifact: 328.6 N) against a robot weight of 327 N" — ~329 always paired with 327 at first use per document; standalone "~329 N" allowed only after the pairing | verified consistent in S1/S5/S6/companion/page (already paired); N1_RESULT unchanged (it is the artifact log) |
| e | (found in sweep) page §03 callout omitted the significance split while §04 card had it — same as (a) root cause: two authorship passes | as (a) | as (a) | `docs/index.html` |

Sweep also re-verified against `paper/RESULTS_LOG.md`: collapse numbers (0.884/0.870/0.893 top-1;
`reports/A5_coverage_dose.json`), grounded strata (+0.025/−0.009; `reports/N_atlas_v21.json`),
prevalence row set (`reports/feasibility_all/prevalence_report.txt`), N5 replication line
(r = 0.92, 6/6 > 5 mm — note this **6/6 is the instrument-replication statistic and is unrelated
to the 6/6 transfer-direction statistic in (a)**; both retained with explicit referents),
P-TAX row (`reports/P_TAX_result.json`). No further conflicts found.

**Result: table empty after the applied fixes** (all rows resolved in the same commit as this file).

---

## Addendum sweep, 2026-08-19 — over-generalisation of the 22.8 % prevalence

*Trigger: a second production bank (BONES-SEED / SONIC, 4,950 clips) was screened by an
independent re-implementation and returned **0.14 %**. Any sentence that let 22.8 % read as a rate
for retargeted humanoid banks in general is now wrong, and every site was checked.*

| site | what it said | what it says now |
|---|---|---|
| `flagship/S1_intro.md` (prevalence para) | "Screening the full 10,705-clip bank shows this is not an anecdote: 22.8 %…" — true, but the only bank-scale number in the paper's opening | same, plus the 0.14 % complement and "prevalence is a property of a particular retargeting pipeline; measure it per corpus" — *superseded by the second addendum: now "corpus-and-pipeline pairing"* |
| `flagship/S1_intro.md` (Contribution 3) | "bank-scale prevalence" (singular bank, generic phrasing) | "prevalence measured on two independently built production banks (22.8 % vs 0.14 %)" |
| `flagship/S6_screen_at_scale.md` | prevalence paragraph ended at the per-source spread | new **Cross-bank** paragraph (pre-registration, descoping, the box-jump caveat, the airborne/infeasible separation) |
| `flagship/S2_related.md` | "the failure class that produced our 22.8 % prevalence" | "…the 22.8 % prevalence we measure on one such pipeline (and 0.14 % on another, §6)"; SONIC entry rewritten — *"clean" was itself an over-claim and is replaced in the second addendum* |
| `flagship/S10_limitations.md` | "One retargeting pipeline's output was screened at scale" | rewritten: what the second bank does and does not settle (confounds named); plane-only terrain made concrete via the box jumps |
| `flagship/A3_screen_appendix.md` | external validation was all within-bank | added cross-implementation validation and the plane-only limit's concrete cost |
| `companion_note_draft.md` abstract | "…marking it as a pipeline property rather than a motion property" (correctly hedged, but unaccompanied) | hedge kept verbatim; the second-bank sentence added after it |
| `companion_note_draft.md` §4 | per-source spread only | new **A second bank, a second pipeline** subsection with the two-bank table |
| `companion_note_draft.md` §7 rec 1 | "Screen before training" | "…and **measure prevalence on your own corpus** — the two banks differ by 160×, so no published rate transfers" |
| `RESULTS_LOG.md` prevalence row | class "measurement" | class annotated "**one pipeline only** … see the cross-bank row" |

**Not fixed here, and owned elsewhere — flagged for the owner:**

1. `docs/index.html:92` renders "**22.8 %** of 10,705 retargeted clips are dynamically infeasible"
   as a hero statistic on the public page. It is the single most exposed over-generalisation
   surface in the project and is not in this builder's scope.
2. `docs/companion.html` and `docs/flagship.html` are generated from the markdown edited above and
   are now stale; they need `tools/render_paper_html.py` re-run.
3. The second bank's per-clip screen CSV lives only in a session scratchpad under `/tmp`
   (`RESULTS_LOG.md` cross-bank row carries the ⚠). It needs a durable path plus sentinel before
   submission — the same artifact-hygiene failure the 2026-08-20 companion review caught for the
   gap-sensitivity JSON.


---

## Second addendum sweep, 2026-08-19 (later same day) — attribution, cost, and what else the second bank now bounds

*Trigger: a re-read of every site the first addendum touched, plus the question the first sweep did
not ask — "which **other** claims does the SONIC negative result now over-generalise?". Five sites
found; all fixed in place. Section files and `flagship/DRAFT_full.md` verified byte-identical after
the edits.*

| site | what it said | what it says now | why |
|---|---|---|---|
| `flagship/S6…md` §6 head + methodological claim; `companion_note_draft.md` §4 + abstract | "prevalence is a property of **the retargeting pipeline**" / "belongs to a particular retargeting pipeline" | "…of a particular **corpus-and-pipeline pairing**" | attributing the 160× gap to the *retargeter* is more than the design supports: corpus content and a shipped release filter are confounded with it. §10 already said so ("prevalence varies by orders of magnitude across pipelines, not that any named pipeline causes it") — §6, §1 and the companion were stating the stronger version two paragraphs above their own caveat |
| `flagship/S6…md` caveat sentence | "different source corpora screened by two implementations of one method" | "…of one method, **with a shipped release filter on one side only**" | the filter confound was named in §10, RED_TEAM #20 and companion §4 but missing from §6 — the section most readers will use |
| `flagship/S2…md` | "We screen SONIC's own BONES-SEED bank in §6 and **it is clean** (0.14 %)" | "it returns 0.14 %, two orders of magnitude below our 22.8 % — **though not defect-free**, since seven clips do flag and five are jumps whose box is missing from the flat scene" | "clean" oversells a bank with 111 clips > 10 % airborne and a shipped box-jump defect; §6 already refuses "SONIC is clean and AMASS is broken" and §2 should not undo it |
| `companion_note_draft.md` §8 | "The practical split **for the community**: roughly two-thirds of the contamination is a 3-second script" | "The practical split **on this bank**: …" + a sentence noting the split is no more portable than the prevalence, since root projection cannot address a scene-mismatch defect class at all | the same over-generalisation as the 22.8 %, one deliverable further down. The second bank is the counterexample: its flagged class would be ~0 % recoverable by this operator. Logged as RED_TEAM #17 scope note |
| `flagship/S1…md`, `S6…md`, `companion` abstract + §4, `RESULTS_LOG` cross-bank row | screen cost quoted as "~0.2 CPU-seconds per clip" (= 131.7 s wall × 8 workers ÷ 4,950) | **0.145 CPU-s/clip = 0.84 ms per screened frame**, the register's measured figure, with 0.21 kept in `RESULTS_LOG` as the conservative billed-core equivalent; prose that spans both implementations now says "≤ 1 CPU-second per clip" | the durable pre-registered record (`prediction_register.md` P10) states 0.145; the drafts stated 0.21 with no derivation shown, so a reviewer cross-checking the register would have found an unexplained conflict. The companion abstract also said "~1 CPU-second" in one sentence and "~0.2" in the next |

**Also transcribed into `RESULTS_LOG.md`** (artifact-hygiene mitigation, not a correction): the
seven flagged BONES-SEED clip names with their `infeasible_frac`, and the 0.05 / 0.20 threshold
counts. Until the per-clip CSV has a durable home, that row plus the register entry are the whole
durable record of the measurement.

**Checked and deliberately left alone:** `S1_intro.md`'s "0.1 % to 100 % across source datasets
under a single retargeting pipeline — a pipeline property, not a difficulty gradient" (the
contrast there is with *difficulty*, and the within-pipeline source spread is exactly a
pipeline × source property — correctly hedged already); `S10_limitations.md`'s bank-provenance
paragraph (already the strictest statement in the paper, and the model the others were pulled
toward); the companion's "marking it as a pipeline property rather than a motion property"
(same within-pipeline contrast).

**Still open, still owned elsewhere:** the three items listed at the end of the first addendum
(`docs/index.html:92` hero statistic, stale `docs/{companion,flagship}.html`, the ephemeral
BONES-SEED CSV) are unchanged by this sweep and all three now also need the cost figure updated
where the page quotes it.
