#!/usr/bin/env python3
"""Frozen Phase-G analysis: manipulation gate, then G2 - G1 and G1 - G0.

Inputs are a run manifest (per arm, per seed: evaluator per-condition CSVs per
checkpoint and sampler ledgers), the sealed evaluation-condition manifest, and
nothing else. The gate is evaluated before any endpoint is read. The tool
fails closed when a ledger or checkpoint is missing. ``--synthetic`` exercises
the positive / null / inconclusive / gate-fail branches on generated data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

SESOI = 0.05
TV_BAND = (0.05, 0.15)
MIN_ENTROPY_EFFECTIVE_UNITS = 12.0
MAX_SATURATION_FRACTION = 0.90
G1_MAX_TV = 0.01
WARMUP_ITERATION = 400
FINAL_ITERATION = 3999
AULC_ITERATIONS = (1000, 2000, 3000, 3999)
NONINFERIORITY_MARGIN = 0.10
QUALITY_METRICS = (
    "common_root_relative_mpkpe_m_mean",
    "error_anchor_rot_mean",
    "absolute_mechanical_work_per_actuator_j",
)
BOOTSTRAP_SEED = 20260910
BOOTSTRAP_DRAWS = 10_000
ARMS = ("G0", "G1", "G2")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open() as handle:
        rows = {row["condition_id"]: row for row in csv.DictReader(handle)}
    if not rows:
        raise ValueError(f"{path}: empty evaluator output")
    return rows


def validate_rows(rows: dict[str, dict[str, str]], conditions: dict[str, Any], label: str) -> None:
    expected = {row["condition_id"] for row in conditions["conditions"]}
    if set(rows) != expected:
        raise ValueError(f"{label}: condition set differs from the sealed manifest")
    if any(row["full_window"] not in ("True", "1", "true") for row in rows.values()):
        raise ValueError(f"{label}: a condition is not full-window")


def per_clip(rows: dict[str, dict[str, str]], clips: list[str], column: str) -> np.ndarray:
    sums = {clip: [] for clip in clips}
    for row in rows.values():
        sums[row["clip"]].append(float(row[column]))
    return np.array([np.mean(sums[clip]) for clip in clips])


def hierarchical_bootstrap(matrix: np.ndarray, rng: np.random.Generator, draws: int) -> dict[str, float]:
    """Seed-then-clip resampling of a seeds x clips effect matrix."""
    seeds, clips = matrix.shape
    stats = np.empty(draws)
    for index in range(draws):
        seed_index = rng.integers(0, seeds, size=seeds)
        clip_index = rng.integers(0, clips, size=clips)
        stats[index] = matrix[np.ix_(seed_index, clip_index)].mean()
    return {
        "point": float(matrix.mean()),
        "ci_low": float(np.percentile(stats, 2.5)),
        "ci_high": float(np.percentile(stats, 97.5)),
        "seeds": int(seeds),
        "clips": int(clips),
        "draws": int(draws),
    }


def manipulation_gate(manifest: dict[str, Any]) -> dict[str, Any]:
    """Read every post-warm-up ledger before any endpoint is opened."""
    report: dict[str, Any] = {"G2": {}, "G1": {}, "G0": {}}
    for arm in ("G2", "G1"):
        for seed, run in manifest["arms"][arm]["seeds"].items():
            ledgers = [json.loads(Path(p).read_text()) for p in run.get("ledgers", [])]
            post = [l for l in ledgers if int(l["iteration"]) >= WARMUP_ITERATION]
            if not post:
                raise ValueError(f"{arm} seed {seed}: no sampler ledger after warm-up (fail closed)")
            seg = [l["segment"] for l in post]
            tv = [float(s["adaptation_total_variation"]) for s in seg]
            entropy = [float(s["entropy_effective_units"]) for s in seg]
            invalid = sum(int(s["invalid_start_count"]) + int(s["invalid_reference_frame_count"]) for s in seg)
            censored = sum(int(s.get("censored_resets", 0)) for s in seg)
            final = max(post, key=lambda l: int(l["iteration"]))["segment"]
            saturation = float(final.get("rank_saturation_fraction", float("nan")))
            entry = {
                "ledgers_after_warmup": len(post),
                "mean_tv": float(np.mean(tv)),
                "min_entropy_effective_units": float(min(entropy)),
                "invalid_frames": invalid,
                "censored_resets": censored,
                "final_saturation_fraction": saturation,
            }
            if arm == "G2":
                entry["pass"] = bool(
                    TV_BAND[0] <= entry["mean_tv"] <= TV_BAND[1]
                    and entry["min_entropy_effective_units"] >= MIN_ENTROPY_EFFECTIVE_UNITS
                    and invalid == 0
                    and censored == 0
                    and np.isfinite(saturation)
                    and saturation < MAX_SATURATION_FRACTION
                )
            else:
                entry["pass"] = bool(entry["mean_tv"] < G1_MAX_TV and invalid == 0 and censored == 0)
            report[arm][seed] = entry
    report["G0"] = {"checked": False, "note": "G0 uses the clip-level command; exposure check reported separately"}
    report["pass"] = all(e["pass"] for arm in ("G2", "G1") for e in report[arm].values())
    return report


def analyze(manifest: dict[str, Any], conditions: dict[str, Any], *, seed: int, draws: int) -> dict[str, Any]:
    if manifest.get("conditions_sha256") != conditions.get("_sha256"):
        raise ValueError("run manifest does not bind the sealed condition manifest")
    clips = sorted({row["clip"] for row in conditions["conditions"]})
    seeds = sorted(manifest["arms"]["G2"]["seeds"])
    if sorted(manifest["arms"]["G1"]["seeds"]) != seeds:
        raise ValueError("G1 and G2 must share the same seeds")
    gate = manipulation_gate(manifest)
    rng = np.random.default_rng(seed)

    def table(arm: str, iteration: int, column: str = "success") -> np.ndarray:
        matrix = []
        for s in seeds:
            path = Path(manifest["arms"][arm]["seeds"][s]["checkpoints"][str(iteration)])
            rows = read_rows(path)
            validate_rows(rows, conditions, f"{arm} seed {s} it {iteration}")
            matrix.append(per_clip(rows, clips, column))
        return np.array(matrix)

    result: dict[str, Any] = {"gate": gate, "seeds": seeds, "clips": len(clips)}
    if not gate["pass"]:
        result["verdict"] = "not_tested"
        result["reason"] = "manipulation gate failed; endpoints not opened"
        return result

    g2 = table("G2", FINAL_ITERATION)
    g1 = table("G1", FINAL_ITERATION)
    primary = hierarchical_bootstrap(g2 - g1, rng, draws)
    result["primary_G2_minus_G1_survival"] = primary
    aulc = {arm: np.mean([table(arm, it) for it in AULC_ITERATIONS], axis=0) for arm in ("G1", "G2")}
    result["secondary_G2_minus_G1_aulc"] = hierarchical_bootstrap(aulc["G2"] - aulc["G1"], rng, draws)
    if "G0" in manifest["arms"] and manifest["arms"]["G0"]["seeds"]:
        g0_seeds = sorted(manifest["arms"]["G0"]["seeds"])
        if g0_seeds == seeds:
            g0 = table("G0", FINAL_ITERATION)
            result["secondary_G1_minus_G0_survival"] = hierarchical_bootstrap(g1 - g0, rng, draws)
        else:
            result["secondary_G1_minus_G0_survival"] = {"skipped": "G0 seeds differ (drop order)"}
    else:
        result["secondary_G1_minus_G0_survival"] = {"skipped": "G0 dropped"}

    # Common-survivor quality noninferiority, relative to G1, lower is better.
    quality = {}
    noninferior = True
    for metric in QUALITY_METRICS:
        matrix = []
        for s in seeds:
            r2 = read_rows(Path(manifest["arms"]["G2"]["seeds"][s]["checkpoints"][str(FINAL_ITERATION)]))
            r1 = read_rows(Path(manifest["arms"]["G1"]["seeds"][s]["checkpoints"][str(FINAL_ITERATION)]))
            per = []
            for clip in clips:
                pairs = [
                    (float(r2[c][metric]), float(r1[c][metric]))
                    for c in r2
                    if r2[c]["clip"] == clip and r2[c]["success"] == "1" and r1[c]["success"] == "1"
                ]
                if pairs:
                    a, b = np.mean([p[0] for p in pairs]), np.mean([p[1] for p in pairs])
                    per.append((a - b) / max(abs(b), 1e-9))
                else:
                    per.append(np.nan)
            matrix.append(per)
        matrix = np.array(matrix)
        keep = ~np.isnan(matrix).any(axis=0)
        boot = hierarchical_bootstrap(matrix[:, keep], rng, draws)
        boot["pass"] = bool(boot["ci_high"] < NONINFERIORITY_MARGIN)
        noninferior &= boot["pass"]
        quality[metric] = boot
    result["noninferiority_relative"] = quality

    if primary["point"] >= SESOI and primary["ci_low"] > 0.0 and noninferior:
        verdict = "positive"
    elif primary["ci_high"] < SESOI:
        verdict = "null"
    else:
        verdict = "inconclusive"
    result["verdict"] = verdict
    return result


def _synthetic_case(root: Path, conditions: dict[str, Any], *, delta: float, noise: float, tv: float, rng: np.random.Generator) -> dict[str, Any]:
    clips = sorted({row["clip"] for row in conditions["conditions"]})
    base = {clip: rng.uniform(0.3, 0.9) for clip in clips}
    manifest: dict[str, Any] = {"conditions_sha256": conditions["_sha256"], "arms": {}}
    for arm, shift in (("G0", -0.02), ("G1", 0.0), ("G2", delta)):
        manifest["arms"][arm] = {"seeds": {}}
        for s in ("1", "2", "3"):
            entry: dict[str, Any] = {"checkpoints": {}, "ledgers": []}
            for it in AULC_ITERATIONS:
                path = root / f"{arm}_s{s}_{it}.csv"
                with path.open("w", newline="") as handle:
                    fields = ["condition_id", "clip", "full_window", "success", *QUALITY_METRICS]
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    for row in conditions["conditions"]:
                        p = np.clip(base[row["clip"]] + shift * it / FINAL_ITERATION + rng.normal(0, noise), 0, 1)
                        success = int(rng.random() < p)
                        writer.writerow({
                            "condition_id": row["condition_id"], "clip": row["clip"], "full_window": "True",
                            "success": success,
                            **{m: 0.1 * (1 + rng.normal(0, 0.05)) for m in QUALITY_METRICS},
                        })
                entry["checkpoints"][str(it)] = str(path)
            if arm != "G0":
                for it in (0, WARMUP_ITERATION, 2000, FINAL_ITERATION):
                    ledger = root / f"{arm}_s{s}_{it}_segment.json"
                    ledger.write_text(json.dumps({
                        "iteration": it,
                        "segment": {
                            "adaptation_total_variation": tv if arm == "G2" else 0.0,
                            "entropy_effective_units": 40.0,
                            "invalid_start_count": 0, "invalid_reference_frame_count": 0,
                            "censored_resets": 0, "rank_saturation_fraction": 0.3,
                        },
                    }))
                    entry["ledgers"].append(str(ledger))
            manifest["arms"][arm]["seeds"][s] = entry
    return manifest


def synthetic(conditions: dict[str, Any], out: Path) -> int:
    rng = np.random.default_rng(1)
    cases = {
        "positive": {"delta": 0.12, "noise": 0.02, "tv": 0.08},
        "null": {"delta": 0.0, "noise": 0.02, "tv": 0.08},
        "inconclusive": {"delta": 0.04, "noise": 0.25, "tv": 0.08},
        "gate_fail": {"delta": 0.12, "noise": 0.02, "tv": 0.01},
    }
    verdicts = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, kw in cases.items():
            case_dir = Path(tmp) / name
            case_dir.mkdir()
            manifest = _synthetic_case(case_dir, conditions, rng=rng, **kw)
            result = analyze(manifest, conditions, seed=BOOTSTRAP_SEED, draws=500)
            verdicts[name] = result["verdict"]
    expected = {"positive": "positive", "null": "null", "inconclusive": "inconclusive", "gate_fail": "not_tested"}
    passed = verdicts == expected
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"synthetic": True, "pass": passed, "verdicts": verdicts, "expected": expected,
                               "analyzer_sha256": sha256_file(Path(__file__).resolve())}, indent=1) + "\n")
    print(f"Phase-G analyzer synthetic: {'PASS' if passed else 'FAIL'} {verdicts}")
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conditions", type=Path, default=Path("reports/g_segment/eval_conditions.json"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=BOOTSTRAP_SEED)
    parser.add_argument("--draws", type=int, default=BOOTSTRAP_DRAWS)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    conditions = json.loads(args.conditions.read_text())
    conditions["_sha256"] = sha256_file(args.conditions)
    if args.synthetic:
        return synthetic(conditions, args.out)
    if args.manifest is None:
        parser.error("--manifest is required without --synthetic")
    manifest = json.loads(args.manifest.read_text())
    result = analyze(manifest, conditions, seed=args.seed, draws=args.draws)
    result["inputs"] = {
        "conditions_sha256": conditions["_sha256"],
        "manifest_sha256": sha256_file(args.manifest),
        "analyzer_sha256": sha256_file(Path(__file__).resolve()),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in ("verdict",) if k in result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
