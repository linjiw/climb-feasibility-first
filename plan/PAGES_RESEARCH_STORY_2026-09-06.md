# CLIMB research story and public evidence — 6 September 2026

Classification: measured simulation training allocation and development integrity;
exploratory historical repair comparison; pending policy utility. This addendum
changes no sealed contract, sampler, threshold, seed or scientific queue.

## Research goal and argument

Determine whether allocating exact, model-admissible practice by relative progress
improves held-out Unitree G1 motion tracking at equal training transitions, and
which admission, estimator and physical assumptions govern that result.

The proposed contribution is (1) an auditable exact-support interface with
50-step trials; (2) a four-arm, three-seed policy comparison; and (3) a bounded
account of admission value, apparent progress and physical sensitivity. Only the
interface and allocation intervention currently have the evidence described here.
Progress sampling itself is not claimed as a new invention.

The refactored homepage follows problem → findings → controlled comparison →
mechanism hypotheses → conditional research plan → working abstract → evidence.
It explicitly explains how each result informs a future training intervention.
The previous homepage and earlier manuscript/study pages remain accessible as
dated historical records. Their evidence is not pooled with the new campaign.

## Latest exported experiment state

Snapshot: **6 September 2026, 22:17 EDT**. Ten of twelve training jobs have
completed and independently reproduced their original training gates across
**410 saved checkpoint states**. U23 is running (latest saved iteration 1100 at
capture); A23 is queued. No held-out endpoint has opened. All four supervisors
remain active at the publication checks; active jobs continue independently of
this static page.

| Arm | Seed 21 mean TV | Seed 22 mean TV | Seed 23 mean TV |
| --- | ---: | ---: | ---: |
| U | 0 | 0 | Pending |
| A | 0.029759170 | 0.029338594 | Pending |
| R | 0.083484949 | 0.082491997 | 0.082332844 |
| D | 0.083910689 | 0.085865093 | 0.083983853 |

TV is half the summed absolute allocation probability difference from the
prior. Each mean uses 37 saved states at iterations 400–3999. All 41 saved states
per completed run replay; invalid starts, invalid reference frames and censored
resets are zero. Correlated checkpoint states are not independent training seeds.
A's weak allocation is allowed by its frozen comparator rule.

The new three-panel figure shows every completed confirmation history. R changes
exposure earlier, while D starts near the prior and increases contrast later.
Similar average TV therefore does not identify identical exposure schedules or
useful task ranking. The curves are allocation histories, not tracking learning
curves. Incomplete U23/A23 histories are excluded rather than imputed.

## Claim-to-evidence map

| Claim and scope | Evidence exported | Interpretation / next intervention |
| --- | --- | --- |
| Exact support: 800 motions, 1,184 admitted units, 368,951 starts; zero recorded invalid/censored events in completed runs | Current campaign contract and independently replayed gates, summarized in `docs/assets/progress-2026-09-06/research_snapshot.json` | Hold support fixed for the sampler comparison; later isolate exclusion with matched H1. Model admissibility is not hardware feasibility. |
| Earlier E4 mean TV 0.029659 failed its 0.05 gate | Preserved 5 September JSON export and E4 disposition | `not_tested`, not a measured tracking null; motivates relative scale correction. |
| Repair: 22/26 screen qualifications; fixed-policy TrackingScore difference −0.001003, clip-bootstrap 95% CI [−0.008588,+0.008020], 26 clips and 656 paired conditions per arm | `docs/assets/relative-progress/research_snapshot.json` | No aggregate tracking gain demonstrated. Score reference changes before adopting them as training improvements; one fixed policy is not a retraining study. |
| Current R and D pass all three seeds' allocation checks | Current JSON, 410-row allocation CSV and PNG/PDF figure | Establishes changed exposure. Held-out utility and progress-specific superiority remain untested. |
| Development R11/R12 declining-estimate excess mass 46.6%/46.8% | Earlier development record, discussed in fixed relative-progress design | Fraction of positive excess probability mass, not all training samples. Independent signal measurement and equal-budget practice branches are needed to distinguish noise and recovery. |
| CPU H1 and physical-lifecycle development checks pass | `docs/assets/progress-2026-09-06/development_evidence.json`, with source hashes | Measurement infrastructure only. Full H1, CUDA conformance, full S1 and hardware/HIL results remain pending. |

Public exports contain aggregate telemetry and source artifact identities. Full
local checkpoints, licensed motion payloads and unfinished source changes are not
included in this publication. Hashes identify the preserved local evidence; this
is not a claim that the public export alone reproduces simulator training.

## Fixed confirmation and how findings will be used

