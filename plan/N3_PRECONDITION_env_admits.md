# N3 analysis precondition — does the environment admit the kneel/crawl skill? (2026-08-18)

**Tool:** `tools/env_admits_kneel.py`; outputs `reports/N3_env_admits_{playback_g1.0,follow_g1.0,follow_g3.0}.csv`.
Probe clips `plan/N3_probe_clips.txt` (#44, two matched-easy, three ground16 members), start offsets
{0, 2, 3, 4, 6} s, 3 s windows, 8 episodes each, training-distribution DR on, no pushes.

| oracle | #44 | CMU_76 (easy) | BMLhandball (easy) | KIT_3 kneel_down_to_crawl02 | BMLmovi_36_2 | Eyes hamada bended_knees |
|---|---|---|---|---|---|---|
| **kinematic playback** (robot teleported onto the reference each step; terminations evaluated on it) | 1.00 at every offset, err 0.010–0.012 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| PD mocap-follow, nominal gains (action ≡ reference joint pose) | 0.00 everywhere (0.7–1.1 s) | 0.00 everywhere (0.3–1.1 s) | 0.00 (0.2–0.4 s) | 0.00 at 0–3 s, **1.00 at 4–6 s (kneeling)** | 0.00 | 0.00 |
| PD mocap-follow, gains ×3 | 0.00 | 0.00 | 0.00 | 0.88–1.00 at 3–6 s | 0.00 | 0.00 |

Reading.
1. **Terminations do not fire on the reference itself** — playback survives every clip and offset
   with 4–13 mm error, so `anchor_pos` / `anchor_ori` / `ee_body_pos` are not sized against kneeling
   by construction. The env admits the skill at the termination level.
2. **The naive PD-follow oracle is not a "perfect tracker" for a floating-base humanoid**: it falls
   within ~1 s on *every* clip, including the easy walking/handball clips, at ×1 and ×3 gains —
   open-loop joint following has no balance feedback. It therefore cannot discriminate kneeling
   from standing. Where it does discriminate, it points the *other* way: the only survivals of the
   open-loop follower are the **kneeling** offsets of KIT_3 kneel_down_to_crawl02 (statically stable
   posture) — kneeling is easier to hold open-loop than standing.
3. Dynamic admissibility under the sim's own contact model (frictionless non-foot geoms) was
   established by N1's torque-limited contact LP: the kneel/crawl phase of #44 is supportable
   within actuator limits with feet μ 0.6 and knees μ 0 (unsupported residual 0 N in every frame
   1.75–7.25 s).

**Precondition met** on the two channels that can be checked without a trained controller
(terminations, contact-supported dynamics). N3's augmentation result reads as a data/coverage
result. What N3 cannot rule out is a *learning* obstacle (reward shaping, exploration) — that is
exactly what the pre-listed null follow-ups cover.

## Pre-listed N3 null follow-ups (written before N3 runs; in order)

If E1 fails (both keystone seeds < 0.25 on the kneel/crawl phase) while E4/E5 are as predicted:
1. **Exposure mass insufficient** — 16 clips at ≈ 14 % of uniform mass may be too small a dose.
   Follow-up: grounded sampler with the family's floor raised (targeted mixing, `clip_uniform_ratio`
   on the ground category), one seed; prediction: E1 recovers if dose is the issue.
2. **Within-family start-phase curriculum** — start episodes inside the feasible kneel/crawl phase
   of the family clips (stratified starts in training, not evaluation) so the policy sees the
   posture without the infeasible descent; one seed.
3. **Environment constraint** — none found at the termination or contact level (above); if 1–2
   also fail, the remaining candidates are reward shaping (self-collision penalty −10 with knees
   and hands on the floor; joint-limit penalty in deep flexion) — check the per-term reward rates
   the oracle logged (`r_self_collisions`, `r_joint_limit`) for the ground16 clips before touching
   any weight.
None of these expands the bank; all are single-seed, gap-capacity, post-Sept-15 unless a window
opens.

## Addendum (same day): the self-collision penalty fires on reference poses — bank-wide, not kneel-specific

The playback oracle logged the reward-term rates on the reference itself. `self_collisions`
(weight −10, force threshold 10 N) is charged **on the reference poses**: #44 −2 to −4.6 per step
(offsets 0/2/3/6 s), but also CMU_76 −8.7 (offset 0), BMLhandball −5 to −6, and Eyes hamada
bended-knees −11 to −21. Static self-penetration on the reference (`reports/N3_candidate_selfpenetration.json`,
frames with any robot–robot penetration > 1 cm): mixed100 sample median 10 %, 75th pct 20 %, 90th pct
65 %; #44 30 % (hands into hips/thighs); ground16 members 0–31 % except the three Eyes_Japan
sit/stand clips at 62–75 % (hands on hips, up to 9 cm deep). This is a **retargeting artefact
(hands penetrating hips/thighs) already present across the bank**, i.e. a reward tax the trained
policies already live with; it is not a kneel-specific constraint and the kneel/crawl frames of
#44 (2.5–7 s) carry none. Decision: ground16 stays as sealed; the per-clip self-penetration fraction
is recorded as an analysed covariate for E5, and "reward tax on the reference" is the concrete form
of null follow-up 3. Upstream note (retargeting pipeline): hand–hip interpenetration and airborne
transitions are the two systematic defects the feasibility screen finds; both belong in the same
issue as the sampler note.
