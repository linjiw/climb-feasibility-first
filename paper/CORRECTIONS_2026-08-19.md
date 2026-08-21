# Corrections, 2026-08-19 — three paper-bound numbers

Found while writing generator scripts for two artifacts that were cited in the drafts but had
**no generator anywhere in the repo** (`grep -rl … tools/` returned nothing). Both were
hand-computed. Writing the reducers reproduced most of their contents bit-exactly and falsified
three claims built on top of them.

None of the affected files were sealed (`plan/SEALS_2026-08-19.sha256` covers
GLOBAL_EVAL_ADDENDUM, PREREGISTRATION_P_SIGN, PREREGISTRATION_P_TAX, RESEARCH_PLAN_v5,
ADVISOR_DIRECTIVE_v6 — none of them), so these are direct edits, not addenda.

Generators now exist and are the provenance going forward:
`tools/analyze_wasted_exposure.py`, `tools/analyze_sat_at_fall.py`. Both refuse to overwrite the
cited artifact and write to a separate path.

---

## C1 — "48.8 % of clip draws to the impossible clip" was a copied key

**What was wrong.** In `reports/wasted_exposure_accounting.json`, `exposure_to_impossible_clip_mean`
is `0.4884832416666667` and `mean_top1_mass` is `0.4884832416666667` — **the same float, digit for
digit**. It is a copied key, not an independent measurement. The two quantities are different:
mean top-1 mass is the mass of whichever clip leads at each iteration; it is an *upper* bound on
the mass any one named clip receives.

**Ground truth**, re-derived independently from `logs/campaign/adaptive-mixed100-s{1,2,3}.log`
(`sampling_top1_prob` and `sampling_top1_bin`; the latter is `argmax(p)/num_clips` per
`climb/commands.py:160`, so on a 100-clip bank it is the top-1 clip index):

| seed | mean top-1 mass | #44 top-1 in | mass provably on #44 | peak held by |
|---|---|---|---|---|
| s1 | 0.4980 | 27.2 % | 0.1816 | **clip 66** (0.8842) |
| s2 | 0.4882 | 44.8 % | 0.2884 | clip 44 (0.8698) |
| s3 | 0.4793 | 30.5 % | 0.1878 | **clip 5** (0.8927) |
| mean | **0.4885** | **34.2 %** | **0.2193** | — |

So the impossible clip's share is bracketed **[21.9 %, 48.8 %]**, and in two of three seeds the
peak belongs to a different clip. The original statement overstates by up to 2.2×.

**What survives, and it is the load-bearing claim.** 48.8 % mean top-1 mass is correct as stated
for *a single clip* — the sampler really does concentrate about half of all draws on whichever one
clip is currently winning. The collapse result does not depend on that clip being #44, and is
arguably cleaner without it.

**Edited:** `paper/RESULTS_LOG.md:34`, `paper/flagship/S1_intro.md`, `paper/flagship/DRAFT_full.md`,
`paper/companion/companion_note_draft.md`, `plan/PERFORMANCE_PAYOFF_PLAN.md`.

Reproduce: `bridge/.venv/bin/python tools/analyze_wasted_exposure.py --compare`

---

## C2 — saturation-at-fall was 7/8, not 8/8, and 17.2 % is not the mean

**What was wrong.** "5/29 (17.2 %) at ≥98 % force … 8/8 replicates". The shipped artifact
`reports/effort_sat_at_fall.json` itself carries `sat_frac_max_fall_2.2-3.0s =
[0.172 ×7, 0.138]` and `mean_fall = 0.16810345090925694`.

**Ground truth.** 0.172 × 29 = 5/29; 0.138 × 29 = 4/29. So: **≥ 4/29 in 8/8 replicates, exactly
5/29 in 7/8** (world 7 is 4/29 = 13.8 %), **mean 16.8 %**. 17.2 % is a per-world value, not the
mean. Pre-fall saturation is exactly 0.0 in 8/8 — that part was right.

**Edited:** `paper/RESULTS_LOG.md:35`, `paper/companion/companion_note_draft.md`,
`paper/flagship/S6_screen_at_scale.md`, `paper/flagship/DRAFT_full.md`,
`plan/PERFORMANCE_PAYOFF_PLAN.md`.

Reproduce: `bridge/.venv/bin/python tools/analyze_sat_at_fall.py --compare`

---

## C3 — the per-actuator identity ("wrists, waist") was never measured; withdrawn

**What was wrong.** Several documents named *which* actuators saturate at fall. That information
does not exist in the artifact.

**Evidence.** `tools/g1_clip44_gate.py:242` computes
`sat = (af.abs() >= 0.98*frange[:,:,1]).float().mean(dim=1)` — it averages over the actuator axis
*before* storage. Verified directly: every array in `reports/G1/run0/armA.npz` is `(500, 480)`
(or `(500, 480, 2)` for contact), and **no array carries a 29-length axis**. The claim is
unrecoverable without a new GPU rollout that keeps the per-actuator stream.

**Also corrected in the same pass:** "post-airborne contact event" → "losing foot support". The
artifact shows all eight worlds terminating while `root_z` is still falling; what is measured is
support loss at 2.46–2.54 s, not a contact event.

**Edited:** `paper/RED_TEAM.md` row 18 (✅ → ⚠️ partly, claim withdrawn in place),
`plan/G1_RESULT.md`, `paper/companion/companion_note_draft.md`,
`plan/PERFORMANCE_PAYOFF_PLAN.md`.

---

## Noted, not changed

`infeasible_frac > 0.10` yields **2,442** clips; `>= 0.10` yields **2,443**. The repair census ran
on 2,443 and the drafts cite "65.8 % of 2,443", which is internally consistent with the census;
the prevalence table's 22.8 % uses the strict `>`. Both round to 22.8 %. Changing the census
denominator would require recomputing the recovery fraction, so the operator is documented in
`tools/analyze_wasted_exposure.py --flag-op` rather than silently reconciled here.

---

## Seal-manifest issues found 2026-08-19 (both pre-existing, neither from this session's work)

Surfaced by an independent audit of the sealed record. Reported rather than fixed: repairing a
seal is the author's call, not an editor's.

**S1 — `plan/N3_PRECONDITION_env_admits.md` no longer matches its seal.**
`plan/PREREGISTRATION_N3_coverage.md.sha256:2` records `3c331e18…`; the file hashes to
`569b30f5…`. File mtime 2026-08-18 00:43, seal written 00:41 — so it was edited two minutes
after being sealed and has been broken since. The file is the N3 precondition ("env admits the
skill"), cited as a gate for the N3 causal block that is running now. Either the seal should be
re-issued against the current content with the edit narrated, or the edit reverted.

**S2 — `plan/PREREGISTRATION_G1_clip44.md.sha256` carries two hashes for one filename.**
Both lines name `PREREGISTRATION_G1_clip44.md`; the file matches only the second
(`2a9ceac…`, not `41e4b20c…`). A re-seal appears to have been appended rather than replacing the
original, so the manifest does not say which is authoritative. `sha256sum -c` passes on it, which
is exactly why it went unnoticed.

**Verified clean:** every entry in `plan/SEALS_2026-08-19.sha256` (GLOBAL_EVAL_ADDENDUM,
PREREGISTRATION_P_SIGN, PREREGISTRATION_P_TAX, RESEARCH_PLAN_v5, ADVISOR_DIRECTIVE_v6) hashes
correctly, as does `plan/E_HYG_FREEZE.sha256`. Note the manifest mixes bare and `plan/`-prefixed
paths, so `sha256sum -c` reports spurious failures unless run from the right directory — that
cost me one false alarm before I checked it properly.
