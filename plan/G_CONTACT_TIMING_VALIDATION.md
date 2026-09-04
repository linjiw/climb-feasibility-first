# Phase-G contact-timing instrument validation

**Status:** unsealed, outcome-blind instrument protocol, 2026-09-03; Phase-G v1
disposition recorded 2026-09-04. No contact-timing validation result exists.
`plan/G_CONTACT_TIMING_DISPOSITION_2026-09-04.md` freezes the metric as
exploratory-only for Phase G v1. This protocol does not amend a sealed result.

## 1. Construct and boundary

The target construct is **agreement in foot touchdown and liftoff timing** between a policy
rollout and its retargeted G1 reference. The AMASS→G1 files do not contain force-plate contact
truth. Therefore `tools/build_reference_contact_labels.py` initially produces only an
**exploratory kinematic proxy** from each foot's signed collision-geometry clearance to a
`z=0` plane and ankle-roll-origin speed. The proxy must not be described as physical contact
accuracy, ground-reaction-force accuracy, or dynamically correct support.

The fixed proxy is:

- enter contact at clearance ≤ 0.010 m and speed ≤ 0.250 m/s;
- remain in contact while clearance ≤ 0.020 m and speed ≤ 0.500 m/s;
- merge interior binary runs shorter than 3 source frames;
- score left/right foot and touchdown/liftoff separately;
- one-to-one chronological event matching at ±2 frames; the Phase-G sources are 50 Hz, so this
  is ±40 ms;
- ignore the state at the first frame as an event. Only transitions internal to the scored
  interval count.

These thresholds are frozen before viewing manual labels and are not tuned on either split.
Clearance and speed traces are retained for diagnosis, but changing a threshold after labels
are viewed creates a new instrument version and requires a new untouched validation panel.

## 2. Outcome-blind panel

`reports/g_segment/contact_validation/panel.csv` fixes 20 clips without policy outputs. Within
each already-frozen feasible-hard/remainder stratum, clips are ordered by
`SHA256(20260903:clip)`; the first 10 are taken. Ranks 1–5 in each stratum form a 10-clip
development split and ranks 6–10 form a 10-clip held-out validation split. Its adjacent
manifest binds the strata, panel, source-motion hashes, selector, and output.

The development split is for rater training and codebook clarification only. Proxy thresholds,
matching tolerance, aggregation, and pass gates may not change after any development label is
opened. The held-out split remains inaccessible to the proxy author until both raters finish
and hash their independent annotation files.

## 3. Reference rendering and annotation

After the licensed bank is restored and all 20 source hashes pass:

1. Render each reference alone at native 50 Hz from front-oblique and sagittal synchronized
   views with frame number and left/right foot identity. Do not display proxy masks, policy
   rollouts, feasibility features, clip stratum, or training/evaluation results.
2. Two raters independently mark every observable `touchdown` and `liftoff` for each foot. A
   touchdown is the first frame of sustained visible surface support; a liftoff is the first
   frame after the last sustained visible support. Sliding without support loss is not an event.
3. Each annotation CSV has exactly
   `rater_id,clip,foot,event,frame,uncertain,notes`. `foot` is `left|right`; `event` is
   `touchdown|liftoff`; `frame` is a zero-based integer; `uncertain` is `0|1`. Clips with no
   event still appear in a separate completion ledger so omission is distinguishable from
   incomplete annotation.
4. The raters may discuss the development split after both files are complete and may clarify
   the written codebook. They then independently annotate the sealed held-out split. The
   held-out files are hashed before comparison.
5. Disagreements outside ±2 frames are adjudicated from the same reference-only views by a
   third rater who cannot see proxy labels or policy outcomes. Consensus contains one frame per
   adjudicated event and is separately hashed.

## 4. Validation estimands and gates

All event counts are pooled as micro counts; per-clip F1 values are not averaged. One-to-one
matching prevents duplicate predictions from receiving credit. A clip/foot with no reference
and no predicted event is **not** a perfect score: its event F1 is undefined and it contributes
zero counts. Contact-state IoU is diagnostic only.

The instrument is validated only if the held-out split meets every gate:

| Gate | Threshold | Reason for the gate |
|---|---:|---|
| Held-out consensus support | ≥40 total events and ≥8 in each foot×event subgroup | avoids validating on a sparse or one-sided sample |
| Inter-rater event agreement | micro-F1 ≥0.90 | establishes that the visual construct is reproducible |
| Inter-rater subgroup floor | F1 ≥0.80 in each foot×event subgroup | prevents aggregate agreement from hiding one failed event type |
| Proxy vs consensus agreement | micro-F1 ≥0.85 | minimum agreement for use as a declared policy metric |
| Proxy subgroup floor | F1 ≥0.75 in each foot×event subgroup | prevents a single-foot or touchdown-only instrument |
| Matched timing error | median absolute error ≤2 frames (40 ms) | bounds timing error at the declared matching tolerance |

Uncertain consensus events remain in the primary validation; a sensitivity row excluding them
is descriptive. If consensus support is below its floor, the result is `insufficient_support`,
not a failed or passed instrument. Any other missed gate is `failed_validation`.

## 5. Phase-G use

Until a hash-complete report says `validated`, contact timing is exploratory and cannot affect
the Phase-G positive/null/inconclusive/not-tested verdict. If validated before the Phase-G
seal, evaluation compares the policy foot-sensor contact history with the source-bound proxy:

- score the survived prefix only, aligning post-step observation `k` to reference frame
  `start_frame + 1 + k`;
- exclude the first sampled contact state from event creation on both series;
- report pooled per-foot/event TP, FP, FN, F1, and matched timing error;
- report the number of reference and observed events and survived frames;
- use contact timing as a common-survivor quality metric, never as a replacement for the
  liveness-weighted TrackingScore.

If the instrument fails or cannot be validated before sealing, Table G-F remains labelled
exploratory and no contact-timing result enters the confirmatory verdict. Contact fraction and
switch rate are not substitutes.

## 6. Required provenance

The proxy manifest must bind the panel, every source-motion SHA-256, base G1 XML, builder,
thresholds, and every label artifact. The validation report must bind the validation-panel
manifest, reference renders, independent rater files, completion ledgers, consensus file,
scorer, and proxy manifest. The evaluator metadata and Phase-G run manifest must bind the exact
validated proxy and validation report before any contact endpoint is parsed.

## 7. Result shell

All cells are pending and must remain so until the corresponding artifact exists.

| split | comparison | events / subgroup minimum | micro-F1 | minimum subgroup F1 | median absolute timing error | status |
|---|---|---:|---:|---:|---:|---|
| development | rater A vs rater B | pending | pending | pending | pending | rater training only |
| validation | rater A vs rater B | pending | pending | pending | pending | pending |
| validation | fixed proxy vs consensus | pending | pending | pending | pending | pending |

## 8. Current execution state

Ready now: deterministic 20-clip selection, manifest, proxy construction code, byte-stable
artifacts, reference-only synchronized dual-view renderer, hysteresis/debounce logic, one-to-one
event scorer, evaluator validation gate, and synthetic unit/model/render tests.

The licensed AMASS→G1 payload is restored and all 20 selected source identities are available
under the full 900-file verification contract. The remaining blocker is human coordination:
two independent raters and an adjudicator, with the required independent files and completion
ledgers, are absent. No validation status is inferred from synthetic tests. Phase G v1 therefore
uses the exploratory-only disposition in
`plan/G_CONTACT_TIMING_DISPOSITION_2026-09-04.md`; future human validation remains a separate
instrument study.
