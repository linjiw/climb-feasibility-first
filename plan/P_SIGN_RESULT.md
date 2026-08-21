# P-SIGN result — motor sign-reversal generality (run 2026-08-20)

**Verdict: sealed fail.** The three-part rule in `plan/PREREGISTRATION_P_SIGN.md` (`c7916e8c…`)
does not fire (`reports/P_SIGN/run0/p_sign_summary.json`; run sentinel
`reports/P_SIGN/run0/COMPLETED`).

| criterion | required | result | verdict |
|---|---:|---:|---|
| (i) family clips with airborne S ≥ +5 mm and bootstrap CI > 0 | ≥ 8/12 | **7/12** | fail |
| (ii) feasible controls with whole-clip \|S\| < 2 mm | ≥ 8/12 | **4/12** | fail |
| (iii) \|S(airborne)\| ≥ 3×\|S(standing)\| among (i) clips | all passing (i) | **2/7** localised | fail |

The family response is heterogeneous: seven clips show the predicted positive airborne effect,
but one is significantly negative (−4.9 mm), several miss +5 mm, and most positive cases are not
airborne-localised. Feasible controls are also not clean: eight exceed the sealed 2 mm whole-clip
bound. The per-run identical-physics floors are published in the same summary and do not rescue
the criteria.

The two original #44 replications remain exploratory observations (+15.0/+16.0 mm airborne), but
this experiment does not generalize them into a reference-infeasibility signature. The outcome is
consistent with motor sensitivity depending on posture, policy state, or transition dynamics in
addition to reference feasibility.

## What must not be claimed

- Do not present gain tightening as a rollout-only infeasibility detector or runtime guard.
- Do not say the sign reversal is family-general or specific to airborne windows.
- Do not use the 7/12 directional count as a near-pass; all three sealed criteria were required.

Disposition: keep one parked exploratory paragraph for the two #44 cases. Downgrade the companion
and flagship deployment prediction, and retain N7's repaired-clip comparison only as a narrow
mechanism probe rather than a load-bearing falsifier.
