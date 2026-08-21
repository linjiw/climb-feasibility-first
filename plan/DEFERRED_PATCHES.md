# Deferred patches — applied after the sealed chain

Status: **APPLIED 2026-08-20**, after `reports/E_HYG/EVALS_DONE` appeared and the real
training/evaluation process set was empty. Both patch hashes below matched; both `git apply
--check` calls passed before application. CPU verification passed: four-file `py_compile`, a
direct exposure-count test (startup excluded; uniform episodes/failures nonzero), and old/new CSV
replay through both frozen analyzer readers. The live GPU smoke tests remain pending because
`nvidia-smi` cannot currently communicate with the driver.

| patch | touches | verified |
|---|---|---|
| `reports/patches/exposure_ledger.patch` | `climb/commands.py`, `tools/climb_train.py` | applied; CPU tests pass |
| `reports/patches/eval_saturation.patch` | `tools/climb_eval.py`, `tools/eval_stratified.py` | applied; CPU/schema tests pass |

sha256:

```
bba922be2f5a315cad318b98e86bb962d38956e612af10fc2a1fcf07b7e82f7b  reports/patches/exposure_ledger.patch
45fd2b77335dce6992543edfbcad875b355372a85316757a2355f728cea19092  reports/patches/eval_saturation.patch
```

---

## Why both are blocked right now

The pre-registered N3 + E-HYG chain is running and will keep launching **fresh**
training and eval processes for several more arms (N3 A1-s2, A2 adaptive, A3
random16, the stratified evals, E-HYG uniform-800 and uniform-800-pruned):

```
pid 307992  /data/robotixx/climb/tools/n3_ehyg_chain.sh
pid 456831  mjlab-1.6.0/.venv/bin/python tools/climb_train.py Climb-Tracking-Flat-Unitree-G1 ...
```

`reports/campaign/_frozen/<TAG>/run_campaign.sh` freezes **only itself and
`config.env`** (see the `checksums.txt` beside it). It then runs
`( $PY tools/climb_train.py ... )` from the **live**
repo root. The freeze is a freeze of the *driver*, not of the code the driver
imports.

Verified import resolution for the running interpreter
(`mjlab-1.6.0/.venv/bin/python`):

* `mjlab-1.6.0/.venv/lib/python3.13/site-packages/mjlab.pth` contains the single
  line `/data/robotixx/climb/mjlab-1.6.0/src` → `import mjlab` resolves to
  **`/data/robotixx/climb/mjlab-1.6.0/src/mjlab/__init__.py` (LIVE)**.
* `tools/climb_train.py:20` does
  `sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))`
  → `import climb` resolves to **`/data/robotixx/climb/climb/__init__.py` (LIVE)**.
* `/proc/456831/cwd -> /data/robotixx/climb`.

Consequences, patch by patch:

* **`exposure_ledger.patch`** edits `climb/commands.py`, which is
  live-imported by the training process now running *and* by every arm the
  chain has yet to start. Editing it mid-chain means later arms train against
  different sampler bookkeeping than earlier arms — the arms stop being
  comparable, which is the one thing a pre-registered comparison cannot
  survive. It also edits `tools/climb_train.py`, which the chain re-executes
  for each remaining arm.
* **`eval_saturation.patch`** edits `tools/eval_stratified.py`, which the
  chain invokes directly for the N3 and E-HYG stratified evals, and
  `tools/climb_eval.py`, which `tools/run_campaign_n3.sh` invokes for the
  checkpoint-ladder evals. Editing a script that is mid-run also risks the
  interpreter reading a partially rewritten file.

Neither patch touches `tools/analyze_ehyg.py` or `tools/analyze_n3.py`, which
the chain sha256-verifies at start (`5f8eb56e…`, `b118b2d3…`); editing either
would abort the chain.

---

## Precondition to apply (both patches, same gate)

Apply only when **both** hold:

```bash
# 1. the chain reached its final sentinel
test -f /data/robotixx/climb/reports/E_HYG/EVALS_DONE

# 2. no training/eval process is still alive
pgrep -af 'climb_train\.py|eval_stratified\.py|climb_eval\.py|n3_ehyg_chain\.sh'   # must print nothing
```

`reports/E_HYG/EVALS_DONE` is the last line of `tools/n3_ehyg_chain.sh` before
its completion echo, so it appears only after the final E-HYG stratified eval
returns. As of this writing it does **not** exist: `reports/E_HYG/` is empty and
`reports/N3/` holds only `baseline_s2/` and `baseline_s3/`.

Check both in one shot:

```bash
cd /data/robotixx/climb
if [ -f reports/E_HYG/EVALS_DONE ] && ! pgrep -f 'climb_train\.py|eval_stratified\.py|climb_eval\.py|n3_ehyg_chain\.sh' >/dev/null; then
  echo "SAFE TO APPLY"
else
  echo "STILL BLOCKED"; ls reports/E_HYG/; pgrep -af 'climb_train\.py|n3_ehyg_chain\.sh'
fi
```

## Apply

```bash
cd /data/robotixx/climb
git apply --check reports/patches/exposure_ledger.patch    # expect rc=0, no output
git apply --check reports/patches/eval_saturation.patch    # expect rc=0, no output
git apply         reports/patches/exposure_ledger.patch
git apply         reports/patches/eval_saturation.patch
git diff --stat                                            # expect 4 files changed
```

Both patches apply cleanly in either order and together
(`git apply --check a.patch b.patch` → rc=0); they touch disjoint files.

If `--check` fails later because one of the four files drifted, regenerate
rather than force: the patches were cut against the working tree at commit
`a20fe7a` with a clean `git status`.

---

# Patch 1 — `exposure_ledger.patch`

## What it fixes

Two defects that combine into one silent hole: the per-clip exposure ledger is
**counted only on the adaptive code path** and is **never written anywhere**.

## Evidence it is broken today

`climb/commands.py:143-154` — the tally lives inside `_adaptive_sampling`:

```python
    def _adaptive_sampling(self, env_ids: torch.Tensor):
        """Clip-level failure-weighted sampling: the error-adaptive comparator."""
        terminated = self._env.termination_manager.terminated[env_ids]
        if torch.any(terminated):
            failed = self.clip_ids[env_ids][terminated]
            self._clip_failed_now[:] = torch.bincount(
                failed, minlength=self.motion.num_clips
            ).float()
            self.clip_failures += self._clip_failed_now
        self.clip_episodes += torch.bincount(
            self.clip_ids[env_ids], minlength=self.motion.num_clips
        ).float()
```

`climb/commands.py:137-141` — the uniform path does no such thing:

```python
    def _uniform_sampling(self, env_ids: torch.Tensor):
        self._place(env_ids, self._sample_clips(len(env_ids)))
        self.metrics["sampling_entropy"][:] = 1.0
        self.metrics["sampling_top1_prob"][:] = 1.0 / self.motion.num_clips
        self.metrics["sampling_top1_bin"][:] = 0.5
```

So for a uniform arm `clip_episodes` and `clip_failures` stay at their
`__init__` values (`climb/commands.py:73-74`, `torch.zeros(n)`) for the entire
run, and `per_clip_stats()` (`climb/commands.py:250-260`) returns

```python
        return {
            "clip": list(self.motion.clip_names),
            "episodes": ep,                                   # all 0.0
            "failures": fa,                                   # all 0.0
            "failure_rate": [f / e if e > 0 else float("nan") for e, f in zip(ep, fa)],
            "sampling_weight": self._clip_probabilities().cpu().tolist(),
        }
```

Second half of the defect — `per_clip_stats` has **zero callers anywhere in the
repo**:

```
$ grep -rn "per_clip_stats" /data/robotixx/climb --include=*.py --include=*.sh --include=*.md --include=*.json
/data/robotixx/climb/climb/commands.py:250:    def per_clip_stats(self) -> dict[str, list]:
```

