# Handoff — 2026-08-20 — continue from the completed N3 + E-HYG + P-SIGN chain

*Written for an external implementation agent (Codex) taking over. Repo: `/data/robotixx/climb`.
Authoritative plan: `plan/RESEARCH_PLAN_v5.md` (sealed). Read `plan/STATUS.md` first, then this
file. Nothing below overrides a seal; where this file and a sealed pre-registration disagree, the
seal wins.*

## 0. Where the project stands (one paragraph)

The project's spine: failure-adaptive motion-tracking curricula collapse onto dynamically
*infeasible* reference clips (22.8 % of the AMASS/wbt bank; 48.8 % of adaptive draws land on one
impossible clip); a cheap CPU feasibility screen separates learnable difficulty from reference
infeasibility; grounded sampling, pruning, repair (65.8 % of flagged clips auto-recoverable by
contact projection), and segment-level curation are the fixes, tested causally by N3
(composition), E-HYG (end-to-end hygiene at scale), N7 (repair-vs-prune, draft), and FGAS
(eligibility-masked adaptive sampling, apparatus built, unrun). Two papers are in flight: a
companion note (submit-candidate v0.2) and a flagship draft (`paper/flagship/DRAFT_full.md`).
Both repos are public; the site renders both drafts (`docs/{companion,flagship}.html`).

## 1. What just happened (the reason this handoff exists)

The pre-registered, gap-gated **N3 + E-HYG chain finished 2026-08-20 08:28:44 UTC**
(`reports/N3/COMPLETED`, `reports/E_HYG/EVALS_DONE`, `logs/campaign/n3_ehyg_chain.log` ends
"chain done"; exit_code=0). **P-SIGN also ran** (`reports/P_SIGN/run0/COMPLETED`). No training
or eval process is running. The outputs are on disk and **unanalyzed / unwritten-up**:

| experiment | outputs on disk | analysis state |
|---|---|---|
| N3 (sealed `af1b7c9f…`) | stratified CSVs `reports/N3_{uniform-mixed100g16-s1,uniform-mixed100g16-s2,adaptive-mixed100g16-s1,uniform-mixed100r16-s1}_strat.csv`; baselines `reports/N3_baseline_uniform-s{1,2,3}_strat.csv` + `reports/N3/baseline_s{2,3}/`; checkpoint-ladder evals under `reports/campaign/` | **NOT run.** No `plan/N3_RESULT.md` |
| E-HYG (sealed `a5494b7c…`, frozen analysis `5f8eb56e…`) | six CSVs `reports/E_HYG_uniform-amass800{,p}-s1_{heldout100,zsg,zsd}_strat.csv` (+ dirs under `reports/E_HYG/`) | **NOT run.** No result file |
| P-SIGN (sealed `c7916e8c…`) | `reports/P_SIGN/run0/{p_sign_summary.json,analysis.log,armA.npz,armC.npz,meta.json}` | analysis ran inside the harness; **verdict: `PASS: false`** — family 7/12 (need ≥8), controls 4/12 (need ≥8), localised 2. No `plan/P_SIGN_RESULT.md` written |

Frozen-analyzer hashes re-verified today: `tools/analyze_n3.py` = `b118b2d3…`,
`tools/analyze_ehyg.py` = `5f8eb56e…` — both match their seals. The s2/s3 stratified baselines
(the pre-unblinding requirement from `plan/N3_PREFLIGHT.md`) were captured by the chain.

## 2. Priority queue

### P0 — Unblind and write up the three completed experiments

Run the **frozen analyzers exactly as sealed** (verify sha256 first; if a hash mismatches, STOP
and report — do not edit or regenerate a frozen analysis):

```bash
cd /data/robotixx/climb
sha256sum tools/analyze_n3.py tools/analyze_ehyg.py   # must be b118b2d3…, 5f8eb56e…

# N3 — arm=path pairs; consult plan/N3_PREFLIGHT.md §decision-tree for the sealed
# endpoint definitions (E1: #44 kneel/crawl phase 0.000 → ≥0.25 both seeds) and arm naming.
bridge/.venv/bin/python tools/analyze_n3.py \
  --strat A1s1=reports/N3_uniform-mixed100g16-s1_strat.csv \
          A1s2=reports/N3_uniform-mixed100g16-s2_strat.csv \
          A2s1=reports/N3_adaptive-mixed100g16-s1_strat.csv \
          A3s1=reports/N3_uniform-mixed100r16-s1_strat.csv \
          B1s1=reports/N3_baseline_uniform-s1_strat.csv \
          B1s2=reports/N3_baseline_uniform-s2_strat.csv \
          B1s3=reports/N3_baseline_uniform-s3_strat.csv \
  --out reports/N3_result.json
# (arm keys above are a guess at the convention — read analyze_n3.py's header and
#  PREREGISTRATION_N3_coverage.md before running; the seal's naming wins.)

# E-HYG — control (-c) = tier_800, pruned (-p) = tier_800_pruned:
bridge/.venv/bin/python tools/analyze_ehyg.py \
  --held-c reports/E_HYG_uniform-amass800-s1_heldout100_strat.csv \
  --held-p reports/E_HYG_uniform-amass800p-s1_heldout100_strat.csv \
  --zsg-c  reports/E_HYG_uniform-amass800-s1_zsg_strat.csv \
  --zsg-p  reports/E_HYG_uniform-amass800p-s1_zsg_strat.csv \
  --zsd-c  reports/E_HYG_uniform-amass800-s1_zsd_strat.csv \
  --zsd-p  reports/E_HYG_uniform-amass800p-s1_zsd_strat.csv \
  --out reports/E_HYG_result.json
```

