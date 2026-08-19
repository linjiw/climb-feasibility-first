# Pre-registration — P-TAX: does the self-collision reward tax matter beyond hygiene?

**Sealed:** 2026-08-19, before any partial correlation is computed. Per D3 of the 2026-08-19
directive. CPU only; runs this week.

## Background (already on record, hygiene finding regardless of outcome)

The `self_collisions` penalty (weight −10, force threshold 10 N) is charged on *reference poses*
bank-wide: kinematic playback of the reference collects −0.6 to −21 per step on some clips
(`plan/N3_PRECONDITION_env_admits.md` addendum; `reports/N3_env_admits_playback_g1.0.csv`).
Static anatomy: hands interpenetrating hips/thighs, a retarget artefact
(`reports/N3_candidate_selfpenetration.json`). This is documented hygiene no matter what P-TAX
finds. The question here: does the tax *predict difficulty*, i.e. is a systematic reward bias
shaping what the policy learns, beyond what the feasibility flag already captures?

## Measurement (fixed now)

Per clip, **tax fraction** = fraction of reference frames with any robot–robot contact at
penetration > 1 cm, computed by forward kinematics on the reference (stride 2 frames), same model
XML as the pinned screen. Tool: `tools/selfpen_screen.py` (this seal's companion, written before
results). Populations: tier_mixed100 (n = 100, training-tier difficulty labels) and heldout100
(n = 100, campaign difficulty labels).

## Sealed analyses

With flag = 1[`infeasible_frac` > 0.10] from the pinned screen (`GLOBAL_EVAL_ADDENDUM.md`):

- **T1:** partial Spearman correlation of tax fraction with the intrinsic-atlas LOO |residual|
  (from `tools/analyze_atlas_support.py` T1, uniform-s1, both start protocols), controlling for
  the flag. 95 % CI by 2,000-draw bootstrap over clips.
- **T2:** partial Spearman correlation of tax fraction with per-clip difficulty
  (1 − survival; training tier fixed & random start; heldout campaign it3999 per arm),
  controlling for the flag. Same CI.

Partialling: Spearman on the residuals of rank(tax) and rank(y) after regressing each on the flag.

## Sealed decision rule

The tax becomes a **paper claim** ("reward bias correlated with difficulty beyond feasibility")
only if the T2 partial-correlation CI excludes zero on the heldout population for at least two of
the three arms *and* the sign is positive. Otherwise it stays a hygiene finding (one paragraph in
the companion note's recommendations). T1 is supporting evidence either way.

## Constraints

No reward changes to any existing or sealed arm. A masked-penalty ablation (self-collision penalty
gated off during reference-interpenetrating frames) may be *drafted* for post-freeze work only —
if drafted it goes to `plan/PARKING.md`, not to any run queue.
