#!/usr/bin/env python3
"""Build the N-preserving *repaired* view of a sealed tier as a symlink overlay.

Why an overlay and not an absolute-path clip list
-------------------------------------------------
tools/eval_stratified.py (and climb/motion_bank.py) join clip names with
``os.path.join(args.bank, name + ".npz")``.  An absolute path in the list would be
swallowed by os.path.join and silently resolve to the wrong (or a nonexistent)
file.  A directory of symlinks keeps every consumer's "bank dir + plain name"
contract intact while letting individual clips come from a different source.

What it builds
--------------
Given a sealed tier list (default ``bank/tiers/tier_800.txt``) and the flagged
subset (clips whose feasibility screen reports ``infeasible_frac`` above a
threshold), it writes

  <out-dir>/<name>.npz   -> relative symlink into bank/amass or bank/repaired_census
  <tier-out>             -> the same N plain names, in the sealed tier's order
  <manifest>             -> per-clip provenance {source, target, sha256, fps, n_frames,
                            stratum, census metrics} + counts + invariants
  <manifest>.sha256      -> sha256 of the manifest bytes

Composition of the 21 clips whose repair failed the census success budget
(offset_max_m <= 0.15 and infeasible_frac_after <= 0.05) is a *declared policy*,
never a default silently applied:

  --fail-policy repair-all      substitute the repaired file anyway (N preserved).
                                Justification and the alternative's evidence are in
                                plan/REPAIRED800_COMPOSITION.md.
  --fail-policy keep-original   leave those clips at their raw original (N preserved,
                                but the arm still carries their contamination).
  --fail-policy drop            omit them entirely (N shrinks; reintroduces the
                                clip-count confound this bank exists to remove).

Nothing here writes into an existing bank or tier file; every output path is new.

Examples
--------
  build_repaired_bank.py --check-only
  build_repaired_bank.py --fail-policy repair-all
  build_repaired_bank.py --fail-policy keep-original \
      --out-dir bank/amass_repaired800_certified \
      --tier-out bank/tiers/tier_800_repaired_certified.txt \
      --manifest reports/repaired800/manifest_certified.json
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import os
import sys

import numpy as np

ROOT = "/data/robotixx/climb"

# Census success budget, quoted from tools/repair_contact_projection.py.
OFFSET_BUDGET_M = 0.15
RESIDUAL_BUDGET = 0.05


def rel(path: str) -> str:
    return os.path.relpath(path, ROOT)


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def read_list(path: str) -> list[str]:
    with open(path) as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def flagged_from_screen(csv_path: str, tier: list[str], threshold: float) -> tuple[list[str], list[str]]:
    """Clips in `tier` whose screen infeasible_frac exceeds `threshold` (strict >)."""
    rows = {}
    with open(csv_path) as fh:
        for r in csv.DictReader(fh):
            rows[r["clip"]] = r
    missing = [c for c in tier if c not in rows]
    if missing:
        raise SystemExit(f"{len(missing)} tier clips absent from {csv_path}, e.g. {missing[:3]}")
    flagged = [c for c in tier if float(rows[c]["infeasible_frac"]) > threshold]
    return flagged, missing


def stratum_of(rec: dict) -> str:
    """Label a repaired clip from its census record alone (no extra measurement)."""
    if rec["success"]:
        return "repaired_certified"
    if rec["infeasible_frac_after"] > RESIDUAL_BUDGET:
        # Residual infeasibility is the binding physical objection; it takes
        # precedence over an offset-budget miss when a clip fails both.
        return "repaired_residual"
    return "repaired_over_budget"


def npz_facts(path: str) -> tuple[float, int]:
    with np.load(path) as z:
        if "fps" not in z:
            raise KeyError("no 'fps' key")
        fps = float(np.asarray(z["fps"]).reshape(-1)[0])
        n = int(z["joint_pos"].shape[0])
    return fps, n


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--tier", default=f"{ROOT}/bank/tiers/tier_800.txt")
    ap.add_argument("--pruned", default=f"{ROOT}/bank/tiers/tier_800_pruned.txt",
                    help="sealed pruned list; used only to cross-check the flagged set")
    ap.add_argument("--screen-csv", default=f"{ROOT}/reports/feasibility_all/feasibility.csv")
    ap.add_argument("--threshold", type=float, default=0.10,
                    help="flag clips with screen infeasible_frac > THRESHOLD (strict)")
    ap.add_argument("--orig-bank", default=f"{ROOT}/bank/amass")
    ap.add_argument("--repaired-bank", default=f"{ROOT}/bank/repaired_census")
    ap.add_argument("--census-dir", default=f"{ROOT}/reports/repair_census/json")
    ap.add_argument("--annotations", default=f"{ROOT}/reports/repaired800/fail21_contact_diagnosis.json",
                    help="optional per-frame contact diagnosis; refines labels only, never composition")
    ap.add_argument("--out-dir", default=f"{ROOT}/bank/amass_repaired800")
    ap.add_argument("--tier-out", default=f"{ROOT}/bank/tiers/tier_800_repaired.txt")
    ap.add_argument("--manifest", default=f"{ROOT}/reports/repaired800/manifest.json")
    ap.add_argument("--fail-policy", choices=("repair-all", "keep-original", "drop"),
                    default="repair-all")
    ap.add_argument("--check-only", action="store_true",
                    help="verify the composition invariant and exit without writing")
    ap.add_argument("--force", action="store_true",
                    help="rebuild <out-dir> even if it already exists (symlinks only)")
    a = ap.parse_args()

    tier = read_list(a.tier)
    if len(set(tier)) != len(tier):
        raise SystemExit("tier list has duplicates")
    flagged, _ = flagged_from_screen(a.screen_csv, tier, a.threshold)
    flagged_set = set(flagged)

    # ---- invariant: tier_800_pruned == tier_800 minus exactly the flagged clips ----
    invariants: dict = {"tier_n": len(tier), "flagged_n": len(flagged),
                        "threshold_infeasible_frac": a.threshold}
    if a.pruned and os.path.exists(a.pruned):
        pruned = read_list(a.pruned)
        expect = [c for c in tier if c not in flagged_set]
        invariants["pruned_matches_tier_minus_flagged"] = bool(pruned == expect)
        invariants["pruned_n"] = len(pruned)
        if pruned != expect:
            extra = sorted(set(pruned) - set(expect))
            gone = sorted(set(expect) - set(pruned))
            print(f"[FAIL] {rel(a.pruned)} is not {rel(a.tier)} minus the {len(flagged)} flagged clips",
                  file=sys.stderr)
            print(f"       in pruned but should be flagged out: {extra[:5]}", file=sys.stderr)
            print(f"       flagged out but should be kept:      {gone[:5]}", file=sys.stderr)
            return 2
        print(f"[ok] {rel(a.pruned)} == {rel(a.tier)} minus exactly "
              f"{len(flagged)} clips with infeasible_frac > {a.threshold} (order preserved)")

    # ---- census records for the flagged clips ----
    census: dict[str, dict] = {}
    for c in flagged:
        p = os.path.join(a.census_dir, c + ".json")
        if not os.path.exists(p):
            raise SystemExit(f"no census record for flagged clip {c}: {p}")
        census[c] = json.load(open(p))
    failed = [c for c in flagged if not census[c]["success"]]
    print(f"[ok] census: {len(flagged) - len(failed)} certified repairs, "
          f"{len(failed)} outside the success budget")

    annotations = {}
    if a.annotations and os.path.exists(a.annotations):
        annotations = json.load(open(a.annotations)).get("clips", {})

    if a.check_only:
        print(json.dumps(invariants, indent=1))
        return 0

    # ---- resolve every clip to a concrete source file ----
    plan: list[tuple[str, str, str]] = []          # (name, source-label, absolute target)
    for name in tier:
        if name not in flagged_set:
            plan.append((name, "original", os.path.join(a.orig_bank, name + ".npz")))
            continue
        ok = census[name]["success"]
        if ok or a.fail_policy == "repair-all":
            plan.append((name, "repaired", os.path.join(a.repaired_bank, name + ".npz")))
        elif a.fail_policy == "keep-original":
            plan.append((name, "original", os.path.join(a.orig_bank, name + ".npz")))
        # "drop" -> omit

    missing = [t for _, _, t in plan if not os.path.exists(t)]
    if missing:
        raise SystemExit(f"{len(missing)} source files do not exist, e.g. {missing[:3]}")

    # ---- build the symlink overlay (relative links keep the repo relocatable) ----
    os.makedirs(os.path.dirname(a.manifest), exist_ok=True)
    if os.path.isdir(a.out_dir):
        stale = [f for f in os.listdir(a.out_dir)]
        if stale and not a.force:
            raise SystemExit(f"{rel(a.out_dir)} already exists and is not empty; pass --force to rebuild")
        for f in stale:
            p = os.path.join(a.out_dir, f)
            if not os.path.islink(p):
                raise SystemExit(f"refusing to remove non-symlink {p}")
            os.unlink(p)
    os.makedirs(a.out_dir, exist_ok=True)
    for name, _, target in plan:
        link = os.path.join(a.out_dir, name + ".npz")
        os.symlink(os.path.relpath(target, a.out_dir), link)

    # ---- manifest: hash and read every file THROUGH the overlay ----
    clips = []
    fps_seen: set[float] = set()
    for name, source, target in plan:
        link = os.path.join(a.out_dir, name + ".npz")
        fps, n_frames = npz_facts(link)
        fps_seen.add(fps)
        rec = census.get(name)
        entry = {
            "name": name,
            "source": source,
            "target": rel(os.path.realpath(link)),
            "sha256": sha256_file(link),
            "fps": fps,
            "n_frames": n_frames,
            "stratum": "original" if name not in flagged_set
                       else (stratum_of(rec) if source == "repaired" else "flagged_kept_original"),
        }
        if rec is not None:
            entry["census"] = {
                "infeasible_frac_before": rec["infeasible_frac_before"],
                "infeasible_frac_after": rec["infeasible_frac_after"],
                "airborne_frac_before": rec["airborne_frac_before"],
                "airborne_frac_after": rec["airborne_frac_after"],
                "offset_max_m": rec["offset_max_m"],
                "peak_added_downward_vel_mps": rec["peak_added_downward_vel_mps"],
                "success": rec["success"],
            }
        ann = annotations.get(name)
        if ann is not None:
            entry["residual_is_in_contact"] = ann["residual_is_in_contact"]
            entry["infeasible_in_contact_frac_after"] = ann["after"]["infeasible_in_contact_frac"]
        clips.append(entry)

    if len(fps_seen) != 1:
        raise SystemExit(f"clips disagree on fps: {sorted(fps_seen)} -- "
                         "climb/motion_bank.py would raise at bank construction")

    counts: dict[str, int] = {}
    for e in clips:
        counts[e["stratum"]] = counts.get(e["stratum"], 0) + 1

    with open(a.tier_out, "w") as fh:
        fh.write("\n".join(e["name"] for e in clips) + "\n")

    manifest = {
        "generator": "tools/build_repaired_bank.py",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "tier": rel(a.tier), "tier_sha256": sha256_file(a.tier),
            "pruned": rel(a.pruned) if os.path.exists(a.pruned) else None,
            "pruned_sha256": sha256_file(a.pruned) if os.path.exists(a.pruned) else None,
            "screen_csv": rel(a.screen_csv), "threshold_infeasible_frac": a.threshold,
            "orig_bank": rel(a.orig_bank), "repaired_bank": rel(a.repaired_bank),
            "census_dir": rel(a.census_dir),
            "success_budget": {"offset_max_m": OFFSET_BUDGET_M,
                               "infeasible_frac_after": RESIDUAL_BUDGET},
        },
        "policy": {"fail_policy": a.fail_policy},
        "outputs": {"bank_dir": rel(a.out_dir), "tier_list": rel(a.tier_out),
                    "tier_list_sha256": sha256_file(a.tier_out)},
        "invariants": invariants,
        "counts": {"n_clips": len(clips), "fps": sorted(fps_seen)[0],
                   "total_frames": sum(e["n_frames"] for e in clips), "by_stratum": counts},
        "clips": clips,
    }
    blob = json.dumps(manifest, indent=1, sort_keys=False).encode()
    with open(a.manifest, "wb") as fh:
        fh.write(blob)
    digest = hashlib.sha256(blob).hexdigest()
    # The wall-clock stamp makes the whole-file hash change on every rebuild, which
    # would make "the manifest hash" useless as an identity for the bank. The payload
    # hash covers everything *except* that stamp, so two builds from the same inputs
    # and policy agree on it -- that is the number to quote and to pin.
    payload = {k: v for k, v in manifest.items() if k != "generated_utc"}
    payload_digest = hashlib.sha256(
        json.dumps(payload, indent=1, sort_keys=False).encode()
    ).hexdigest()
    base = os.path.basename(a.manifest)
    with open(a.manifest + ".sha256", "w") as fh:
        fh.write(f"{digest}  {base}\n{payload_digest}  {base}:payload\n")

    print(f"[ok] {len(clips)} clips @ {sorted(fps_seen)[0]:g} fps -> {rel(a.out_dir)}")
    for k in sorted(counts):
        print(f"       {k:26s} {counts[k]:4d}")
    print(f"[ok] tier list  {rel(a.tier_out)}")
    print(f"[ok] manifest   {rel(a.manifest)}")
    print(f"       file sha256    {digest}")
    print(f"       payload sha256 {payload_digest}   (reproducible; excludes generated_utc)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
