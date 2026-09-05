# DFRP fixed-policy tracking validation

Status: prepared, not measured. No policy CSV has been read or generated.

The pre-outcome `design.json` binds the 22 qualified repairs, four unchanged
controls, historical motion identities, common raw fidelity reference, conditions,
evaluator, and analyzer. There are 656 paired conditions per arm: 644 full
three-second windows and 12 shorter windows. Two clips overlap Exact Uniform
training. The checkpoint is fixed to seed 1, iteration 3999 before evaluation.

Execution order: E4 terminal decision → exact CUDA payload recovery → raw and
repaired evaluation → identity-checked paired analysis. E4 and E3 share an
exclusive execution lock and the existing 14,000-MiB GPU-availability gate.
CPU recovery was rejected (0/26 historical NPZ hashes matched); all 26 upstream
source arrays have verified Git LFS hashes. Recovery products stay in ignored
`bank/dfrp_validation_recovery`, separate from the active E4 bank.

Verification:

```bash
mjlab-1.6.0/.venv/bin/python -m pytest tests/test_dfrp_policy_validation.py tests/test_e4_continuation.py -q
mjlab-1.6.0/.venv/bin/python tools/run_dfrp_policy_validation.py --prepare-only
sha256sum --check --status plan/G_SEGMENT_FREEZE.sha256
git diff --check
```

All 18 tests pass. Tests cover same-checkpoint/common-reference commands,
missing trials, reference/checkpoint/software/randomization mismatch, retained
failures, explicit survivor denominators, equal clip weighting, missing payload
rejection, and refusal to launch while E4 is active. Preparation starts no simulator.

`paper/figures/f_dfrp_tracking.py --synthetic --out /tmp/climb-dfrp-figure-synthetic`
also passes and was visually inspected. The synthetic image is not a research
result and is not published. After validated measurement, the worker renders all
26 clips with a complete clip-key CSV, including regressions and unchanged controls.

Launch command (one instance only; waits for E4):

```bash
mjlab-1.6.0/.venv/bin/python tools/run_dfrp_policy_validation.py --wait-e4 --source-repo /tmp/fleaven-tree.gkaMLh/repo
```

The comparison estimates a windowed reference-assignment effect for one policy,
not full-sequence execution, a training benefit, or seed-level generalization.
All failures and empty survivor strata remain visible. Fidelity is also reported
on paired complete-window survivors, not the earlier pilot's common-frame set.
