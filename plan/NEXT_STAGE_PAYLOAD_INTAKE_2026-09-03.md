# Next-stage blocker resolution — exact Phase-G payload intake

**Status:** exact licensed payload restored and verified 900/900, 2026-09-04.
This is an unsealed research note. It does not amend a sealed protocol or report a new policy
outcome.

## Decision

Proceed with the Phase-G **G2 learning-progress versus G1 exact-uniform** experiment. The
manipulated variable must be allocation alone; changing the retargeter, frame convention,
grounding, or file identities would change the experimental substrate and destroy that causal
contrast.

The payload blocker is now closed. `tools/restore_phase_g_bank.py` verified all 800 training and
100 disjoint evaluation files and created the ignored `bank/amass` symlink only after all 900
SHA-256 identities passed. No motion data or machine-specific intake receipt is committed.

## Evidence for the diagnosis

- `reports/g_segment/unit_table.json` binds 800 training motion files by SHA-256, containing
  1,184 admissible units and 368,951 legal starts.
- `reports/g_segment/panel/panel_manifest.json` binds 100 evaluation motion files by SHA-256.
  Their name overlap and content-hash overlap with the 800 training files are both zero, hence
  the full experiment requires 900 unique files.
- A read-only search of `/home/linjiw`, `/data`, `/mnt`, and `/scratch` found neither the
  historical `bank/amass` directory nor the historical `train_converted_complete` retarget
  source. `/data`, the location named by the old workspace, is not mounted.
- The repository and its remote intentionally omit the approximately 14 GB retargeted payload.
  Existing aggregate screens and segment sidecars do not contain the per-frame joint trajectories
  required to reconstruct it.
