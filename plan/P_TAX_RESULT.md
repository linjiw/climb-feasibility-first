# P-TAX result (run 2026-08-19, against seal `7960057a…`)

**Verdict: hygiene finding only — the sealed rule does not fire.** No paper claim.

Tax fraction (reference frames with robot–robot penetration > 1 cm; `reports/P_TAX_tax_fractions.csv`,
n = 200): median 0.126; 53 % of clips exceed 0.10. The artefact is widespread, as the playback
oracle indicated.

Partial Spearman correlations controlling for the feasibility flag (2,000-draw bootstrap CIs;
`reports/P_TAX_result.json`):

| test | population | partial ρ | 95 % CI |
|---|---|---:|---|
| T1 tax vs atlas LOO residual | train, fixed start | −0.156 | [−0.384, +0.022] |
| T1 | train, random start | −0.141 | [−0.366, +0.020] |
| T2 tax vs difficulty | train fixed / random | −0.006 / −0.055 | both cross 0 |
| T2 (sealed decision) | heldout, uniform | −0.039 | [−0.324, +0.072] |
| T2 | heldout, adaptive | −0.151 | [−0.401, **−0.032**] |
| T2 | heldout, grounded | −0.089 | [−0.391, **−0.026**] |

Sealed rule required *positive* CIs excluding zero on ≥ 2 heldout arms: **0/3.** Where the CI does
exclude zero the sign is negative — interpenetration-taxed clips are, if anything, slightly
*easier*, consistent with the anatomy (hands-on-hips poses occur in quiet, slow clips). The
self-collision reward tax is real, bank-wide, and charged on the reference itself, but it does not
shape difficulty beyond what feasibility and the atlas already carry.

Disposition: one paragraph in the companion note's recommendations ("reward terms should be
audited against the reference, not only the policy"), a row in the pre-registration table
(outcome: null, as sealed), and the masked-penalty ablation stays in `PARKING.md` for post-freeze
work with even weaker motivation.
