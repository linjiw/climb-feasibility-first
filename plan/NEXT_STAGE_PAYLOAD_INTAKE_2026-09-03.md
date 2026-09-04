# Next-stage blocker resolution — exact Phase-G payload intake

**Status:** engineering path resolved; external licensed payload still absent, 2026-09-03.
This is an unsealed research note. It does not amend a sealed protocol or report a new policy
outcome.

## Decision

Proceed with the Phase-G **G2 learning-progress versus G1 exact-uniform** experiment. Do not
switch to a conveniently available AMASS-to-G1 derivative. The manipulated variable must be
allocation alone; changing the retargeter, frame convention, grounding, or file identities would
change the experimental substrate and destroy that causal contrast.

The infrastructure blocker is now closed: `tools/restore_phase_g_bank.py` provides a fail-closed
local intake path, and `tools/research_preflight.py` distinguishes the 800-motion calibration
scope from the 900-motion full confirmation scope. The remaining blocker is external and exact:
no licensed, hash-matching payload is present on this machine.

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

Public derivatives such as other AMASS-for-G1 retargets are useful datasets but are not valid
drop-in replacements here. A different retarget would fail the committed SHA-256 identities and
would entangle allocation with motion preprocessing. Such a dataset can support a later,
separately registered external-validity replication after Phase G; it cannot resolve this
experiment's missing-payload blocker.

## Prioritized experiment cards

| Priority | Consumable object | One changed variable | Gate / endpoint | State |
| --- | --- | --- | --- | --- |
| P0 | Verified 900-file local payload receipt | payload availability only; no experiment outcome | every required SHA-256 passes | blocked on researcher-supplied licensed path |
| P1 | ALP calibration ledger and independent-validation decision | exploration ratio / progress floor within the finite predeclared grid | TV in `[0.05, 0.15]`, effective units ≥12, top-1 ≤0.05, no invalid or censored mass | runnable after P0; no endpoint access |
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

## Blocker boundary

No additional safe local computation can synthesize the missing trajectories from aggregate
reports. Resolving P0 requires either the exact historical `bank/amass` directory or another
directory whose 900 required files independently match the committed hashes. If only the original
`train_converted_complete` CSV export is recovered, rebuild in a separate directory with the
historical converter and ground-alignment sequence, then accept it only if this intake check passes.