- The official [AMASS access page](https://amass.is.tue.mpg.de/register.php) requires the user to
  register and accept its terms. The official
  [whole_body_tracking instructions](https://github.com/HybridRobotics/whole_body_tracking#motion-data)
  tell users to gather motion datasets while respecting the original licenses and manage their
  own reference-motion registry; they do not provide CLIMB's exact historical retarget.

## Resolution record — 2026-09-04

The researcher-supplied licensed AMASS subsets were paired with the public
[retargeted source tree](https://huggingface.co/datasets/fleaven/Retargeted_AMASS_for_robotics)
`fleaven/Retargeted_AMASS_for_robotics` at immutable commit
`275c4c4a028cadf5241c10a613c2f11913531ad2`. A path-only audit mapped every one of the 900 Phase-G
targets to exactly one Unitree-G1 source array; there were no missing or ambiguous names. This was
not accepted as a substitute on provenance alone. It was accepted only after reconstruction
reproduced every already-committed Phase-G output hash.

The recovered historical serialization is `numpy.savetxt(..., delimiter=",", fmt="%.8f")`,
followed by `tools/build_motion_bank.py --input-fps 120 --infer-fps` and
`tools/ground_align_bank.py`. The source set exercises 59, 60, 100, 120, 150, and 250 Hz rates.
The first three conversions in a fresh MJLab process exhibit a warm-up transient; clips 4–900
matched immediately, and rebuilding those first three after three disposable warm-up clips
produced their sealed hashes. The final intake result is:

```text
required=900  verified=900  missing=0  mismatched=0  pass=true
strict calibration preflight: 18 ok, 3 warnings, 0 blockers
```

Local, ignored provenance receipts bind the 900 source paths and arrays without publishing motion
data. The source receipt SHA-256 is
`cdb8d5e37a60ef41a985b634dcc2ef962128c9050e8a854af26ab3447145fc53`; the final intake receipt
SHA-256 is `f9b6d680064a9a033e11fbca9db9ebef5945ce4bd086f0712c2403dc7920c20c`.

## Resolution contract

The researcher supplies one local directory obtained under their own access. Verification occurs
before any repository link is created:

```bash
mjlab-1.6.0/.venv/bin/python tools/restore_phase_g_bank.py \
  --source-dir /absolute/path/to/amass_g1_npz_bank \
  --scope full \
  --link-destination bank/amass \
  --json-out reports/g_segment/local_bank_intake.json
```

The command:

1. validates the canonical unit-table identity and the evaluation-panel manifest;
2. requires all 800 training and 100 disjoint evaluation files;
3. streams and compares all 900 SHA-256 digests;
4. creates a single ignored directory symlink only after every identity passes; and
5. optionally writes an ignored local receipt containing machine-specific paths.

It refuses to replace an existing directory or a symlink that points elsewhere. It neither
downloads nor copies motion data. For a calibration-only source, use `--scope calibration`, but
that does not satisfy confirmation or contact-instrument evaluation.

After successful intake:

```bash
source research.env
mjlab-1.6.0/.venv/bin/python tools/research_preflight.py \
  --g2-stage calibration --verify-motion-hashes --strict
```

The 50-iteration, endpoint-blind 12-setting treatment-separation screen is then the next compute
action. No evaluation return, survival, MPKPE, orientation error, or TrackingScore may be read
while choosing the ALP setting.

## No-substitution rule

Public derivatives such as other AMASS-for-G1 retargets are not valid drop-in replacements here.
The pinned source tree in the resolution record was accepted only because it reproduced all 900
committed outputs byte-for-byte. A different retarget would fail those identities and entangle
allocation with motion preprocessing; it belongs in a separately registered external-validity
replication after Phase G.

## Prioritized experiment cards

| Priority | Consumable object | One changed variable | Gate / endpoint | State |
| --- | --- | --- | --- | --- |
| P0 | Verified 900-file local payload receipt | payload availability only; no experiment outcome | every required SHA-256 passes | **complete: 900/900** |
| P1 | ALP calibration ledger and independent-validation decision | exploration ratio / progress floor within the finite predeclared grid | TV in `[0.05, 0.15]`, effective units ≥12, top-1 ≤0.05, no invalid or censored mass | next compute action; no endpoint access |
| P2 | Blinded contact-proxy validation report | proxy validity, policies untouched | held-out event gates in `G_CONTACT_TIMING_VALIDATION.md` | runnable after P0 and independent labels |
| P3 | Hash-complete three-seed G2−G1 result | allocation rule only | feasible-hard liveness-weighted TrackingScore; survival and common-survivor safeguards | requires P1, proxy disposition, footprint, and Phase-G seal |
| P4 | G1 actuator-consequence bridge | reference feasibility only | saturation, thermal/current proxy, torque and contact-force traces | follows the allocation result; separate protocol |

This ordering follows the instrument-first rule: payload identity and manipulation validity must
be established before policy endpoints are opened.

## Provisional contribution statement

1. **A feasibility-first screen** that turns raw retargeted humanoid motions into auditable
   admissibility decisions.
2. **A segment-native evaluation standard** with 1,184 exact training units, 368,951 legal starts,
   and 2,800 paired held-out conditions.
3. **A grounded allocation test** comparing learning-progress and exact-uniform sampling on one
   identical feasible substrate, with treatment-separation and provenance gates before outcome
   interpretation.

These are proposed paper contributions, not claims that G2 wins.

## Claim–evidence map

| Candidate claim | Evidence required | Current status | Permitted wording now |
| --- | --- | --- | --- |
| The old adaptive pilot tested allocation | TV manipulation on the pilot | measured TV 0.014; gate failed | it did **not** identify the allocation effect |
| ALP creates a distinct treatment | endpoint-blind screen plus independent seed | unrun | pending |
| ALP improves feasible-hard precision | sealed paired G2−G1 result | unrun | no claim |
| Contact timing is a valid secondary metric | blinded held-out manual event labels | instrument ready; labels absent | exploratory proxy only |
| Exact-uniform is the recommended default | passed manipulation plus TrackingScore and survival CIs below SESOIs | unrun | conditional kill-rule outcome only |
| Newton disagreement predicts valid-motion difficulty | sealed Newton predictive gate | measured failure | rejected for curriculum use |

## Reproducibility boundary

Aggregate reports still cannot synthesize the trajectories. This recovery succeeded because an
independent source tree reproduced every final file identity through the historical conversion
sequence. Any future recovery must meet the same 900-hash contract; path similarity, feature
agreement, or a different AMASS-to-G1 retarget remains insufficient.
