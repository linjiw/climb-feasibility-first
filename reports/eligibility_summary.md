# Eligibility sidecar: per-clip, per-bin `m_b` for FGAS

Generated 2026-08-19T21:26:42Z by `tools/build_eligibility_sidecar.py`.

`m_b` is the mask FGAS multiplies into *both* terms of

`p_b = (1-rho)*m_b*psi(f_b)/sum_j m_j*psi(f_j) + rho*m_b/sum_j m_j`.
`bin_eligible` is the hard mask (0/1); `bin_score` is the soft mask (fraction of the bin
that survives the feasibility screen, guard band and minimum-segment filter). Thresholding
`bin_score` at `min_bin_frac` reproduces `bin_eligible` exactly -- the builder asserts it.

## Sets

| set | clips | guard s | bin frames | min_bin_frac | min_seg_s | severity | policy | set_sha256 |
|---|---:|---:|---:|---:|---:|---|---|---|
| `mixed100_assume_g0` | 100 | 0 | 50 | 1 | 1 | severe | assume-eligible | `c1f38530379a30d6` |
| `mixed100_g0` | 100 | 0 | 50 | 1 | 1 | severe | screen | `bd742558d72bad2e` |
| `mixed100_g1.0` | 100 | 1 | 50 | 1 | 1 | severe | screen | `3279d44d149a3aa0` |
| `tier800_assume_g0` | 800 | 0 | 50 | 1 | 1 | severe | assume-eligible | `fc02d773ac5e1aa4` |
| `tier800_g0` | 800 | 0 | 50 | 1 | 1 | severe | screen | `783a52c77d87805d` |
| `tier800_g1.0` | 800 | 1 | 50 | 1 | 1 | severe | screen | `2508d575f721eebf` |

## Eligible-bin distribution

| bank | guard s | clips | bins | eligible bins | eligible % | soft mass % | clips 0 eligible | clips all eligible | eligible min | segment min | bank min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tier_800 | 0 | 800 | 9505 | 8495 | 89.4% | 93.8% | 9 | 561 | 135.87 | 142.83 | 152.36 |
| tier_800 | 1 | 800 | 9505 | 7845 | 82.5% | 84.6% | 46 | 561 | 125.43 | 128.66 | 152.36 |
| tier_mixed100 | 0 | 100 | 1300 | 986 | 75.8% | 85.1% | 9 | 44 | 15.90 | 17.90 | 21.00 |
| tier_mixed100 | 1 | 100 | 1300 | 811 | 62.4% | 66.8% | 23 | 44 | 13.04 | 13.99 | 21.00 |

All minute columns are exact wall-clock (the final, short bin of each clip counts its true
length, not a whole bin), so bin-level, segment-level and clip-level minutes are comparable.

## What clip-level thresholding throws away

A clip-level screen at `infeasible_frac > 0.10` discards a flagged clip whole. The bin mask
keeps its feasible bins. Below: of the material a clip-level prune would delete, how much
the bin mask retains -- and, in the other direction, how much *unflagged* material the bin
mask correctly refuses.

| bank | guard s | flagged clips | flagged min (pruned whole) | segment-level min | soft-bin min | hard-bin min | hard recovery | unflagged clips losing >=1 bin | unflagged min ineligible |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tier_800 | 0 | 99 | 20.21 | 12.48 | 12.48 | 9.16 | 46.4% | 140/701 | 5.43 |
| tier_800 | 1 | 99 | 20.21 | 5.85 | 5.85 | 4.68 | 24.2% | 140/701 | 11.39 |
| tier_mixed100 | 0 | 25 | 4.81 | 2.65 | 2.65 | 1.93 | 40.3% | 31/75 | 2.22 |
| tier_mixed100 | 1 | 25 | 4.81 | 1.33 | 1.33 | 1.10 | 23.3% | 31/75 | 4.25 |

`segment-level` is the frame-level feasible material after the guard band and the
minimum-segment filter; `hard-bin` is what survives the sampler's bin grid at
`min_bin_frac=1.0`; `soft-bin` is the same grid weighted by `bin_score`. The gap between
segment-level and hard-bin is the price of the grid: a bin straddling the edge of a severe
window is discarded whole even though most of it is feasible. The soft mask recovers it.

