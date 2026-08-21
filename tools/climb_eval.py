#!/usr/bin/env python3
"""Measure per-clip tracking difficulty for a trained policy.

This is the empirical half of the RQ1 difficulty atlas, and the instrument the
SIM-D1 headroom gate needs. Training-time telemetry is not a substitute: during
training the policy is changing under you and clip coverage is whatever the
sampler happened to favour, so per-clip statistics are confounded with the
sampler being evaluated.

Here every clip instead gets a fixed set of environments, all started at frame
0, and the policy is frozen. What comes out per clip is survival fraction
(episodes reaching the horizon without a termination) and mean tracking error
over the surviving prefix.

Usage:
    climb_eval.py --checkpoint model_4000.pt --clips tiers/tier_50.txt \
                  --bank bank/amass --episodes-per-clip 8 --out eval.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import asdict

import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--clips", required=True)
    ap.add_argument("--bank", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--episodes-per-clip", type=int, default=8)
    ap.add_argument("--max-seconds", type=float, default=10.0)
    ap.add_argument("--sampling-mode", default="uniform",
                    help="arm whose env cfg to instantiate; clips are pinned regardless")
    ap.add_argument("--start", choices=["frame0", "random"], default="random",
                    help="frame0: every episode from the clip start -- answers 'can the "
                         "policy track this clip end to end', but the episodes are near "
                         "identical so per-clip survival collapses to 0 or 1. random: "
                         "uniform start within the clip, matching how training samples "
                         "and how a curriculum would score a clip.")
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()

    import climb  # noqa: PLC0415,F401  (registers tasks / imports cfg helpers)
    from mjlab.envs import ManagerBasedRlEnv  # noqa: PLC0415
    from mjlab.rl import RslRlVecEnvWrapper  # noqa: PLC0415
    from mjlab.tasks.registry import load_rl_cfg, load_runner_cls  # noqa: PLC0415

    from climb import climb_g1_tracking_env_cfg, read_clip_list  # noqa: PLC0415

    files = read_clip_list(args.clips, args.bank)
    n_clips = len(files)
    num_envs = n_clips * args.episodes_per_clip
    print(f"[eval] {n_clips} clips x {args.episodes_per_clip} episodes = {num_envs} envs")

    task = "Climb-Tracking-Flat-Unitree-G1"
    env_cfg = climb_g1_tracking_env_cfg(
        motion_files=files, sampling_mode=args.sampling_mode
    )
    env_cfg.scene.num_envs = num_envs
    # Never resample mid-episode: a clip switch would silently splice two
    # motions into one measurement.
    env_cfg.commands["motion"].resampling_time_range = (1.0e9, 1.0e9)

    agent_cfg = load_rl_cfg(task)
    env = ManagerBasedRlEnv(cfg=env_cfg, device=args.device)
    wrapped = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)

    runner_cls = load_runner_cls(task)
    runner = runner_cls(wrapped, asdict(agent_cfg), device=args.device)
    runner.load(args.checkpoint, load_cfg={"actor": True}, strict=True,
                map_location=args.device)
    policy = runner.get_inference_policy(device=args.device)
    print(f"[eval] loaded {args.checkpoint}")

    cmd = env.command_manager.get_term("motion")
    # Block layout, not interleaved: envs [i*k, (i+1)*k) all run clip i, so the
    # later reshape(n_clips, k) groups episodes of the *same* clip. Interleaving
    # with `% n_clips` and reshaping the same way silently averages k different
    # clips into each row, which flattens the per-clip distribution toward the
    # bank mean and destroys any correlation with the atlas.
    clip_of_env = torch.arange(num_envs, device=args.device) // args.episodes_per_clip

    obs, _ = wrapped.reset()
    cmd.assign_clips(clip_of_env, at_start=(args.start == "frame0"))

    horizon = int(args.max_seconds / env.step_dt)
    alive = torch.ones(num_envs, dtype=torch.bool, device=args.device)
    completed = torch.zeros(num_envs, dtype=torch.bool, device=args.device)
    survived = torch.zeros(num_envs, device=args.device)
    err_sum = torch.zeros(num_envs, device=args.device)
    err_n = torch.zeros(num_envs, device=args.device)

    # Actuator-effort headroom -- the third metric family. Survival cannot
    # separate a policy that tracks a clip with margin from one that only holds
    # on by pinning every motor at its limit, and it is the second that falls
    # over on hardware, where the limit is real rather than a clamp in the
    # solver. `effort_sat` is the fraction of force-limited actuators at >= 98%
    # of their force range; the definition and the threshold are lifted from
    # the S1 intervention harness (tools/g1_clip44_gate.py) so the training-eval
    # path and the fragility gate report the same quantity.
    frange_hi = torch.tensor(
        env.sim.mj_model.actuator_forcerange[:, 1].copy(),
        dtype=torch.float32,
        device=args.device,
    )
    limited = frange_hi > 0
    n_limited = int(limited.sum())
    sat_thresh = 0.98 * frange_hi
    if n_limited == 0:
        print("[eval] WARNING: no actuator declares a force range; effort_sat -> nan")
    sat_sum = torch.zeros(num_envs, device=args.device)
    sat_peak = torch.zeros(num_envs, device=args.device)
    sat_end = torch.zeros(num_envs, device=args.device)

    with torch.inference_mode():
        for _ in range(horizon):
            obs, _, _, _ = wrapped.step(policy(obs))
            # The wrapper folds truncation into `dones`, but running out of
            # episode clock is success here, not failure. Read the termination
            # manager so only genuine falls / tracking blowups count.
            failed = env.termination_manager.terminated.bool()
            # Reaching the end of a clip wraps the command onto a *new* clip.
            # The bank's median clip is 7.3 s against a 10 s episode, so most
            # envs hit this before the horizon; counting past it would splice a
            # second, randomly chosen motion into the measurement. Treat the
            # wrap as "tracked this clip to its end" and freeze the env.
            wrapped_off = cmd.clip_ids != clip_of_env

            e = cmd.metrics["error_body_pos"]
            err_sum += torch.where(alive, e, torch.zeros_like(e))
            err_n += alive.float()
            survived += alive.float()

            # Read effort under the same `alive` mask as the tracking error and
            # before this step retires anyone, so a dead env contributes 0 and
            # `sat_end` keeps the value from its last live step (the torque
            # state at the fall).
            sat = (
                (env.sim.data.actuator_force.abs() >= sat_thresh) & limited
            ).float().sum(dim=1) / max(n_limited, 1)
            sat = torch.where(alive, sat, torch.zeros_like(sat))
            sat_sum += sat
            sat_peak = torch.maximum(sat_peak, sat)
            sat_end = torch.where(alive, sat, sat_end)

            # A step that both fails and wraps counts as a failure.
            completed |= alive & wrapped_off & ~failed
            alive &= ~(failed | wrapped_off)
            if not alive.any():
                break

    steps = survived.reshape(n_clips, args.episodes_per_clip)
    mean_err = (err_sum / err_n.clamp(min=1)).reshape(n_clips, args.episodes_per_clip)
    # Success = tracked the clip to its end, or still upright at the horizon
    # for clips longer than max_seconds.
    full = (completed | alive).float().reshape(n_clips, args.episodes_per_clip)
    sat_mean = (sat_sum / err_n.clamp(min=1)).reshape(n_clips, args.episodes_per_clip)
    sat_pk = sat_peak.reshape(n_clips, args.episodes_per_clip)
    sat_fin = sat_end.reshape(n_clips, args.episodes_per_clip)

    def _sat(x: torch.Tensor) -> float:
        """nan, not 0.0, when the model declares no force limit to saturate."""
        return float("nan") if n_limited == 0 else round(float(x), 5)

    rows = []
    for i, path in enumerate(files):
        rows.append({
            "clip": os.path.splitext(os.path.basename(path))[0],
            "survival_rate": round(float(full[i].mean()), 4),
            "mean_survival_s": round(float(steps[i].mean()) * env.step_dt, 3),
            "mean_body_pos_err": round(float(mean_err[i].mean()), 5),
            "episodes": args.episodes_per_clip,
            "horizon_s": args.max_seconds,
            "start": args.start,
            # Appended, never inserted or renamed: every consumer of these CSVs
            # reads them with csv.DictReader keyed by name, so extra trailing
            # columns are invisible to existing analyses.
            "effort_sat_mean": _sat(sat_mean[i].mean()),
            "effort_sat_peak": _sat(sat_pk[i].mean()),
            "effort_sat_at_end": _sat(sat_fin[i].mean()),
        })

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    sr = torch.tensor([r["survival_rate"] for r in rows])
    print(f"\n[eval] survival rate: mean={sr.mean():.3f} "
          f"min={sr.min():.3f} max={sr.max():.3f}")
    # The SIM-D1 gate: a bank with no clips in the 0.2-0.8 band gives an
    # adaptive sampler nothing to prioritise between.
    frontier = ((sr > 0.2) & (sr < 0.8)).float().mean()
    mastered = (sr >= 0.8).float().mean()
    print(f"[eval] frontier fraction = {frontier:.3f} (gate >= 0.20)")
    print(f"[eval] mastered fraction = {mastered:.3f} (gate >= 0.30)")
    if n_limited > 0:
        sm = torch.tensor([r["effort_sat_mean"] for r in rows])
        print(f"[eval] effort_sat over {n_limited} limited actuators: "
              f"mean={sm.mean():.3f} max={sm.max():.3f}")
    print(f"[eval] wrote {args.out}")
    env.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