U/A/R/D × seeds 21/22/23; 512 environments; 4,000 PPO iterations; checkpoints
1000/2000/3000/3999. Evaluate 100 held-out clips, including 25 feasible-hard, with
2,800 paired conditions per cell. All twelve training gates precede 48 evaluation
cells. Primary final R−U feasible-hard TrackingScore gain must be at least +0.02,
with a positive lower **two-sided 95% paired seed-level t bound, df=2**, and an
all-panel lower bound above −0.01. The supplementary paired hierarchical bootstrap
does not replace the primary decision. Three seeds limit precision.

1. **If primary benefit passes:** report the declared simulation effect; inspect
   R−D before a progress-specific claim; prioritize admission and sensitivity tests.
2. **If only intermediate learning curves favor R:** report an exploratory efficiency
   lead, with explicit target non-attainment; freeze a separate prospective
   efficiency study before making that the confirmatory contribution.
3. **If the target-sized benefit is ruled out:** preserve that bounded conclusion;
   investigate signal quality and practice utility before another allocator campaign.
4. **If intervals stay wide:** retain an inconclusive result. Any further replication
   needs a separate design; more clips are not more trained policies.
5. **If integrity or manipulation gates fail:** preserve the declared invalid or
   not-tested disposition and endpoint-access rule.

## Next-stage execution plan

- Complete active confirmation; then run its bound analysis and queued efficiency
  postprocessor, which must reproduce the original complete analysis first.
- Run the frozen-policy instrumentation pilot after confirmation. It checks recording
  and inference immutability; independent stationarity/noise measurement and causal
  practice branches require separate designs. Those results would motivate a future
  uncertainty-aware or recovery-oriented sampler, not a change to the current arm.
- H1: compare D admission on/off using a common 800-clip candidate partition. CPU
  training/evaluation, statistical ordering and cell provenance preparation pass;
  full training remains disabled until production integration, complete fresh-seed
  audit, GPU smokes and a separate freeze. Proposed budget: six runs and 24 cells.
  This isolates exclusion within common feasibility-derived boundaries.
- S1: validate CUDA lifecycle after confirmation and the pilot (nine development
  cells queued). Proposed full sensitivity study: all twelve final policies × eight
  conditions = 96 cells; unchanged evaluation, command delays 5/10/20 ms, knee-only
  caps 120/90 N·m, and foot friction 0.3/1.2. These are stress levels, not calibrated
  hardware distributions. Retain startup pairing, all failures and exposure. Full
  evaluation remains pending a separate validated adapter and freeze.
- Physical evidence: prepare 3–5 motion families using reference kinematics before
  inspecting policy videos; include turning, crouching and dynamic stepping. Keep all
  attempts, residuals and interventions. Hardware access and identified platform
  calibration remain unconfirmed. HIL supports only its included components;
  simulation sensitivity does not demonstrate Sim2Real.

## Publication verification

- `mjlab-1.6.0/.venv/bin/python reports/pages_update_2026-09-06/export_progress.py`:
  exact replay of ten original training gates; 410 saved states; unchanged complete
  376-file runtime inventory. No policy outcome reads.
- `mjlab-1.6.0/.venv/bin/python reports/pages_update_2026-09-06/export_development.py`:
  hash-verified calibration, H1 and CPU lifecycle summaries, without raw payloads.
- Figure generated by matplotlib from the public CSV. The render script and detail
  update script are one-time publication preparation, not an automatic live monitor.
- `node reports/pages_update_2026-09-06/check_pages.cjs`: six pages × desktop/mobile ×
  light/dark = 24 views. Local files/anchors, images and JavaScript errors checked;
  keyboard interaction and no-JavaScript fallback checked. Resolved hidden-control
  display and long inline-code overflow on older draft pages.
- `git diff --check`; both original seals; complete runtime inventory and follow-on
  binding checks. No frozen scientific source is edited.

Screenshots: [desktop homepage](../reports/pages_update_2026-09-06/index_1440_light.png),
[mobile dark homepage](../reports/pages_update_2026-09-06/index_390_dark.png),
[confirmation evidence](../reports/pages_update_2026-09-06/relative-progress_evidence.png),
[research roadmap](../reports/pages_update_2026-09-06/index_evidence.png).
Publication uses a separate checkout and an explicit file list, preserving unrelated
local research work. Deployment completion and live byte checks are recorded in
`reports/pages_update_2026-09-06/deployment_verification.json` after publication.

## Deployed publication

The research site was published in commit
`99cb95ad9965956e5aaca36d99e5d32fc114cf8d`. GitHub Pages reports the build as
`built`. All fourteen checked public pages/assets return HTTP 200 and match the
reviewed local bytes, including both research pages, historical pages, styles,
script, JSON exports, CSV and PNG/PDF figure. The deployment receipt is preserved
in the report directory linked above. The page remains a dated 22:17 EDT snapshot;
training continues independently.
