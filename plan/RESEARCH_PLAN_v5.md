# Research Plan v5 — Writing-first window and the feasibility-first program (2026-08-19)

Encodes the advisor directive of 2026-08-19 (D1–D4 + schedule + paper spec). v4's freeze discipline
continues underneath. Decisions are not re-litigated here; conflicts with sealed artifacts are
flagged in `GLOBAL_EVAL_ADDENDUM.md` §Conflicts.

## Standing constraints

- CPU-only until 2026-09-15 (LUCID ICRA window). GPU minutes only for items this plan names
  (P-SIGN), in genuine gap capacity, through the shared queue.
- Frozen stays frozen: E3/E10/E4 seals, N3 pre-registration, sampling ledger, SONIC,
  Featherstone/XPBD, differentiable contacts.
- Seal-before-run; corrections by addendum; sealed files never edited.
- Every background job writes a completion sentinel (`tools/with_sentinel.sh`) into its report dir.
- Every paper-bound number carries an artifact path in `paper/RESULTS_LOG.md`.
- No new research threads; new ideas go to `plan/PARKING.md` (one paragraph + why it waits).

## D1 — evaluation-contamination policy

Sealed as `GLOBAL_EVAL_ADDENDUM.md` (`a93a87a0…`): primary endpoints feasible-only
(`infeasible_frac ≤ 0.10`, screen pinned by hash), secondary all-clips, descriptive infeasible-only.
Threshold provenance cited (first appearance in the N3 seal `af1b7c9f…` and E3 addendum
`f7929136…`, both 2026-08-18). Worked example: ceiling 0.810 → 0.834; grounded edge +0.025
feasible / −0.009 infeasible. Sealed before N3 relaunch and before any E3 number.

## D2 — spin-out (approved; prevalence condition met: 22.8 % bank-wide, ground 39 %, dynamic 59 %, per-source 0.1–100 %)

a) **Tool release**: standalone repo `refeas/` (this workspace), Apache-2.0, versioned, G1 worked
example, output schema documented, the D1-pinned hash tagged. → `refeas/`
b) **Companion note** (4–6 pp, arXiv + workshop): *Auditing dynamic feasibility of retargeted
humanoid motion data*. Method; clip #44 anatomy as validation (airborne window, ~329 N unsupported,
family-wide) with the N5 sign-reversal localisation as independent corroboration; prevalence by
category × source; the 29/100 eval-set contamination; recommendations; tool link. Flagship keeps a
compressed subsection citing it. → `paper/companion/`
c) **Upstream note drafts** (professional format, as #1153/#73): (1) to
**whole_body_tracking / BeyondMimic** — the AMASS bank here is its retarget output
(`/data/robotixx/wbt/train_converted_complete`, see `SETUP_AND_FINDINGS.md` provenance and the
retarget-quality table); (2) dataset-level advisory for the extreme sources (CNRS 100 %,
Transitions 90 % flagged). Minimal repro: one clip + screen output + rendered airborne-window
frames. Scope: artifact demonstrated in the retarget-to-G1 *output*, not necessarily the source
mocap. **Draft only — not filed until Linji approves.** → `reports/upstream_drafts/`

## D3 — new pre-registrations (sealed 2026-08-19, `SEALS_2026-08-19.sha256`)

- **P-SIGN** (`c7916e8c…`): generality of the motor-strength sign reversal on the 12
  highest-infeasibility family clips vs 12 feasible ground controls; three sealed criteria
  (≥ +5 mm airborne on ≥ 8/12; < 2 mm on ≥ 8/12 controls; ≥ 3× localisation); N5 statistic with
  per-run floor. GPU gap capacity only.
- **P-TAX** (`7960057a…`): partial correlations of the self-collision tax fraction with atlas
  residuals and survival, controlling for the feasibility flag; paper claim only if the heldout T2
  CI excludes zero on ≥ 2 arms; hygiene finding regardless; no reward changes anywhere. CPU, this
  week.

## D4 — writing-first window (now → Sept 15)

Primary work product: the paper. Companion note submittable Sept 5; flagship full draft with slots
Sept 12. Flagship spec (titles ×5 for review, decomposition spine, section list with
complete-vs-slot marking, pre-registration table as first-class exhibit, sealed-vs-exploratory
labels on every table, figures F1–F7 with generating scripts recorded, RSS format, appendices for
G0 / N5 calibration / screen validation) — lives in `paper/00_outline.md` (updated) and
`paper/flagship/`. Red-team pass Sept 5–12 → `paper/RED_TEAM.md`.

## Schedule

| window | work |
|---|---|
| Aug 19–22 | seals (done: D1, P-SIGN, P-TAX); run P-TAX; tool repo; upstream drafts for approval; flagship §3–§6 prose |
| Aug 23–Sept 5 | companion note complete; flagship §1–2, §7, §9–10 + pre-registration table; P-SIGN iff GPU gap |
| Sept 5–12 | full flagship assembly with slots; red-team pass |
| Sept 15+ (GPU order) | relaunch N3 chain — **before relaunch verify resume safety**: config re-loaded from the frozen resolved artifact, hash-checked, seeds confirmed against the seal; N3 readout → seal + run N7 → E3 under addendum v2 → E10 → E4 budget permitting; measure realized GPU-hours on N3 and re-plan from that number |
| Dec 1 | results freeze; figures-only GPU thereafter. RSS 2027 target, CoRL 2027 fallback |
| ongoing gaps | LUCID-correlation (PhysFrag's surviving test; small-N caveat wherever cited) |

## Writing rules

No claim without an artifact path. Effects with CIs. Pending results written as sealed-prediction +
confirmation criteria + slot date. Instrument failures and withdrawn verdicts narrated plainly.
Never let narrative smoothness override the sealed record.