## Clip-level `infeasible_frac` vs bin-level eligible fraction

### tier_800

| infeasible_frac band | clips | bins | eligible % (g=0) | soft % (g=0) | clips 0 elig (g=0) | eligible % (g=1) | soft % (g=1) | clips 0 elig (g=1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| [0.00,0.01) | 585 | 6839 | 99.6% | 99.9% | 0 | 98.8% | 99.1% | 1 |
| [0.01,0.05) | 76 | 873 | 82.4% | 94.7% | 0 | 59.7% | 66.9% | 9 |
| [0.05,0.10) | 39 | 529 | 72.2% | 89.2% | 3 | 49.5% | 57.0% | 9 |
| [0.10,0.15) | 22 | 253 | 57.3% | 74.7% | 2 | 31.2% | 38.2% | 7 |
| [0.15,0.25) | 37 | 396 | 52.8% | 68.1% | 1 | 29.3% | 35.1% | 9 |
| [0.25,0.50) | 41 | 615 | 37.6% | 53.2% | 3 | 17.9% | 22.7% | 11 |

Scatter (y = bin eligible fraction at guard 0, x = clip `infeasible_frac`; `.`=1 clip, `o`<4, `O`<10, `#`>=10):

```
1.00 |# o                                     |
0.94 |#Oo.                                    |
0.88 |#OoOO.                                  |
0.81 |OOO. o.. . .   .                        |
0.75 | oO..o o  . .. ...                      |
0.69 |..Oo.. o  ..oo.  .    .                 |
0.62 | ....  o....   o.  o .     .            |
0.56 |.ooo O.o ..    o  ..    o o.  .         |
0.50 | .        .           ..   .o.          |
0.44 |  .. .     o ..        o      .  .      |
0.38 |    .   ..o   ...    .        .         |
0.31 |   . . .   .  .  o .   .                |
0.25 |      .   ..           .                |
0.19 |       .         .  ..     ..           |
0.12 |                                        |
0.06 |   . ....     .  .   .   .              |
     +----------------------------------------+
     0.00                                0.60+
     bin eligible fraction (y) vs clip infeasible_frac (x)
```

### tier_mixed100

| infeasible_frac band | clips | bins | eligible % (g=0) | soft % (g=0) | clips 0 elig (g=0) | eligible % (g=1) | soft % (g=1) | clips 0 elig (g=1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| [0.00,0.01) | 53 | 704 | 93.9% | 98.7% | 0 | 86.4% | 89.5% | 1 |
| [0.01,0.05) | 12 | 195 | 76.4% | 89.3% | 1 | 51.8% | 59.2% | 3 |
| [0.05,0.10) | 10 | 101 | 54.5% | 72.8% | 0 | 31.7% | 38.2% | 5 |
| [0.10,0.15) | 8 | 114 | 51.8% | 64.8% | 1 | 33.3% | 37.8% | 3 |
| [0.15,0.25) | 10 | 116 | 39.7% | 51.7% | 3 | 22.4% | 28.8% | 6 |
| [0.25,0.50) | 7 | 70 | 22.9% | 43.9% | 4 | 8.6% | 10.0% | 5 |

Scatter (y = bin eligible fraction at guard 0, x = clip `infeasible_frac`; `.`=1 clip, `o`<4, `O`<10, `#`>=10):

```
1.00 |#                                       |
0.94 |o                                       |
0.88 |o. .                                    |
0.81 |o o                                     |
0.75 | .     ..                               |
0.69 |... .                                   |
0.62 | .          .   .                       |
0.56 |  ... . .    .                          |
0.50 |                                        |
0.44 |   o             .                      |
0.38 |    oo   .       .                      |
0.31 |       o  .    .   .                    |
0.25 |               .                        |
0.19 |            .                           |
0.12 |                                        |
0.06 |.        ..   . ....     .              |
     +----------------------------------------+
     0.00                                0.60+
     bin eligible fraction (y) vs clip infeasible_frac (x)
```

Per-clip CSVs: `reports/eligibility/scatter_tier_800.csv`, `reports/eligibility/scatter_tier_mixed100.csv`

## Unflagged-clip policy: `screen` (default) vs `assume-eligible`

The cheap alternative screens only clips flagged at the clip level and declares every
bin of the rest eligible. It is reconstructible with `--unflagged-policy assume-eligible`.
The cost of that shortcut, measured:

| set | guard s | clips assumed | assumed clips losing >=1 bin | losing every bin | bins wrongly eligible | % of bank | minutes |
|---|---:|---:|---:|---:|---:|---:|---:|
| `mixed100_assume_g0` | 0 | 75 | 31 | 1 | 135 | 10.38% | 2.2 |
| `tier800_assume_g0` | 0 | 701 | 140 | 3 | 335 | 3.52% | 5.4 |

Worst offenders (clips the clip-level threshold passes but the bin mask does not):

- `mixed100_assume_g0`:
  - `CMU_91_91_43_poses_120_jpos` infeasible_frac=0.011 -> 0/2 bins eligible
  - `BMLmovi_Subject_3_F_MoSh_Subject_3_F_20_poses_120_jpos` infeasible_frac=0.081 -> 1/3 bins eligible
  - `CMU_108_108_15_poses_120_jpos` infeasible_frac=0.074 -> 1/3 bins eligible
  - `CMU_75_75_11_poses_60_jpos` infeasible_frac=0.082 -> 1/3 bins eligible
  - `Eyes_Japan_Dataset_hamada_jump-12-boxer_step-hamada_poses_120_jpos` infeasible_frac=0.064 -> 11/30 bins eligible
- `tier800_assume_g0`:
  - `CMU_108_108_11_poses_120_jpos` infeasible_frac=0.098 -> 0/3 bins eligible
  - `CMU_108_108_20_poses_120_jpos` infeasible_frac=0.052 -> 0/3 bins eligible
  - `CMU_143_143_01_poses_60_jpos` infeasible_frac=0.084 -> 0/2 bins eligible
  - `BMLmovi_Subject_62_F_MoSh_Subject_62_F_3_poses_120_jpos` infeasible_frac=0.100 -> 1/5 bins eligible
  - `BMLmovi_Subject_15_F_MoSh_Subject_15_F_14_poses_120_jpos` infeasible_frac=0.077 -> 2/8 bins eligible

## Sanity check: clip #44

`BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos` (set `mixed100_g0`, guard 0 s, bin 50 frames): **PASS**

- severe windows: `[[0.72, 1.62], [8.06, 8.46]]` (expected `[[0.72, 1.62], [8.06, 8.46]]`)
- bins eligible: 7/10 (expected 7/10)
- `bin_eligible` = `[0, 0, 1, 1, 1, 1, 1, 1, 0, 1]`
- `bin_score`    = `[0.0, 0.38, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.6, 1.0]`
- clip-level `infeasible_frac` = 0.130261 (reconciles with the bank-wide screen)

## Caveats

- `severity=severe` = infeasible OR torque-infeasible. The published clip-level
  `infeasible_frac` scores an in-contact LP failure as 0; the mask does not inherit that
  hole, so `severe_frac >= infeasible_frac` and a clip can lose bins its clip-level number
  does not predict.
- `min_seg_s=1.0` drops feasible runs shorter than one second. On short clips (2-3 bins)
  this can zero out a clip whose `infeasible_frac` is tiny -- e.g. a 1.9 s clip cut by two
  brief severe windows has no 1 s feasible run at all. That is a deliberate episode-length
  policy, not a physics claim; rebuild with `--min-seg-s 0` to see the difference.
- `min_bin_frac=1.0` is strict: one severe frame disqualifies a bin. The soft mask
  `bin_score` is the unthresholded quantity; use it if you want a graded `m_b`.
- Guard band is framework-specific: mjlab observes only the current anchor (guard 0 s);
  SONIC observes 1.0 s of future reference, so it needs guard >= 1.0 s.
- All screens at the production contact gap 0.06 m. Mixing gaps invalidates the mask.
