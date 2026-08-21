#!/usr/bin/env python3
"""Build the per-clip, per-bin eligibility sidecar m_b that FGAS consumes.

FGAS restricts failure prioritisation to *feasible* bins:

    p_b = (1-rho) * m_b*psi(f_b)/sum_j m_j*psi(f_j)  +  rho * m_b/sum_j m_j

Both terms are masked, so `m_b` is the only new input the sampler needs. This tool produces it,
one JSON per clip, from the dynamic-feasibility screen (`tools/n1_knee_id.py`, full mode) via the
segment reducer (`tools/screen_segments.py`). It adds nothing physical: every per-frame definition,
the guard-band dilation, the minimum-segment filter and the bin grid come from `screen_segments`,
which is imported, not copied. What this tool adds is (a) bank-level orchestration + screening of
clips that have no screen yet, (b) the *soft* mask `bin_score` alongside the hard `bin_eligible`,
and (c) a hash manifest so a training run can prove which mask it consumed.

SOFT vs HARD MASK
    bin_score[b]    = fraction of bin b that survives (guard band applied, short feasible runs
                      dropped). Continuous in [0,1]. This is the soft m_b.
    bin_eligible[b] = 1 iff bin_score[b] >= --min-bin-frac. This is the hard m_b.
Both are emitted from the same `kept` frame mask, and the tool asserts that thresholding
`bin_score` reproduces `screen_segments.bin_eligibility` exactly. A run that fails that assertion
aborts rather than shipping a mask whose two forms disagree.

UNFLAGGED CLIPS -- POLICY (this is a decision, not a fact)
    The bank-wide screen flags a clip when its clip-level `infeasible_frac` exceeds 0.10. It is
    tempting to declare every bin of an unflagged clip eligible and screen only the flagged ones.
    That is WRONG in general: a clip at infeasible_frac = 0.09 has ~9% of its frames infeasible,
    and if they are contiguous they can wipe out a bin (at bin_frames=50 on a 10 s clip, 9% is
    45 frames -- almost a whole bin) while the clip stays under the clip-level threshold. The
    clip-level threshold is exactly the instrument whose loss this project measures; inheriting it
    inside the sidecar would beg the question.

    DEFAULT POLICY: `--unflagged-policy screen` -- every clip in the bank is screened in full mode
    and reduced identically. No clip-level threshold appears anywhere in the sidecar. A full-mode
    screen costs ~1 s of CPU per clip, so this is affordable for banks of this size (800 clips
    ~= 3 min on 6 workers) and removes the assumption entirely.

    ALTERNATIVE (reconstructible): `--unflagged-policy assume-eligible` emits, for every clip whose
    clip-level `infeasible_frac <= --flag-threshold`, an all-ones mask with
    `"policy": "assumed_eligible"` and no screen provenance, and screens only the flagged clips.
    This reproduces the cheap variant bit-for-bit and is what `summarize` compares against to
    report how many bins the shortcut would have wrongly declared eligible.

Every sidecar records which policy produced it, so the two can never be silently mixed.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, "tools")
DEFAULT_PY = os.path.join(REPO, "bridge", ".venv", "bin", "python")
DEFAULT_FEAS_CSV = os.path.join(REPO, "reports", "feasibility_all", "feasibility.csv")
DEFAULT_SCREEN_CACHE = os.path.join(REPO, "reports", "eligibility", "screens")
PRODUCTION_GAP_M = 0.06
SCHEMA_VERSION = "eligibility_sidecar/1"


def _load_screen_segments():
    """Import tools/screen_segments.py by path (tools/ is not a package)."""
    path = os.path.join(TOOLS, "screen_segments.py")
    spec = importlib.util.spec_from_file_location("screen_segments", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SS = _load_screen_segments()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_clip_list(path: str) -> list[str]:
    seen, out = set(), []
    for line in open(path):
        c = line.strip()
        if c and not c.startswith("#") and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def load_json_any(path: str) -> dict:
    if path.endswith(".gz"):
        with gzip.open(path, "rt") as fh:
            return json.load(fh)
    with open(path) as fh:
        return json.load(fh)


def find_screen(clip: str, dirs: list[str]) -> str | None:
    for d in dirs:
        for ext in (".json", ".json.gz"):
            p = os.path.join(d, clip + ext)
            if os.path.exists(p):
                return p
    return None


def run_screen(clip: str, cache_dir: str, gap: float, python_bin: str, nice_n: int,
               gzip_out: bool) -> str:
    """Full-mode dynamic-feasibility screen for one clip. CPU only, nice'd. Returns path."""
    os.makedirs(cache_dir, exist_ok=True)
    tmp = os.path.join(cache_dir, f".{clip}.{os.getpid()}.tmp.json")
    env = dict(os.environ)
    env["CUDA_VISIBLE_DEVICES"] = ""          # hard rule: this tool never touches the GPU
    cmd = ["nice", "-n", str(nice_n), python_bin, os.path.join(TOOLS, "n1_knee_id.py"),
           "--clip", clip, "--t0", "0", "--t1", "1e9", "--gap", str(gap), "--out", tmp]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.exists(tmp):
        if os.path.exists(tmp):
            os.remove(tmp)
        raise RuntimeError(f"screen failed for {clip}: rc={proc.returncode} {proc.stderr[-400:]}")
    final = os.path.join(cache_dir, clip + (".json.gz" if gzip_out else ".json"))
    if gzip_out:
        with open(tmp, "rb") as fi, gzip.open(final, "wb", compresslevel=6) as fo:
            fo.writelines(fi)
        os.remove(tmp)
    else:
        os.replace(tmp, final)
    return final