and no run directory or report contains an exposure artifact:

```
$ find logs/ reports/ -iname '*exposure*' -o -iname '*per_clip*' -o -iname '*ledger*'
reports/wasted_exposure_accounting.json          # analytic, not measured — see below
```

`tools/climb_train.py` is a 28-line launcher that calls
`mjlab.scripts.train.main()`; it has no checkpoint hook at all.

## What the patch does

1. **`climb/commands.py`** — adds `_count_exposure(env_ids)` and calls it from
   `_place`, the one method every sampler routes through, *before* `_place`
   overwrites `self.clip_ids[env_ids]`. The tally is removed from
   `_adaptive_sampling` so nothing is double counted.
2. Counting is gated on `self._env.episode_length_buf[env_ids] > 0`, which
   excludes the startup reset. `ManagerBasedRlEnv._reset_idx` calls
   `command_manager.reset(env_ids)` and only afterwards runs
   `self.episode_length_buf[env_ids] = 0`, so the buffer read inside `_place`
   still holds the *outgoing* episode's length. Without this gate the ledger
   would credit `num_envs` (4096) phantom episodes to clip 0.
3. `assign_clips` passes `count_exposure=False`: evaluation pins clips
   deterministically and must not enter the training-exposure ledger.
4. **`tools/climb_train.py`** — `_install_exposure_ledger()` wraps
   `MotionTrackingOnPolicyRunner.save` so every checkpoint gets a sibling
   `model_<it>_exposure.json` containing `per_clip_stats()` plus `iteration`
   and `sampling_mode`. The wrapper is installed in the launcher, not in
   `mjlab/tasks/tracking/rl/runner.py`, so the vendored upstream tree stays
   untouched. Any failure is caught and printed — telemetry never kills a run.

### Behaviour change for the adaptive/grounded arms

None that is observable. The moved code computes the same two bincounts from
the same tensors at the same point in the resample; `_clip_failed_now` (which
feeds `clip_failed_ema`, and therefore the sampling distribution) is written
under identical conditions, because `terminated` is all-False on the startup
reset that the new `ran` gate excludes. `clip_episodes` / `clip_failures` never
influence sampling and have never been written to disk, so no published number
moves.

Cost: one extra boolean mask index per resample (`clips[ran]`) — the same class
of GPU/CPU sync the existing `if torch.any(terminated)` already performs.

## How to verify it worked

```bash
cd /data/robotixx/climb
# 1. static: the tally is now in _place and gone from _adaptive_sampling
sed -n '/def _count_exposure/,/def _place/p' climb/commands.py
grep -n "clip_episodes\|clip_failures" climb/commands.py     # expect only __init__, _count_exposure, per_clip_stats

# 2. compile
bridge/.venv/bin/python -m py_compile climb/commands.py tools/climb_train.py

# 3. live: a SHORT uniform smoke run must produce a NON-zero ledger.
#    GPU work — only after the CPU-only rule lifts (2026-09-15) or with an
#    explicit exception, and only when the card is free.
CLIMB_CLIPS=bank/tiers/tier_50.txt CLIMB_BANK=bank/amass MUJOCO_GL=egl WANDB_MODE=offline \
  mjlab-1.6.0/.venv/bin/python tools/climb_train.py Climb-Tracking-Flat-Unitree-G1 \
    --env.scene.num-envs 256 --agent.max-iterations 20 --agent.logger tensorboard \
    --agent.seed 1 --agent.run-name ledger-smoke-uniform

RUN=$(ls -d logs/rsl_rl/g1_tracking/*ledger-smoke-uniform | tail -1)
bridge/.venv/bin/python - "$RUN" <<'PY'
import json, sys, glob, os
p = sorted(glob.glob(os.path.join(sys.argv[1], "*_exposure.json")))[-1]
d = json.load(open(p))
ep = d["episodes"]
print(p, "mode=", d["sampling_mode"], "iter=", d["iteration"])
print("clips:", len(ep), "total episodes:", sum(ep), "clips with 0 exposure:", sum(e == 0 for e in ep))
assert sum(ep) > 0, "LEDGER STILL EMPTY — patch did not take effect"
print("PASS: uniform arm now records exposure")
PY
```

