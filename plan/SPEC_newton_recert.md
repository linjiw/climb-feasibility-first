# SPEC — TASK newton-1.0-recert: does the conformance certificate survive a major release? (DO NOT RUN)

*Status: spec only. Framing per v6: the S1/G0 certificate is **version-pinned**, not universal.*

## Version note (flagged, not re-litigated)

The certificate was earned against the Newton checkout at commit **`7bb6d02d`** (pip metadata
`1.6.0.dev0`, repo main of 2026-08; pins in `plan/PREREGISTRATION_G1_clip44.md`), with
MuJoCo Warp 3.11.0 / warp-lang 1.16.0 / MuJoCo 3.11.0 / mjlab v1.6.0. The directive's external
event — **Newton 1.0 GA (GTC 2026-03-17)** with a changed collision stack (SDF collision from CAD
meshes, hydroelastic contact) — names a release line whose numbering differs from our checkout's
pip version string; the recert must begin by resolving the exact GA tag/commit and its
MuJoCo-Warp dependency pin **and record both** before anything runs. If the GA line and our
checkout share the same MuJoCo-Warp version and SolverMuJoCo path, the recert tests the
*integration stack*; if the collision default changed under SolverMuJoCo, it also tests class-7.

## Minimal recert protocol (≈ 1 GPU-hour total; identical pass/fail to S1)

Environment: a fresh venv with Newton @ GA tag (exact pin recorded), everything else held at the
certificate's pins. The harness (`tools/s1_newton_conformance.py`) runs unmodified; any API break
is itself a finding (recorded, then minimally shimmed with the shim diffed in the report).

| step | check | pass criterion (identical to S1) | predicted-sensitive? |
|---|---|---|---|
| 1 | model diff (live MJWarp models, field-by-field) | only the known visual-mesh delta | **yes — class 7**: new collision defaults (SDF path, margins, hydroelastic flags) may surface as new opt/geom fields or changed defaults |
| 2 | static + spinning bias forces from identical (q, q̇) | |Δqfrc_bias| ≤ 1e-5 after DR mirror | no (mass/inertia path unchanged in release notes) |
| 3 | **float32 geometry class (class 4)** — geom_quat/pos deltas after import | bitwise-equal after exact-geometry mirror; without the mirror, record the raw deltas and compare to the 4e-7 baseline | **yes — the predicted-sensitive check.** A rewritten import/collision path can change rounding; the knife-edge frictional-contact flip is the failure mode to watch (contact-set diff at rest, 300 steps × 8 worlds, 0 mismatches required) |
| 4 | per-substep paired stepping across KIT_1226 window 290–312 | |Δq̇| ≤ 3e-5; identical nefc/nacon | yes if 3 moves |
| 5 | closed-loop survival, KIT_1226 n=32 ×2 + clip #44 n=32 | Δsurvival ≤ 1/32; Δerr ≤ 10 % | — |
| 6 | absorbed-writes count | 57–59 ± protocol events (unchanged env side) | no |

Report: one table (step → S1 value → GA value → pass/fail), the exact two version pins, and a
one-paragraph verdict for the companion note: *"the certificate is a property of a
(stack-pair, version-pair); here is what one major release did to it."* Either outcome is
publishable: survival intact = the taxonomy's checks are cheap insurance; a step-3 failure =
a live demonstration of class 4/7 on a real release, and a candidate minimal repro for the
Newton tracker (per TASK upstream-drafts, only if the behaviour is engine-side rather than
coupling-side).

Dependencies: none on sealed experiments; can run in any GPU gap after P-SIGN. Sentinel required.
