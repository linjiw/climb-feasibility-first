#!/usr/bin/env python3
"""Plot measured CPU intervention checks, without policy-performance claims."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-dir", type=Path, required=True)
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--out-prefix", type=Path, required=True)
    args = parser.parse_args()
    verification = json.loads(args.verification.read_text())
    path = args.smoke_dir / "traces.pt"
    if hashlib.sha256(path.read_bytes()).hexdigest() != verification["traces_sha256"]:
        raise ValueError("trace hash differs from independent verification")
    data = torch.load(path, map_location="cpu", weights_only=True)
    result = json.loads((args.smoke_dir / "result.json").read_text())
    order = result["conditions"][0]["compiled"]["actuator_order"]
    knee = order.index("left_knee_joint")
    hip = order.index("left_hip_roll_joint")
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.6), constrained_layout=True)
    for name, label in (("unchanged", "0 ms"), ("delay_5ms", "5 ms"),
                        ("delay_10ms", "10 ms"), ("delay_20ms", "20 ms")):
        axes[0].plot(np.arange(12) * 5, data[name]["controls"][:, 0, knee], marker=".", label=label)
    axes[0].set(xlabel="Physics time (ms)", ylabel="Applied position target (rad)", title="Measured command delay")
    axes[0].legend(fontsize=8)
    names = ("unchanged", "knee_120nm", "knee_90nm")
    x = np.arange(3)
    for offset, index, label in ((-0.18, knee, "Knee"), (0.18, hip, "Hip roll")):
        axes[1].bar(x + offset, [float(data[n]["saturation_forces"][0, 0, index]) for n in names],
                    width=0.36, label=label)
    axes[1].set(xticks=x, xticklabels=["Unchanged", "120 N m", "90 N m"],
                ylabel="Saturated actuator force (N m)", title="Knee-only torque intervention")
    axes[1].legend(fontsize=8)
    rows = {r["condition"]: r for r in verification["conditions"]}
    names = ("unchanged", "friction_0p3", "friction_1p2")
    for world in range(2):
        axes[2].plot(x, [rows[n]["sliding_friction_per_world"][world] for n in names],
                     "o--", label=f"Fixture world {world + 1}")
    axes[2].set(xticks=x, xticklabels=["Startup draw", "0.3", "1.2"],
                ylabel="Foot sliding-friction coefficient", title="Realized model coefficients")
    axes[2].legend(fontsize=8)
    fig.suptitle("CPU actuator fixture: instrumentation evidence, no policy evaluation", fontsize=12)
    args.out_prefix.parent.mkdir(parents=True, exist_ok=True)
    for suffix in (".png", ".pdf"):
        destination = args.out_prefix.with_suffix(suffix)
        if destination.exists():
            raise FileExistsError(destination)
        fig.savefig(destination, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