def kept_mask_from_segments(reduced: dict) -> np.ndarray:
    """Rebuild the frame-level survivor mask from the reducer's own segment list.

    Derived from `reduce_clip`'s output rather than recomputed, so the soft mask cannot drift from
    the hard mask. Verified against the reducer's `feasible_frac_kept` before use.
    """
    n, fps = int(reduced["frames"]), float(reduced["fps"])
    kept = np.zeros(n, dtype=bool)
    for a_s, b_s in reduced["feasible_segments_s"]:
        a, b = int(round(a_s * fps)), int(round(b_s * fps))
        kept[max(0, a):min(n, b)] = True
    if abs(float(kept.mean()) - float(reduced["feasible_frac_kept"])) > 1e-9:
        raise RuntimeError(
            f"{reduced['clip']}: segment round-trip lost frames "
            f"({kept.mean():.9f} vs {reduced['feasible_frac_kept']:.9f}); refusing to emit a mask")
    return kept


def bin_scores(kept: np.ndarray, bin_frames: int) -> np.ndarray:
    """Soft m_b: fraction of each bin that survives. Same grid `screen_segments` bins on."""
    n = len(kept)
    return np.array([kept[s:min(s + bin_frames, n)].mean() for s in range(0, n, bin_frames)],
                    dtype=float)


def sidecar_from_screen(screen: dict, *, guard_s: float, min_seg_s: float, bin_frames: int,
                        min_bin_frac: float, severity: str, screen_source: str) -> dict:
    reduced = SS.reduce_clip(screen, guard_s=guard_s, min_seg_s=min_seg_s, bin_frames=bin_frames,
                             min_bin_frac=min_bin_frac, severity=severity)
    kept = kept_mask_from_segments(reduced)
    score = bin_scores(kept, bin_frames)
    hard = (score >= min_bin_frac).astype(int)
    ref = np.asarray(reduced["bin_eligible"], dtype=int)
    if hard.shape != ref.shape or not np.array_equal(hard, ref):
        raise RuntimeError(f"{reduced['clip']}: soft/hard mask disagree with screen_segments "
                           f"({hard.tolist()} vs {ref.tolist()})")
    return {
        # --- the runtime contract ---
        "clip": reduced["clip"],
        "fps": reduced["fps"],
        "frames": reduced["frames"],
        "bin_frames": bin_frames,
        "guard_s": guard_s,
        "severity": severity,
        "bin_eligible": hard.tolist(),
        "bin_score": [round(float(v), 6) for v in score],
        "n_bins": int(len(score)),
        "n_bins_eligible": int(hard.sum()),
        "screen_gap_m": reduced["screen_gap_m"],
        "screen_schema": reduced["screen_schema"],
        # --- provenance / reduction parameters ---
        "schema_version": SCHEMA_VERSION,
        "policy": "screened",
        "min_seg_s": min_seg_s,
        "min_bin_frac": min_bin_frac,
        "screen_source": os.path.relpath(screen_source, REPO),
        # --- clip-level scalars, for reconciliation against the bank-wide screen ---
        "bin_eligible_frac": float(hard.mean()) if len(hard) else 0.0,
        "bin_score_mean": float(score.mean()) if len(score) else 0.0,
        "airborne_frac": reduced["airborne_frac"],
        "infeasible_frac": reduced["infeasible_frac"],
        "torque_infeasible_frac": reduced["torque_infeasible_frac"],
        "severe_frac": reduced["severe_frac"],
        "severe_frac_guarded": reduced["severe_frac_guarded"],
        "feasible_frac_kept": reduced["feasible_frac_kept"],
        "n_severe_windows": reduced["n_severe_windows"],
        "n_feasible_segments": reduced["n_feasible_segments"],
        "severe_windows_s": reduced["severe_windows_s"],
        "feasible_segments_s": reduced["feasible_segments_s"],
        "unsupported_ratio_p95": reduced["unsupported_ratio_p95"],
    }


def sidecar_assumed(clip: str, frames: int, fps: float, *, guard_s: float, min_seg_s: float,
                    bin_frames: int, min_bin_frac: float, severity: str,
                    infeasible_frac: float) -> dict:
    n_bins = int(math.ceil(frames / bin_frames)) if frames else 0
    return {
        "clip": clip, "fps": fps, "frames": frames, "bin_frames": bin_frames, "guard_s": guard_s,
        "severity": severity,
        "bin_eligible": [1] * n_bins,
        "bin_score": [1.0] * n_bins,
        "n_bins": n_bins, "n_bins_eligible": n_bins,
        "screen_gap_m": None, "screen_schema": "assumed",
        "schema_version": SCHEMA_VERSION,
        "policy": "assumed_eligible",
        "min_seg_s": min_seg_s, "min_bin_frac": min_bin_frac,
        "screen_source": None,
        "bin_eligible_frac": 1.0, "bin_score_mean": 1.0,
        "infeasible_frac": infeasible_frac,
    }


def load_feasibility_csv(path: str) -> dict[str, dict]:
    out = {}
    if not os.path.exists(path):
        return out
    for row in csv.DictReader(open(path)):
        out[row["clip"]] = row
    return out