The pass condition is precisely the thing that is broken today: `sum(episodes)
> 0` on a **uniform** arm. Before the patch it is exactly `0.0`.

---

# Patch 2 — `eval_saturation.patch`

## What it fixes

Actuator saturation is measured nowhere in the training/eval path, so no arm
can report torque health — the third metric family the research plan wants,
alongside survival and tracking error.

## Evidence it is broken today

`effort_sat` exists only in the S1 intervention harness,
`tools/g1_clip44_gate.py:213,226,242`:

```python
    frange = (itv.forcerange if (itv is not None and phys is not None) else
              torch.tensor(m.actuator_forcerange, dtype=torch.float32, device=dev)[None].repeat(n, 1, 1))
...
                af = wp.to_torch(data.actuator_force)
...
            sat = (af.abs() >= 0.98 * frange[:, :, 1]).float().mean(dim=1)
```

The training-eval path records survival and tracking error only.
`tools/climb_eval.py:136-144` writes:

```python
        rows.append({
            "clip": os.path.splitext(os.path.basename(path))[0],
            "survival_rate": round(float(full[i].mean()), 4),
            "mean_survival_s": round(float(steps[i].mean()) * env.step_dt, 3),
            "mean_body_pos_err": round(float(mean_err[i].mean()), 5),
            "episodes": args.episodes_per_clip,
            "horizon_s": args.max_seconds,
            "start": args.start,
        })
```

and `tools/eval_stratified.py:122-124` writes only
`clip, offset_s, survival, mean_survival_s, n, window_s`. Neither file
references `actuator_force` or `actuator_forcerange`.

Consequence: a policy that tracks a clip with margin and one that only holds on
by pinning every motor at its limit produce the identical row. The second is
the one that fails on hardware, where the force limit is a real motor rather
than a clamp in the solver.

## What the patch does

Adds the same quantity, with the same 98 % threshold, to both eval tools:
`effort_sat` = fraction of **force-limited** actuators whose `|actuator_force|`
is at or above 98 % of the model's `actuator_forcerange` upper bound. It is
sampled every step under the same `alive` mask the survival and error
accumulators already use, and reduced three ways per clip (per `(clip, offset)`
in the stratified tool):

| column | meaning |
|---|---|
| `effort_sat_mean` | mean over live steps and episodes — steady-state effort load |
| `effort_sat_peak` | per-episode max, averaged over episodes — worst instant |
| `effort_sat_at_end` | value on the last live step — torque state at the fall / at the horizon |

Implementation notes:

* Reads `env.sim.data.actuator_force`, the `WarpBridge`/`TorchArray` view
  (`mjlab/sim/sim_data.py`), rather than importing `warp` into the eval tools.
  `env.sim.data.<field>` is the pattern `eval_stratified.py:92` and
  `g1_clip44_gate.py` already use inside their rollout loops.
* Only actuators with a positive `actuator_forcerange[:, 1]` are counted. If a
  model declares no force limits at all the columns are `nan`, never `0.0` —
  the whole point of this document is that a zero must not be readable as a
  measurement.
* O(N) accumulators, not a per-step history, so the 800-clip E-HYG evals do not
  grow memory with the horizon.

## The schema hazard, and why this is safe

`tools/eval_stratified.py`'s CSV is consumed by `tools/analyze_ehyg.py`, whose
sha256 (`5f8eb56e…`) is verified by the running chain — editing it **aborts**
the chain. `tools/analyze_n3.py` (`b118b2d3…`) is verified the same way.

**Therefore the schema change is strictly additive.** The three columns are
*appended* to the end of every row. No existing column is renamed, reordered,
retyped, or removed, and neither analyzer file is touched by the patch.

That is safe because every consumer reads by column *name*:

* `tools/analyze_ehyg.py:22-29` — `csv.DictReader`, touches only
  `r["offset_s"]`, `r["clip"]`, `r["survival"]`.
* `tools/analyze_n3.py:39-42` — `csv.DictReader`, same three fields.
* An audit of `tools/*.py` finds **no positional `csv.reader`** on any eval
  CSV; every hit is `csv.DictReader`.

Verified by replaying both readers' exact logic over an old-schema and a
new-schema CSV:

```
analyze_ehyg.read_strat  old==new : {'clipA': 0.625} == {'clipA': 0.625}
analyze_n3  strat reader old==new : {'clipA': {0.0: 0.75, 1.0: 0.5}} == {'clipA': {0.0: 0.75, 1.0: 0.5}}
```

One detail worth keeping: `eval_stratified.py` builds its header from
`rows[0].keys()`, so the new keys must appear in *both* the per-offset rows and
the trailing `offset_s == "mean"` row. The patch adds them to both (the mean
row leaves `effort_sat_peak` / `effort_sat_at_end` blank, since a max-of-maxes
across offsets is not a meaningful summary).

**Do not** insert a column, rename one, or change `mean_survival_s`'s empty
string in the mean row. Any of those breaks a sealed analysis.

## How to verify it worked

```bash
cd /data/robotixx/climb
bridge/.venv/bin/python -m py_compile tools/climb_eval.py tools/eval_stratified.py

# GPU work — only after the CPU-only rule lifts, and only on a free card.
MUJOCO_GL=egl bridge/.venv/bin/python tools/eval_stratified.py \
  --checkpoint "$(ls -d logs/rsl_rl/g1_tracking/*uniform-mixed100-s1)/model_3999.pt" \
  --clips plan/N3_probe_clips.txt --offsets 0,1,2 --window 3 --episodes 4 \
  --out /tmp/sat_check.csv

head -1 /tmp/sat_check.csv
# expect: clip,offset_s,survival,mean_survival_s,n,window_s,effort_sat_mean,effort_sat_peak,effort_sat_at_end
#         ^^^ the first six names, in this order, unchanged

# the sealed reader must produce identical survivals from the new file
bridge/.venv/bin/python -c "
import csv,io,numpy as np
rows=[r for r in csv.DictReader(open('/tmp/sat_check.csv')) if r['offset_s']!='mean']
print('clips read:', len({r[\"clip\"] for r in rows}))
print('sat range:', min(float(r['effort_sat_mean']) for r in rows), max(float(r['effort_sat_peak']) for r in rows))
assert all(0.0 <= float(r['effort_sat_mean']) <= 1.0 for r in rows)
print('PASS: additive columns present, survivals unchanged in name and position')
"
```

Sanity anchor for the magnitude: `reports/effort_sat_at_fall.json` measured
`0.0` before the fall and `~0.17` during it on clip 44, using the same 98 %
definition. A stratified run whose `effort_sat_peak` is orders away from that
band means the wiring is wrong, not that the policy changed.

---

# Runs whose exposure ledger is unusable

**Read this before quoting any per-clip exposure number for any completed run.**

Because `per_clip_stats()` has never had a caller, **no run in
`logs/rsl_rl/g1_tracking/` or `reports/campaign/` has an exposure ledger on
disk at all.** There is no file to misread — but there is also no measurement,
and the absence must not be filled in by assumption.

Separately, for the uniform arms the in-memory ledger was *also* identically
zero, so even a live debugger attached to those runs would have shown
`episodes = [0.0] * n`. That is the reading that must never be reported as
"these clips were never sampled".

Enumerated from `logs/rsl_rl/g1_tracking/` (sampling mode read from each run's
own frozen `params/env.yaml`):

