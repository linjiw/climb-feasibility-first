# Composition of the repaired 800-clip bank

**Status:** decided and built. Written 2026-08-19, *before* any training run consumes the bank.
**Artifacts:** `bank/amass_repaired800/`, `bank/tiers/tier_800_repaired.txt`,
`reports/repaired800/manifest.json` (+`.sha256`), generator `tools/build_repaired_bank.py`.
**Manifest payload sha256 `825df57d92a02e2df8ffab11e8e877b919ae13f19a84fdbe181b80c20d702a1f`**
(reproducible across rebuilds; the whole-file hash also covers the wall-clock stamp and so moves).
`tier_800_repaired.txt` is byte-identical to `tier_800.txt` (sha256 `87cbeb8e…`) — N, names and
order are preserved exactly, and the entire difference lives in the bank directory.
**Recommendation: option C — substitute the repaired file for all 99 flagged clips, N = 800,
with a three-way provenance stratum frozen in the manifest.** Option A is materialised alongside
it as a sensitivity arm. Nothing here modifies a sealed list; every path is new.

---

## 0. Why this bank exists

`tier_800` (800 clips) and `tier_800_pruned` (701 clips) differ on *two* things at once: whether
the contaminated clips are present, and how many clips there are. Any performance gap between
them is therefore confounded by "fewer clips ⇒ more gradient steps per clip ⇒ faster apparent
convergence". A repaired view keeps N = 800 and the clip *names* identical to `tier_800`, so it
isolates the contamination axis. That property is load-bearing, and it is what rules out option B
below almost on its own.

## 1. Composition invariant (verified, not assumed)

`tier_800_pruned` is exactly `tier_800` minus the 99 clips whose feasibility screen
(`reports/feasibility_all/feasibility.csv`) reports `infeasible_frac > 0.10` — same clips, same
relative order, no extras in either direction. The threshold is strictly `>`: one clip sits at
exactly 0.100 (`BMLmovi_Subject_62_F_MoSh_Subject_62_F_3`) and is *kept*. All 800 tier clips are
present in the screen CSV. `tools/build_repaired_bank.py --check-only` re-derives and re-asserts
this on every build and aborts if it ever stops holding.

    tier_800  800 clips   sha256 87cbeb8e…
    pruned    701 clips   sha256 4cfb5aea…      (= 800 − 99, order preserved)  ✓

All 99 flagged clips have both a census record and a repaired `.npz`. (The census as a whole has
one hole — `CMU_76_76_02_poses_120_jpos` has a JSON but no `.npz`, hence 2 443 records vs 2 442
files — but that clip is **not** in `tier_800`, so this bank is unaffected.)

## 2. The 21 clips at issue

Of the 99, **78 passed** the pre-registered success budget (`offset_max ≤ 0.15 m` **and**
`infeasible_frac_after ≤ 0.05`) and **21 failed**. The failures split as:

| failure mode | n | what it means |
|---|---:|---|
| offset budget only (`offset_max > 0.15 m`, residual ≤ 0.05) | 11 | repair works dynamically; the root had to move 0.15–0.44 m to get there |
| residual budget only (`infeasible_frac_after > 0.05`) | 9 | still infeasible after repair |
| both | 1 | `CMU_36_36_04` (offset 0.280 m, residual 0.082) |

### 2.1 The scoring subtlety — measured, and it does *not* excuse inclusion

The operator (`tools/repair_contact_projection.py`) triggers on **airborne** frames only
(`mind > gap`, gap = 0.06 m) but the budget is scored on the **full-clip torque-limited LP**. A
frame that is *in contact* yet infeasible — the friction cone and actuator limits cannot deliver
the demanded wrench — receives a zero root offset by construction and is still counted against
the operator. I re-ran the full per-frame screen on all 21 clips before and after repair to
decompose the residual (`reports/repaired800/fail21_contact_diagnosis.json`):

* **9 of the 10 residual failures** have a residual that is ≥ 88 % in-contact (7 of them 100 %,
  i.e. airborne infeasibility driven to exactly 0.000). The airborne defect was fully repaired;
  what remains is a *different defect class* the operator never targeted.