# --------------------------------------------------------------------------------------- build

def cmd_build(args) -> int:
    clips = read_clip_list(args.tier)
    bank = args.bank or os.path.splitext(os.path.basename(args.tier))[0]
    gtag = f"{args.guard_s:g}".replace(".", "p")
    out_dir = args.out_dir or os.path.join(REPO, "reports", "eligibility",
                                           f"{bank}_guard{gtag}_bin{args.bin_frames}")
    os.makedirs(out_dir, exist_ok=True)
    screen_dirs = list(args.screen_dir) + [args.screen_cache]
    feas = load_feasibility_csv(args.feasibility_csv)

    assume = args.unflagged_policy == "assume-eligible"
    todo = []
    for c in clips:
        row = feas.get(c)
        if assume and row is not None and float(row["infeasible_frac"]) <= args.flag_threshold:
            todo.append((c, "assumed"))
        else:
            todo.append((c, "screen"))
    n_assumed = sum(1 for _, m in todo if m == "assumed")
    n_cached = sum(1 for c, m in todo if m == "screen" and find_screen(c, screen_dirs))
    print(f"[build] bank={bank} clips={len(clips)} guard={args.guard_s}s bin={args.bin_frames} "
          f"min_bin_frac={args.min_bin_frac} policy={args.unflagged_policy}", file=sys.stderr)
    print(f"[build] {n_assumed} assumed-eligible, {n_cached} screens reused, "
          f"{len(clips) - n_assumed - n_cached} to screen ({args.workers} nice'd CPU workers)",
          file=sys.stderr)

    errors: list[str] = []

    def work(item):
        clip, mode = item
        try:
            if mode == "assumed":
                row = feas[clip]
                return sidecar_assumed(clip, int(row["frames"]), float(row["fps"]),
                                       guard_s=args.guard_s, min_seg_s=args.min_seg_s,
                                       bin_frames=args.bin_frames, min_bin_frac=args.min_bin_frac,
                                       severity=args.severity,
                                       infeasible_frac=float(row["infeasible_frac"]))
            path = find_screen(clip, screen_dirs)
            if path is None:
                if args.no_screen:
                    raise RuntimeError("no screen on disk and --no-screen was given")
                path = run_screen(clip, args.screen_cache, args.gap, args.python_bin,
                                  args.nice, not args.no_gzip_screens)
            return sidecar_from_screen(load_json_any(path), guard_s=args.guard_s,
                                       min_seg_s=args.min_seg_s, bin_frames=args.bin_frames,
                                       min_bin_frac=args.min_bin_frac, severity=args.severity,
                                       screen_source=path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{clip}: {exc}")
            return None

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = [r for r in ex.map(work, todo) if r is not None]
    print(f"[build] {len(results)}/{len(clips)} clips in {time.time()-t0:.1f}s", file=sys.stderr)
    for e in errors[:20]:
        print(f"ERROR {e}", file=sys.stderr)
    if errors and not args.allow_partial:
        print(f"[build] {len(errors)} failures; refusing to write a partial manifest "
              f"(pass --allow-partial to override)", file=sys.stderr)
        return 1

    entries = {}
    for r in sorted(results, key=lambda d: d["clip"]):
        p = os.path.join(out_dir, r["clip"] + ".json")
        with open(p, "w") as fh:
            json.dump(r, fh, indent=1, sort_keys=True)
        entries[r["clip"]] = {
            "sha256": sha256_file(p), "bytes": os.path.getsize(p), "policy": r["policy"],
            "n_bins": r["n_bins"], "n_bins_eligible": r["n_bins_eligible"],
            "screen_source": r["screen_source"],
        }
    set_line = "".join(f"{c}  {entries[c]['sha256']}\n" for c in sorted(entries))
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "bank": bank,
        "tier_file": os.path.relpath(args.tier, REPO),
        "tier_sha256": sha256_file(args.tier),
        "n_clips_requested": len(clips),
        "n_clips_written": len(entries),
        "params": {
            "guard_s": args.guard_s, "bin_frames": args.bin_frames,
            "min_bin_frac": args.min_bin_frac, "min_seg_s": args.min_seg_s,
            "severity": args.severity, "screen_gap_m": args.gap,
            "unflagged_policy": args.unflagged_policy, "flag_threshold": args.flag_threshold,
        },
        "tool_sha256": sha256_file(os.path.abspath(__file__)),
        "reducer_sha256": sha256_file(os.path.join(TOOLS, "screen_segments.py")),
        "screener_sha256": sha256_file(os.path.join(TOOLS, "n1_knee_id.py")),
        "feasibility_csv": os.path.relpath(args.feasibility_csv, REPO)
                           if os.path.exists(args.feasibility_csv) else None,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "set_sha256": sha256_bytes(set_line.encode()),
        "clips": entries,
        "errors": errors,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    with open(os.path.join(out_dir, "SHA256SUMS"), "w") as fh:
        fh.write(set_line)

    fields = ["clip", "policy", "frames", "fps", "n_bins", "n_bins_eligible", "bin_eligible_frac",
              "bin_score_mean", "infeasible_frac", "severe_frac", "severe_frac_guarded",
              "feasible_frac_kept", "n_severe_windows", "screen_schema", "screen_gap_m"]
    with open(os.path.join(out_dir, "index.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in sorted(results, key=lambda d: d["clip"]):
            w.writerow({k: r.get(k) for k in fields})

    tot_b = sum(e["n_bins"] for e in entries.values())
    tot_e = sum(e["n_bins_eligible"] for e in entries.values())
    dead = sum(1 for e in entries.values() if e["n_bins_eligible"] == 0)
    print(f"[build] {out_dir}", file=sys.stderr)
    print(f"[build] set_sha256 {manifest['set_sha256']}", file=sys.stderr)
    print(f"[build] bins eligible {tot_e}/{tot_b} ({tot_e/max(tot_b,1):.4f}); "
          f"clips with zero eligible bins: {dead}", file=sys.stderr)
    return 0


# ----------------------------------------------------------------------------------- summarize

BANDS = [(0.0, 0.01), (0.01, 0.05), (0.05, 0.10), (0.10, 0.15), (0.15, 0.25),
         (0.25, 0.50), (0.50, 1.01)]
CLIP44 = "BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos"
CLIP44_EXPECT = {"severe_windows_s": [[0.72, 1.62], [8.06, 8.46]], "n_bins": 10,
                 "n_bins_eligible": 7, "bin_frames": 50, "guard_s": 0.0}


def _load_set(d: str) -> tuple[dict, dict[str, dict]]:
    man = json.load(open(os.path.join(d, "manifest.json")))
    rows = {c: json.load(open(os.path.join(d, c + ".json"))) for c in sorted(man["clips"])}
    return man, rows


def _minutes(n_bins: float, bin_frames: int, fps: float) -> float:
    return n_bins * bin_frames / fps / 60.0


def _mask_minutes(rows, soft: bool = False) -> float:
    """Wall-clock minutes the mask admits, counting each bin's ACTUAL length.

    The last bin of a clip is short. Counting bins x bin_frames overstates it, which would make
    the bin-level columns non-comparable with the exact segment-level and clip-level minutes.
    """
    tot = 0.0
    for r in rows:
        n, bf, fps = r["frames"], r["bin_frames"], r["fps"]
        w = r["bin_score"] if soft else r["bin_eligible"]
        tot += sum(min(bf, n - i * bf) * v for i, v in enumerate(w)) / fps
    return tot / 60.0


def _bank_stats(rows: dict[str, dict]) -> dict:
    rs = list(rows.values())
    nb = sum(r["n_bins"] for r in rs)
    ne = sum(r["n_bins_eligible"] for r in rs)
    soft = sum(sum(r["bin_score"]) for r in rs)
    fps = rs[0]["fps"] if rs else 50.0
    bf = rs[0]["bin_frames"] if rs else 50
    # exact clip minutes (last bin is short), and bin-grid minutes (what the sampler sees)
    clip_min = sum(r["frames"] / r["fps"] for r in rs) / 60.0
    seg_min = sum(r.get("feasible_frac_kept", 1.0) * r["frames"] / r["fps"] for r in rs) / 60.0
    return {
        "segment_minutes_kept": seg_min,
        "soft_minutes": _minutes(soft, bf, fps),
        "n_clips": len(rs), "n_bins": nb, "n_bins_eligible": ne,
        "bin_eligible_frac": ne / max(nb, 1),
        "soft_mass": soft, "soft_mass_frac": soft / max(nb, 1),
        "n_clips_zero_eligible": sum(1 for r in rs if r["n_bins_eligible"] == 0),
        "n_clips_all_eligible": sum(1 for r in rs if r["n_bins_eligible"] == r["n_bins"]),
        "eligible_minutes": _mask_minutes(rs), "soft_minutes_exact": _mask_minutes(rs, soft=True),
        "grid_minutes": _minutes(nb, bf, fps), "clip_minutes": clip_min,
    }


def _prune_vs_bin(rows: dict[str, dict], flag_threshold: float) -> dict:
    """What clip-level pruning at `flag_threshold` throws away that the bin mask keeps."""
    rs = list(rows.values())
    bf, fps = rs[0]["bin_frames"], rs[0]["fps"]
    flagged = [r for r in rs if r.get("infeasible_frac", 0.0) > flag_threshold]
    unflag = [r for r in rs if r.get("infeasible_frac", 0.0) <= flag_threshold]
    return {
        "flag_threshold": flag_threshold,
        "n_flagged": len(flagged), "n_unflagged": len(unflag),
        "flagged_bins": sum(r["n_bins"] for r in flagged),
        "flagged_bins_eligible": sum(r["n_bins_eligible"] for r in flagged),
        "flagged_minutes_discarded_by_clip_pruning": sum(
            r["frames"] / r["fps"] for r in flagged) / 60.0,
        "flagged_minutes_recovered_by_bin_mask": _mask_minutes(flagged),
        "flagged_minutes_recovered_at_segment_level": sum(
            r.get("feasible_frac_kept", 1.0) * r["frames"] / r["fps"] for r in flagged) / 60.0,
        "flagged_minutes_recovered_by_soft_mask": _mask_minutes(flagged, soft=True),
        "recovery_frac_of_flagged": (sum(r["n_bins_eligible"] for r in flagged)
                                     / max(sum(r["n_bins"] for r in flagged), 1)),
        "unflagged_bins": sum(r["n_bins"] for r in unflag),
        "unflagged_bins_ineligible": sum(r["n_bins"] - r["n_bins_eligible"] for r in unflag),
        "unflagged_clips_losing_a_bin": sum(1 for r in unflag
                                            if r["n_bins_eligible"] < r["n_bins"]),
        "unflagged_clips_losing_all_bins": sum(1 for r in unflag if r["n_bins_eligible"] == 0),
        "unflagged_minutes_ineligible": (sum(r["frames"] / r["fps"] for r in unflag) / 60.0
                                         - _mask_minutes(unflag)),
    }


def _band_table(byguard: dict[float, dict[str, dict]]) -> list[dict]:
    guards = sorted(byguard)
    base = byguard[guards[0]]
    out = []
    for lo, hi in BANDS:
        clips = [c for c, r in base.items() if lo <= r.get("infeasible_frac", 0.0) < hi]
        if not clips:
            continue
        e = {"band": f"[{lo:.2f},{hi:.2f})", "n_clips": len(clips),
             "n_bins": sum(base[c]["n_bins"] for c in clips)}
        for g in guards:
            rs = [byguard[g][c] for c in clips]
            nb = sum(r["n_bins"] for r in rs)
            ne = sum(r["n_bins_eligible"] for r in rs)
            e[f"elig_frac_g{g:g}"] = ne / max(nb, 1)
            e[f"mean_clip_elig_g{g:g}"] = sum(r["bin_eligible_frac"] for r in rs) / len(rs)
            e[f"soft_frac_g{g:g}"] = sum(sum(r["bin_score"]) for r in rs) / max(nb, 1)
            e[f"zero_elig_clips_g{g:g}"] = sum(1 for r in rs if r["n_bins_eligible"] == 0)
        out.append(e)
    return out


def _ascii_scatter(rows: dict[str, dict], w: int = 40, h: int = 16, xmax: float = 0.6) -> str:
    grid = [[0] * w for _ in range(h)]
    for r in rows.values():
        x = min(r.get("infeasible_frac", 0.0) / xmax, 0.999)
        y = min(max(r["bin_eligible_frac"], 0.0), 0.999)
        grid[h - 1 - int(y * h)][int(x * w)] += 1
    def ch(n):
        return " " if n == 0 else ("." if n == 1 else ("o" if n < 4 else ("O" if n < 10 else "#")))
    lines = []
    for i, row in enumerate(grid):
        lab = f"{1.0 - i / h:4.2f}"
        lines.append(f"{lab} |" + "".join(ch(n) for n in row) + "|")
    lines.append("     +" + "-" * w + "+")
    lines.append("     0.00" + " " * (w - 8) + f"{xmax:.2f}+")
    lines.append("     bin eligible fraction (y) vs clip infeasible_frac (x)")
    return "\n".join(lines)


def cmd_summarize(args) -> int:
    sets = {}
    for spec in args.set:
        label, d = spec.split("=", 1)
        sets[label] = _load_set(d if os.path.isabs(d) else os.path.join(REPO, d))

    out = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sets": {}, "banks": {}, "policy_comparison": {}, "clip44_check": None}
    for label, (man, rows) in sets.items():
        out["sets"][label] = {
            "bank": man["bank"], "tier_file": man["tier_file"], "params": man["params"],
            "set_sha256": man["set_sha256"], "tool_sha256": man["tool_sha256"],
            "reducer_sha256": man["reducer_sha256"], "n_clips": man["n_clips_written"],
            "stats": _bank_stats(rows),
        }

    # group the screened sets by tier file -> guard
    screened = {lab: v for lab, v in sets.items()
                if v[0]["params"]["unflagged_policy"] == "screen"}
    banks: dict[str, dict[float, dict]] = {}
    for lab, (man, rows) in screened.items():
        banks.setdefault(man["tier_file"], {})[man["params"]["guard_s"]] = (lab, rows)

    md_scatter_paths = []
    for tier, byg in sorted(banks.items()):
        bank = os.path.splitext(os.path.basename(tier))[0]
        byguard = {g: r for g, (lab, r) in byg.items()}
        guards = sorted(byguard)
        out["banks"][bank] = {
            "tier_file": tier, "guards": guards,
            "labels": {f"{g:g}": byg[g][0] for g in guards},
            "stats_by_guard": {f"{g:g}": _bank_stats(byguard[g]) for g in guards},
            "prune_vs_bin_by_guard": {f"{g:g}": _prune_vs_bin(byguard[g], args.flag_threshold)
                                      for g in guards},
            "band_table": _band_table(byguard),
            "ascii_scatter_g0": _ascii_scatter(byguard[guards[0]]),
        }
        # per-clip scatter csv
        clips = sorted(byguard[guards[0]])
        rowsout = []
        for c in clips:
            base = byguard[guards[0]][c]
            e = {"clip": c, "frames": base["frames"], "fps": base["fps"],
                 "infeasible_frac": base.get("infeasible_frac"),
                 "severe_frac": base.get("severe_frac"), "n_bins": base["n_bins"]}
            for g in guards:
                r = byguard[g][c]
                e[f"n_elig_g{g:g}"] = r["n_bins_eligible"]
                e[f"elig_frac_g{g:g}"] = round(r["bin_eligible_frac"], 6)
                e[f"soft_frac_g{g:g}"] = round(sum(r["bin_score"]) / max(r["n_bins"], 1), 6)
            rowsout.append(e)
        p = os.path.join(REPO, "reports", "eligibility", f"scatter_{bank}.csv")
        with open(p, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rowsout[0].keys()))
            w.writeheader(); w.writerows(rowsout)
        md_scatter_paths.append(p)

    # screened vs assume-eligible, matched on (tier_file, guard_s)
    for lab, (man, rows) in sets.items():
        if man["params"]["unflagged_policy"] != "assume-eligible":
            continue
        key = (man["tier_file"], man["params"]["guard_s"])
        match = [(l2, v) for l2, v in screened.items()
                 if (v[0]["tier_file"], v[0]["params"]["guard_s"]) == key]
        if not match:
            continue
        lab_s, (man_s, rows_s) = match[0]
        assumed = [c for c, r in rows.items() if r["policy"] == "assumed_eligible"]
        if not assumed:
            continue
        wrong = sum(rows_s[c]["n_bins"] - rows_s[c]["n_bins_eligible"] for c in assumed)
        tot_bins = sum(r["n_bins"] for r in rows.values())
        bf, fps = rows_s[assumed[0]]["bin_frames"], rows_s[assumed[0]]["fps"]  # noqa: F841
        out["policy_comparison"][lab] = {
            "screened_set": lab_s, "tier_file": man["tier_file"],
            "guard_s": man["params"]["guard_s"], "flag_threshold": man["params"]["flag_threshold"],
            "n_clips_assumed": len(assumed),
            "n_clips_assumed_that_lose_a_bin": sum(
                1 for c in assumed if rows_s[c]["n_bins_eligible"] < rows_s[c]["n_bins"]),
            "n_clips_assumed_that_lose_every_bin": sum(
                1 for c in assumed if rows_s[c]["n_bins_eligible"] == 0),
            "bins_wrongly_eligible": wrong,
            "bins_wrongly_eligible_frac_of_bank": wrong / max(tot_bins, 1),
            "minutes_wrongly_eligible": (sum(rows_s[c]["frames"] / rows_s[c]["fps"]
                                              for c in assumed) / 60.0
                                         - _mask_minutes([rows_s[c] for c in assumed])),
            "worst_clips": sorted(
                ({"clip": c, "infeasible_frac": rows_s[c].get("infeasible_frac"),
                  "n_bins": rows_s[c]["n_bins"], "n_bins_eligible": rows_s[c]["n_bins_eligible"]}
                 for c in assumed if rows_s[c]["n_bins_eligible"] < rows_s[c]["n_bins"]),
                key=lambda d: d["n_bins_eligible"] / max(d["n_bins"], 1))[:10],
        }

    # self-validating sanity check on the known case
    for lab, (man, rows) in screened.items():
        if CLIP44 in rows and man["params"]["guard_s"] == 0.0 and man["params"]["bin_frames"] == 50:
            r = rows[CLIP44]
            ok = (r["severe_windows_s"] == CLIP44_EXPECT["severe_windows_s"]
                  and r["n_bins"] == CLIP44_EXPECT["n_bins"]
                  and r["n_bins_eligible"] == CLIP44_EXPECT["n_bins_eligible"])
            out["clip44_check"] = {
                "set": lab, "pass": bool(ok), "expected": CLIP44_EXPECT,
                "got": {"severe_windows_s": r["severe_windows_s"], "n_bins": r["n_bins"],
                        "n_bins_eligible": r["n_bins_eligible"],
                        "bin_eligible": r["bin_eligible"], "bin_score": r["bin_score"],
                        "infeasible_frac": r["infeasible_frac"]},
            }
            break

    os.makedirs(os.path.join(REPO, "reports", "eligibility"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "eligibility_summary.json"), "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    md = _render_md(out, md_scatter_paths)
    with open(os.path.join(REPO, "reports", "eligibility_summary.md"), "w") as fh:
        fh.write(md)
    print(md)
    return 0


def _render_md(out: dict, scatter_paths: list[str]) -> str:
    L = []
    A = L.append
    A("# Eligibility sidecar: per-clip, per-bin `m_b` for FGAS\n")
    A(f"Generated {out['generated_utc']} by `tools/build_eligibility_sidecar.py`.\n")
    A("`m_b` is the mask FGAS multiplies into *both* terms of\n")
    A("`p_b = (1-rho)*m_b*psi(f_b)/sum_j m_j*psi(f_j) + rho*m_b/sum_j m_j`.")
    A("`bin_eligible` is the hard mask (0/1); `bin_score` is the soft mask (fraction of the bin")
    A("that survives the feasibility screen, guard band and minimum-segment filter). Thresholding")
    A("`bin_score` at `min_bin_frac` reproduces `bin_eligible` exactly -- the builder asserts it.\n")

    A("## Sets\n")
    A("| set | clips | guard s | bin frames | min_bin_frac | min_seg_s | severity | policy | set_sha256 |")
    A("|---|---:|---:|---:|---:|---:|---|---|---|")
    for lab, s in sorted(out["sets"].items()):
        p = s["params"]
        A(f"| `{lab}` | {s['n_clips']} | {p['guard_s']:g} | {p['bin_frames']} | "
          f"{p['min_bin_frac']:g} | {p['min_seg_s']:g} | {p['severity']} | "
          f"{p['unflagged_policy']} | `{s['set_sha256'][:16]}` |")
    A("")

    A("## Eligible-bin distribution\n")
    A("| bank | guard s | clips | bins | eligible bins | eligible % | soft mass % | "
      "clips 0 eligible | clips all eligible | eligible min | segment min | bank min |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for bank, b in sorted(out["banks"].items()):
        for g in b["guards"]:
            s = b["stats_by_guard"][f"{g:g}"]
            A(f"| {bank} | {g:g} | {s['n_clips']} | {s['n_bins']} | {s['n_bins_eligible']} | "
              f"{100*s['bin_eligible_frac']:.1f}% | {100*s['soft_mass_frac']:.1f}% | "
              f"{s['n_clips_zero_eligible']} | {s['n_clips_all_eligible']} | "
              f"{s['eligible_minutes']:.2f} | {s['segment_minutes_kept']:.2f} | "
              f"{s['clip_minutes']:.2f} |")
    A("")
    A("All minute columns are exact wall-clock (the final, short bin of each clip counts its true")
    A("length, not a whole bin), so bin-level, segment-level and clip-level minutes are comparable.")
    A("")

    A("## What clip-level thresholding throws away\n")
    A("A clip-level screen at `infeasible_frac > 0.10` discards a flagged clip whole. The bin mask")
    A("keeps its feasible bins. Below: of the material a clip-level prune would delete, how much")
    A("the bin mask retains -- and, in the other direction, how much *unflagged* material the bin")
    A("mask correctly refuses.\n")
    A("| bank | guard s | flagged clips | flagged min (pruned whole) | segment-level min | "
      "soft-bin min | hard-bin min | hard recovery | unflagged clips losing >=1 bin | "
      "unflagged min ineligible |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for bank, b in sorted(out["banks"].items()):
        for g in b["guards"]:
            p = b["prune_vs_bin_by_guard"][f"{g:g}"]
            A(f"| {bank} | {g:g} | {p['n_flagged']} | "
              f"{p['flagged_minutes_discarded_by_clip_pruning']:.2f} | "
              f"{p['flagged_minutes_recovered_at_segment_level']:.2f} | "
              f"{p['flagged_minutes_recovered_by_soft_mask']:.2f} | "
              f"{p['flagged_minutes_recovered_by_bin_mask']:.2f} | "
              f"{100*p['recovery_frac_of_flagged']:.1f}% | "
              f"{p['unflagged_clips_losing_a_bin']}/{p['n_unflagged']} | "
              f"{p['unflagged_minutes_ineligible']:.2f} |")
    A("")
    A("`segment-level` is the frame-level feasible material after the guard band and the")
    A("minimum-segment filter; `hard-bin` is what survives the sampler's bin grid at")
    A("`min_bin_frac=1.0`; `soft-bin` is the same grid weighted by `bin_score`. The gap between")
    A("segment-level and hard-bin is the price of the grid: a bin straddling the edge of a severe")
    A("window is discarded whole even though most of it is feasible. The soft mask recovers it.\n")

    A("## Clip-level `infeasible_frac` vs bin-level eligible fraction\n")
    for bank, b in sorted(out["banks"].items()):
        gs = b["guards"]
        A(f"### {bank}\n")
        hdr = "| infeasible_frac band | clips | bins |"
        sep = "|---|---:|---:|"
        for g in gs:
            hdr += f" eligible % (g={g:g}) | soft % (g={g:g}) | clips 0 elig (g={g:g}) |"
            sep += "---:|---:|---:|"
        A(hdr); A(sep)
        for row in b["band_table"]:
            line = f"| {row['band']} | {row['n_clips']} | {row['n_bins']} |"
            for g in gs:
                line += (f" {100*row[f'elig_frac_g{g:g}']:.1f}% |"
                         f" {100*row[f'soft_frac_g{g:g}']:.1f}% |"
                         f" {row[f'zero_elig_clips_g{g:g}']} |")
            A(line)
        A("")
        A(f"Scatter (y = bin eligible fraction at guard {gs[0]:g}, x = clip `infeasible_frac`; "
          f"`.`=1 clip, `o`<4, `O`<10, `#`>=10):\n")
        A("```")
        A(b["ascii_scatter_g0"])
        A("```\n")
    if scatter_paths:
        A("Per-clip CSVs: " + ", ".join(f"`{os.path.relpath(p, REPO)}`" for p in scatter_paths) + "\n")

    if out["policy_comparison"]:
        A("## Unflagged-clip policy: `screen` (default) vs `assume-eligible`\n")
        A("The cheap alternative screens only clips flagged at the clip level and declares every")
        A("bin of the rest eligible. It is reconstructible with `--unflagged-policy assume-eligible`.")
        A("The cost of that shortcut, measured:\n")
        A("| set | guard s | clips assumed | assumed clips losing >=1 bin | losing every bin | "
          "bins wrongly eligible | % of bank | minutes |")
        A("|---|---:|---:|---:|---:|---:|---:|---:|")
        for lab, c in sorted(out["policy_comparison"].items()):
            A(f"| `{lab}` | {c['guard_s']:g} | {c['n_clips_assumed']} | "
              f"{c['n_clips_assumed_that_lose_a_bin']} | "
              f"{c['n_clips_assumed_that_lose_every_bin']} | {c['bins_wrongly_eligible']} | "
              f"{100*c['bins_wrongly_eligible_frac_of_bank']:.2f}% | "
              f"{c['minutes_wrongly_eligible']:.1f} |")
        A("")
        A("Worst offenders (clips the clip-level threshold passes but the bin mask does not):\n")
        for lab, c in sorted(out["policy_comparison"].items()):
            A(f"- `{lab}`:")
            for wcl in c["worst_clips"][:5]:
                A(f"  - `{wcl['clip']}` infeasible_frac={wcl['infeasible_frac']:.3f} -> "
                  f"{wcl['n_bins_eligible']}/{wcl['n_bins']} bins eligible")
        A("")

    c44 = out.get("clip44_check")
    if c44:
        A("## Sanity check: clip #44\n")
        A(f"`{CLIP44}` (set `{c44['set']}`, guard 0 s, bin 50 frames): "
          f"**{'PASS' if c44['pass'] else 'FAIL'}**\n")
        A(f"- severe windows: `{c44['got']['severe_windows_s']}` "
          f"(expected `{c44['expected']['severe_windows_s']}`)")
        A(f"- bins eligible: {c44['got']['n_bins_eligible']}/{c44['got']['n_bins']} "
          f"(expected {c44['expected']['n_bins_eligible']}/{c44['expected']['n_bins']})")
        A(f"- `bin_eligible` = `{c44['got']['bin_eligible']}`")
        A(f"- `bin_score`    = `{c44['got']['bin_score']}`")
        A(f"- clip-level `infeasible_frac` = {c44['got']['infeasible_frac']:.6f} "
          f"(reconciles with the bank-wide screen)\n")

    A("## Caveats\n")
    A("- `severity=severe` = infeasible OR torque-infeasible. The published clip-level")
    A("  `infeasible_frac` scores an in-contact LP failure as 0; the mask does not inherit that")
    A("  hole, so `severe_frac >= infeasible_frac` and a clip can lose bins its clip-level number")
    A("  does not predict.")
    A("- `min_seg_s=1.0` drops feasible runs shorter than one second. On short clips (2-3 bins)")
    A("  this can zero out a clip whose `infeasible_frac` is tiny -- e.g. a 1.9 s clip cut by two")
    A("  brief severe windows has no 1 s feasible run at all. That is a deliberate episode-length")
    A("  policy, not a physics claim; rebuild with `--min-seg-s 0` to see the difference.")
    A("- `min_bin_frac=1.0` is strict: one severe frame disqualifies a bin. The soft mask")
    A("  `bin_score` is the unthresholded quantity; use it if you want a graded `m_b`.")
    A("- Guard band is framework-specific: mjlab observes only the current anchor (guard 0 s);")
    A("  SONIC observes 1.0 s of future reference, so it needs guard >= 1.0 s.")
    A("- All screens at the production contact gap 0.06 m. Mixing gaps invalidates the mask.")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build a sidecar set for one clip list")
    b.add_argument("--tier", required=True, help="clip list, one clip name per line")
    b.add_argument("--bank", default=None, help="label for the output dir (default: tier basename)")
    b.add_argument("--screen-dir", action="append", default=[],
                   help="directory of existing full-mode n1_knee_id.py JSONs (repeatable, "
                        "searched in order; .json and .json.gz both accepted)")
    b.add_argument("--screen-cache", default=DEFAULT_SCREEN_CACHE,
                   help="where freshly-run screens are written (and reused from)")
    b.add_argument("--guard-s", type=float, default=0.0,
                   help="guard-band half-width [s]. mjlab: 0 (no observation lookahead). "
                        "SONIC: >= 1.0 (num_future_frames*dt_future_ref_frames).")
    b.add_argument("--bin-frames", type=int, default=SS.DEFAULT_BIN_FRAMES)
    b.add_argument("--min-bin-frac", type=float, default=1.0,
                   help="bin_eligible = bin_score >= this (1.0 = strict)")
    b.add_argument("--min-seg-s", type=float, default=1.0)
    b.add_argument("--severity", choices=("severe", "infeasible"), default="severe")
    b.add_argument("--unflagged-policy", choices=("screen", "assume-eligible"), default="screen",
                   help="see module docstring. Default 'screen' makes no clip-level assumption.")
    b.add_argument("--flag-threshold", type=float, default=0.10,
                   help="clip-level infeasible_frac above which a clip is 'flagged' (only used "
                        "by --unflagged-policy assume-eligible)")
    b.add_argument("--feasibility-csv", default=DEFAULT_FEAS_CSV)
    b.add_argument("--gap", type=float, default=PRODUCTION_GAP_M,
                   help="contact gap for freshly-run screens (production: 0.06, NOT the "
                        "n1_knee_id.py argparse default 0.03)")
    b.add_argument("--workers", type=int, default=6)
    b.add_argument("--nice", type=int, default=15)
    b.add_argument("--python-bin", default=DEFAULT_PY)
    b.add_argument("--out-dir", default=None)
    b.add_argument("--no-gzip-screens", action="store_true")
    b.add_argument("--no-screen", action="store_true",
                   help="never invoke the screener; fail on any clip without a cached screen")
    b.add_argument("--allow-partial", action="store_true")
    b.set_defaults(func=cmd_build)

    s = sub.add_parser("summarize", help="cross-set distribution report")
    s.add_argument("--set", action="append", required=True, metavar="LABEL=DIR",
                   help="repeatable, e.g. mixed100_g0=reports/eligibility/tier_mixed100_guard0_bin50")
    s.add_argument("--flag-threshold", type=float, default=0.10,
                   help="clip-level infeasible_frac defining 'flagged', for the "
                        "clip-pruning-vs-bin-mask comparison")
    s.set_defaults(func=cmd_summarize)

    args = ap.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = ""   # belt and braces: never a GPU from this process tree
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