| run directory | sampling_mode | ledger on disk | in-memory ledger during the run |
|---|---|---|---|
| `2026-08-15_12-27-56_climb-multiclip-smoke` | uniform | none | identically zero |
| `2026-08-15_12-28-18_climb-adaptive-smoke` | adaptive | none | counted, discarded at exit |
| `2026-08-15_12-29-08_climb-uniform-tier50-s1` | uniform | none | identically zero |
| `2026-08-15_20-29-21_uniform-mixed100-s1` | uniform | none | identically zero |
| `2026-08-15_23-42-12_adaptive-mixed100-s1` | adaptive | none | counted, discarded at exit |
| `2026-08-16_01-42-46_uniform-mixed100-s2` | uniform | none | identically zero |
| `2026-08-16_03-17-22_adaptive-mixed100-s2` | adaptive | none | counted, discarded at exit |
| `2026-08-16_04-30-57_uniform-mixed100-s3` | uniform | none | identically zero |
| `2026-08-16_05-06-29_adaptive-mixed100-s3` | adaptive | none | counted, discarded at exit |
| `2026-08-16_09-03-16_grounded-mixed100-s1` | grounded | none | counted, discarded at exit |
| `2026-08-16_15-44-17_grounded-mixed100-s2` | grounded | none | counted, discarded at exit |
| `2026-08-16_16-19-38_grounded-mixed100-s3` | grounded | none | counted, discarded at exit |
| `2026-08-19_15-37-38_uniform-mixed100g16-s1` | uniform | none | identically zero |

"grounded" counts because `_resample_command` temporarily rewrites
`cfg.sampling_mode` to `"adaptive"` to borrow the base dispatch
(`climb/commands.py:174-183`), so it reaches `_adaptive_sampling`.

Everything the running chain has yet to launch inherits the same hole: the N3
arms A1-s2, A2 (adaptive — counts in memory only), A3 random16, and both E-HYG
arms (uniform-800, uniform-800-pruned) are uniform except A2, so their ledgers
will be zero and unwritten too. **The patch cannot be applied to rescue them
without breaking the seal; they will have to be reported as "exposure not
instrumented".**

## `reports/campaign/` — what is and is not affected

Every CSV under `reports/campaign/` (`{uniform,adaptive,grounded}-mixed100-s{1,2,3}_it{0,500,…,3999}.csv`,
9 checkpoints × 9 cells = 81 files) is a **held-out evaluation** produced by
`tools/climb_eval.py`, with header

```
clip,survival_rate,mean_survival_s,mean_body_pos_err,episodes,horizon_s,start
```

Its `episodes` column is the eval's `--episodes-per-clip` constant (8), **not**
training exposure. None of these files is corrupted by the missing ledger — but
none of them can substitute for it either. The same holds for
`reports/A7_trainbank_uniform_s1.csv`, which despite the name is a
`climb_eval.py` output over the training bank, not an exposure record.

`reports/campaign/_frozen/20260819T193733Z/` contains the frozen driver plus
`train_clips.txt` / `eval_clips.txt`; it records which clips were *available*,
never which were *drawn*.

## The one report that reads like an exposure measurement and is not

`reports/wasted_exposure_accounting.json`:

```json
 "mixed100": {
  "flagged_clips": 25,
  "clip_draw_share_to_flagged": 0.25,
  ...
 },
 "adaptive": {
  "mean_top1_mass": 0.4884832416666667,
  "exposure_to_impossible_clip_mean": 0.4884832416666667,
```

`clip_draw_share_to_flagged = 0.25` is `25/100` — the *analytic* consequence of
assuming a uniform draw, not a count of draws. The adaptive figure comes from
the `sampling_top1_prob` scalar in tensorboard, not from the ledger. Both are
defensible as models; neither is a measurement of which clips the policy
actually trained on. Label them as derived quantities until patch 1 has run on
a real arm.

## What *is* trustworthy today

The aggregate sampler-shape metrics were logged to tensorboard by every one of
the 13 runs (`Metrics/motion/sampling_clip_entropy` confirmed present in each
`events.out.tfevents.*`), along with `sampling_clip_top1_prob` and
`bank_clip_count`. Those measure the *distribution's* concentration. What they
cannot give is the per-clip identity — which clip got the mass — and that is
exactly what patch 1 restores.