* **8 of the 21** already carried > 5 % in-contact infeasibility *before* repair, so they could
  not have cleared the ≤ 5 % residual gate no matter how well the airborne repair went. The
  budget was unattainable for them ex ante.
* The one genuine under-repair is `CMU_36_36_04` (residual 0.082, of which only 0.029 in-contact
  and 0.053 still airborne).

So the operator is not at fault. **But** — and this is the part that changes the answer — I ran
the same decomposition on a 79-clip uniform sample of `tier_800_pruned` as a control. The clean
bank's in-contact infeasibility is essentially zero: mean 0.0008, median 0.0000, p90 0.0000,
max 0.0266, **0 of 79 above 0.05**. The ≤ 5 % residual bar is one the clean bank clears by a
factor of ~60. The 9 clips are therefore not victims of an unfair gate; they are genuinely
anomalous relative to the bank they would join. The correct reading is *reclassification*, not
exoneration: they are "airborne defect repaired, second untreated defect remains", and any
composition that ships them must say so out loud.

### 2.2 Does the repaired file at least beat the raw one?

Yes, on the pre-registered contamination metric, for every one of the 21 — **weak dominance,
strict for 19**. Two are exact no-ops (`CMU_108_108_13` 0.123→0.123 and `CMU_16_16_35`
0.118→0.118; both received 5–6 mm of offset because their infeasibility was in-contact from the
start). **None is made worse.** Mean `infeasible_frac` over the 21 falls 0.281 → 0.070.

The cost is fidelity. The 12 over-budget clips are out of family with the 78 accepted repairs:

| group | `offset_max` med / p90 / max (m) | peak added downward vel. med / p90 / max (m/s) |
|---|---|---|
| 78 accepted | 0.082 / 0.108 / 0.133 | 0.22 / 0.65 / 1.38 |
| 21 failed | 0.161 / 0.415 / 0.439 | 0.74 / 1.85 / 2.43 |

A 0.44 m root drop is a large edit — but it is large *because the source clip floats 0.44 m*, and
the edit is root-z only: joint angles, body orientations and angular velocities are untouched, so
the tracking reward's joint terms see the original motion exactly. 11 of the 12 reach
`infeasible_frac_after ≤ 0.05`, i.e. inside the clean bank's own norm.

## 3. What each option delivers