Then write, in the house style (every number pathed to an artifact; claims labelled
sealed/exploratory; falsifiers stated; "what must NOT be claimed" section):

1. `plan/N3_RESULT.md` — against the sealed endpoints in `PREREGISTRATION_N3_coverage.md` and
   the decision tree in `plan/N3_PREFLIGHT.md`. Report the pre-registered reading whatever it is;
   a null is a result.
2. `plan/E_HYG_RESULT.md` — against `plan/PREREGISTRATION_E_HYG.md` (primary: feasible-only
   held-out survival; secondary: all-clips; zero-shot ground/dynamic generalisation; the VOLUME
   branch guards the "just fewer clips" confound). Note: `tier_800_pruned` is *less dirty*, not
   clean — 140 unflagged clips still admit 5.43 min of infeasible bins
   (`plan/FGAS_DIRECTIVE_2026-08-19.md`); carry that caveat.
3. `plan/P_SIGN_RESULT.md` — **the sealed verdict is FAIL** (7/12 family, 4/12 controls-clean,
   2 localised; `reports/P_SIGN/run0/p_sign_summary.json`). Write it as sealed, no reframing.
   Consequence to propagate: the "runtime complement / raise-gains-suspect-the-reference"
   prediction in companion §5b and flagship §6 carried P-SIGN as its falsifier — those passages
   must be downgraded/rewritten to match the fail (the sign-reversal generalises to only ~half
   the family and controls are not clean). Check `plan/P_SIGN_PREP.md` for the pre-committed
   interpretation branches before writing.

Propagate all three into: `paper/RESULTS_LOG.md` (every new number → artifact path),
`paper/RED_TEAM.md` (close/annotate rows that depended on these outcomes; open new rows for any
weakness), `plan/STATUS.md` (state table), `plan/PERFORMANCE_PAYOFF_PLAN.md` (§1 loop status),
flagship §7/§8 slots and companion §8, and `paper/00_outline.md`.

### P1 — Apply the two deferred patches (gate is now satisfied)

`plan/DEFERRED_PATCHES.md` has the full procedure. The gate
(`reports/E_HYG/EVALS_DONE` exists AND no `climb_train.py|eval_stratified.py|climb_eval.py|
n3_ehyg_chain.sh` process) — **both hold as of this handoff**; re-check, then:

```bash
git apply --check reports/patches/exposure_ledger.patch reports/patches/eval_saturation.patch
git apply reports/patches/exposure_ledger.patch
git apply reports/patches/eval_saturation.patch
```

Follow the per-patch verification in that doc (py_compile now; the GPU smoke tests only when the
card is free). Remember: all 13 completed runs + the chain's arms have **no exposure ledger** —
report them as "exposure not instrumented", never as zeros.

### P2 — N7 seal (repair vs prune vs keep) — now unblocked by N3's readout

`plan/N7_DRAFT_repair.md` seals *after* N3 reads out, with N3's numbers folded into its
predictions. Banks are already built and hash-manifested: `bank/amass_repaired800/` +
`bank/tiers/tier_800_repaired.txt` (byte-identical clip list to tier_800 — isolates the
contamination axis from N; see `plan/REPAIRED800_COMPOSITION.md`). Seal it (sha256 the final
pre-registration, record in `plan/SEALS_*`), then queue the run **gap-gated** (≥ 14 GB free,
nice priority, never preempt LUCID — reuse the `tools/n3_ehyg_chain.sh` pattern with sentinels
via `tools/with_sentinel.sh`).

### P3 — FGAS (the method contribution) — checkout now released

`plan/FGAS_DIRECTIVE_2026-08-19.md` is the design record; read it in full. Now that the chain is
done, the block on `climb/commands.py` / `mjlab-1.6.0/src/mjlab/**` is lifted. Order of work:

1. Port the three-level sampler (`additive` = shipped default / `mixture` / `mixture+FGAS` with
   eligibility mask `m_b`) from the `~/mjlab` checkout into the running chain's tree, with
   telemetry incl. `sampling_ineligible_mass` (must be ~0 under FGAS by construction — that's
   FGAS's implementation falsifier). Tests exist: `~/mjlab/tests/test_tracking_sampling.py`.
2. Build `m_b` from **continuous severity** (`unsupported_impulse_per_weight_s` via `bin_score`),
   not the binary flag — the sidecars in `reports/eligibility/` already carry both; soft mask is
   primary, hard mask the ablation (per the predicts-failure measurement in the directive).
3. FGAS-2 is the open, load-bearing pre-registration: prediction = P(top-1 flagged) falls below
   0.40 while mean top-1 mass stays in [0.30, 0.38] (baseline grounded: 73.7 % / 0.339). Guard
   band 0 s in mjlab. Seal before any FGAS training run.
4. FGAS-3: sweep guard 0/0.5/1.0/2.0 s + `--min-seg-s` + `--min-bin-frac`.

### P4 — Paper and site propagation (after P0 lands)

- Re-render the site: `tools/render_paper_html.py` regenerates `docs/{companion,flagship}.html`
  from the markdown (HTML is generated output — edit markdown, re-run, commit both).
- `docs/index.html` still shows 22.8 % as an unqualified hero stat — qualify it as one
  corpus-and-pipeline pairing (the BONES-SEED bank screens at 0.14 %).
- The SONIC 4,950-row per-clip screen CSV lives only in a `/tmp` scratchpad — copy it to a
  durable path (e.g. `reports/sonic_screen/` + sentinel + sha256) before it is lost on reboot.
- Figure F9 (segment-curation recovery vs guard band) is a written candidate, not drawn.
- Companion is submit-ready **pending Linji's author/scope pass** — do not submit or file the
  upstream drafts (`reports/upstream_drafts/`) without explicit approval from Linji.

## 3. Rules of engagement (non-negotiable)

1. **Seals are law.** Never edit a sealed pre-registration, a frozen analysis, or a sealed clip
   list. Hash-verify before use (`plan/SEALS_2026-08-19.sha256`, `plan/E_HYG_FREEZE.sha256`,
   per-file `.sha256` companions). Report endpoints as pre-registered; nulls and fails are
   results (P-TAX null and P-SIGN fail are both already in the record — that's the house style).
2. **GPU discipline.** Shared box; LUCID has priority. New GPU work only through gap-gating
   (≥ 14 GB free, util check, nice) — reuse `tools/n3_ehyg_chain.sh` / `run_when_free.sh`
   patterns. Long jobs get sentinels (`tools/with_sentinel.sh`, `COMPLETED` files).
3. **Honesty conventions.** Every paper number must have an artifact path in
   `paper/RESULTS_LOG.md`. Claims carry labels (sealed / measured / exploratory / estimate /
   prediction). Statistical unit is the **motion**, not the episode; uncertainty by motion-level
   or seed×motion bootstrap. Lower bounds must never be quoted as totals (see the adaptive-
   contamination "what must NOT be claimed" list in `plan/FGAS_DIRECTIVE_2026-08-19.md`).
4. **grounded ≠ FGAS.** The grounded arm is mixture-mode floor repair with no eligibility mask;
   adaptive-vs-grounded is not evidence for FGAS.
5. **Corrections go in the record**, not silently: `paper/CORRECTIONS_2026-08-19.md` pattern.
6. **Commits**: imperative summaries in the existing style; there are substantial uncommitted
   changes plus all the new chain outputs — commit in coherent units (chain outputs + sentinels;
   then each RESULT doc with its propagation; then patches).
7. **Do not file/submit anything external** (upstream issues, arXiv, journal) without Linji's
   explicit approval.

## 4. Key file map

| what | where |
|---|---|
| status ledger | `plan/STATUS.md` |
| research plan (sealed, authoritative) | `plan/RESEARCH_PLAN_v5.md` |
| this chain's driver + log | `tools/n3_ehyg_chain.sh`, `logs/campaign/n3_ehyg_chain.log` |
| N3 seal / preflight / analyzer | `plan/PREREGISTRATION_N3_coverage.md`, `plan/N3_PREFLIGHT.md`, `tools/analyze_n3.py` |
| E-HYG seal / freeze / analyzer | `plan/PREREGISTRATION_E_HYG.md`, `plan/E_HYG_FREEZE.sha256`, `tools/analyze_ehyg.py` |
| P-SIGN seal / prep / outputs | `plan/PREREGISTRATION_P_SIGN.md`, `plan/P_SIGN_PREP.md`, `reports/P_SIGN/run0/` |
| N7 draft, repaired bank | `plan/N7_DRAFT_repair.md`, `plan/REPAIRED800_COMPOSITION.md`, `bank/amass_repaired800/` |
| FGAS design + measurements | `plan/FGAS_DIRECTIVE_2026-08-19.md`, `reports/eligibility/`, `~/mjlab` checkout |
| deferred patches | `plan/DEFERRED_PATCHES.md`, `reports/patches/*.patch` |
| papers | `paper/flagship/` (sections are source of truth), `paper/companion/companion_note_draft.md` |
| number→artifact ledger, red team | `paper/RESULTS_LOG.md`, `paper/RED_TEAM.md` |
| site renderer | `tools/render_paper_html.py` → `docs/` |