Contamination = infeasible frames / total frames (`reports/repaired800/composition_options.json`).
For scale: the 99 flagged clips are 13.3 % of `tier_800`'s frames but carry **84.5 %** of its
infeasible frames; the 21 alone carry **26.0 %** of all contamination in the tier (30.8 % of the
flagged clips' contamination) while being only 21 % of the flagged clips by count.

| option | N | delivered contamination | verdict |
|---|---:|---:|---|
| `tier_800` raw (baseline arm) | 800 | 3.923 % | — |
| `tier_800_pruned` (prune arm) | 701 | 0.699 % | — |
| **A** keep the raw original for the 21 | 800 | **1.692 %** | N preserved; treatment diluted |
| **B** drop them | 779 | 0.694 % | cleanest bank, arm destroyed |
| **C** repair all 99 | 800 | **0.903 %** | N preserved; matched to the prune arm |

**Option B is out.** N = 779 vs 701 reintroduces exactly the clip-count difference this bank
exists to eliminate. It buys 0.2 pp of contamination for the arm's whole purpose.

**Option A vs C** is the real decision, and the numbers make it: under A the repaired arm sits at
2.4× the prune arm's contamination (1.692 % vs 0.699 %). That gap is the same order as the effect
being measured, so a repaired-arm shortfall would be uninterpretable — repair genuinely worse than
pruning, or just the 21 raw clips left in? Under C the two arms are matched on contamination
(0.903 % vs 0.699 %) and differ on N, which is the contrast the arm was built for.

## 4. Recommendation — option C, declared

Substitute the repaired file for **all 99** flagged clips. N = 800, names and order identical to
`tier_800`. Reasons, in order of weight:

1. **It is the only composition that makes the arm answer its question.** A's residual
   contamination confounds the repair-vs-prune comparison it exists to enable.
2. **No clip is made worse.** The substitution weakly dominates the raw original on
   `infeasible_frac` for all 21, strictly for 19.
3. **The failures are not what the label suggests.** 9 of the 10 residual failures had their
   airborne defect fully repaired and fail on an untreated second defect; 8 of 21 could not have
   passed the gate ex ante. Treating "failed the census budget" as "repair did nothing" would be
   wrong.
4. **It matches the deployable policy.** "Run the cheap operator on everything the screen flags"
   is what a practitioner would actually do; that is the policy worth measuring.
5. **Optionality runs one way.** With the strata frozen in the manifest *before* training, A's
   answer is recoverable from a C run by stratified evaluation on the 779 non-failing clips — no
   retraining. The converse is false: an A run cannot recover C's treatment.

**What C is not:** a clean bank. Ten clips ship with 5.1–29.7 % of frames infeasible while in
contact, versus a clean-bank norm of 0.08 % (max 2.7 %). Twelve ship with root displacements of
0.15–0.44 m. Both facts are labelled per clip in the manifest and must be quoted wherever this
bank's results are. The honest claim is "root-projection repair applied to every flagged clip",
not "a feasible bank".

### Strata frozen in the manifest

| stratum | n | definition |
|---|---:|---|
| `original` | 701 | screen `infeasible_frac ≤ 0.10`; symlink to `bank/amass/` |
| `repaired_certified` | 78 | census `success = true` |
| `repaired_over_budget` | 11 | `offset_max > 0.15 m`, residual ≤ 0.05 |
| `repaired_residual` | 10 | residual > 0.05 (9 of them in-contact-dominated; `residual_is_in_contact` flags which) |

Pre-registered secondary cuts, resolvable from the manifest without retraining: evaluate on the
779 (= all but `repaired_residual` ∪ `repaired_over_budget`, recovering A's population), on the
`repaired_certified` 78 alone, and on the 21 as a labelled group.

### The alternative, materialised

Option A is not merely reconstructible, it is built:
`tools/build_repaired_bank.py --fail-policy keep-original --out-dir bank/amass_repaired800_certified
--tier-out bank/tiers/tier_800_repaired_certified.txt --manifest reports/repaired800/manifest_certified.json`
→ 701 original + 78 repaired + 21 flagged-kept-original, N = 800, manifest payload sha256
`34a560e1bbf50990b982c56f2c0efffad8390e20d925a621861958c4a58f93d5`.
Option B needs no new directory: it is `tier_800_repaired.txt` minus the 21, read against
`bank/amass_repaired800/`.

## 5. Validation performed

* `tools/validate_motion_npz.py --dir bank/amass_repaired800` → **800/800 pass** (required keys,
  finite arrays, consistent frame counts, depth-first MuJoCo body order). Same for
  `bank/amass_repaired800_certified` → 800/800.
* **`fps` key present in all 800; all 800 report exactly 50.0** — the specific abort mode in
  `climb/motion_bank.py` (`clips disagree on fps`) cannot fire.
* End-to-end: `MotionBank` constructed on CPU over the overlay using the same
  `os.path.join(bank, name + ".npz")` join that `tools/eval_stratified.py` uses →
  800 clips, 457 072 frames @ 50 fps, built in 40 s. No absolute-path breakage.
* Rebuilt twice from scratch: the manifest payload hash is identical across builds, so the
  overlay is a generated artifact, not a hand-made directory.
* All 800 entries are symlinks, 0 dangling; 701 resolve into `bank/amass/`, 99 into
  `bank/repaired_census/`; all 99 differ byte-wise from their originals (the substitution really
  happened); all 800 file hashes match the manifest.
* Velocity-estimator check: the repair re-derives `body_lin_vel_w` with `np.gradient`, which could
  have introduced a spurious difference between the 99 repaired and the 701 originals. It does
  not — the originals' stored `body_lin_vel_w` already agrees with `gradient(body_pos_w)` to
  ~0.2 % relative (40-clip sample, max 0.8 %), three orders below the contamination signal.
  `body_ang_vel_w` is correctly left untouched (a pure z-translation does not change orientation).
