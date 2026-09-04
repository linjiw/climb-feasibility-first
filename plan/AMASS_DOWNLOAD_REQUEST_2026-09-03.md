# AMASS download request for Phase G

**Status:** exact collection scope derived from the 800-motion training table and 100-motion
evaluation manifest on 2026-09-03. This is an acquisition note, not a new dataset or result.

## Preferred route: recover the retargeted artifact

The fastest route to an exact hash match is a backup of either:

1. `/data/robotixx/climb/bank/amass` — the finished, ground-aligned G1 NPZ bank; or
2. `/data/robotixx/wbt/train_converted_complete` — the historical Unitree-style G1 CSV retargets.

Raw AMASS downloads are upstream human-body motions. The local
`HybridRobotics/whole_body_tracking` checkout begins from **already retargeted G1 CSVs** and
converts them to maximum-coordinate NPZ files; it does not include an AMASS-to-G1 retargeter.
Therefore raw AMASS is a useful recovery input but cannot, by itself, guarantee the committed
Phase-G file hashes.

## Minimal raw AMASS fallback

On the authenticated AMASS Downloads page, choose **SMPL+H, gendered (`G`)** for each collection
below. Do not mix in SMPL+H neutral or SMPL-X variants. If a listed collection does not offer
SMPL+H G, stop and record which alternatives the page offers rather than substituting silently.

| AMASS collection | Training files | Evaluation files | Required unique files |
| --- | ---: | ---: | ---: |
| ACCAD | 10 | 0 | 10 |
| BMLhandball | 21 | 3 | 24 |
| BMLmovi | 92 | 2 | 94 |
| CMU | 145 | 12 | 157 |
| DFaust | 8 | 0 | 8 |
| EyesJapanDataset | 51 | 13 | 64 |
| GRAB | 111 | 19 | 130 |
| HUMAN4D | 11 | 0 | 11 |
| HumanEva | 3 | 1 | 4 |
| KIT | 334 | 47 | 381 |
| SFU | 2 | 0 | 2 |
| SSM / SSM_synced | 2 | 0 | 2 |
| TCDHands / TCD_handMocap | 5 | 3 | 8 |
| Transitions / Transitions_mocap | 5 | 0 | 5 |
| **Total** | **800** | **100** | **900** |

Also save `amass.bib`, the AMASS license, and the per-collection citation/license files supplied
by the site. Keep the archives outside the Git repository, for example:

```text
/home/linjiw/amass-licensed/raw/
```

Do not download these for the immediate Phase-G run: BMLrub, CNRS, DanceDB, EKUT, HDM05,
MoSh/MPI_mosh, PosePrior/MPI_Limits, SOMA, TotalCapture, WEIZMANN, MOYO, or LARa.

## After download

Before extraction or conversion:

1. inventory archive names, byte sizes, and any publisher checksums;
2. preserve the archives read-only as the licensed source layer;
3. derive the exact 900 source-motion paths from the committed Phase-G names;
4. locate or reconstruct the missing AMASS-to-G1 retarget stage in a versioned environment;
5. convert with the recorded mixed source frame rates and ground alignment; and
6. accept the rebuilt bank only if `tools/restore_phase_g_bank.py --scope full` verifies all
   900 committed SHA-256 identities.

If the hashes do not match, do not overwrite the current manifests. The scientifically valid
fallback is a newly versioned, unsealed substrate with renewed screens, unit table, evaluation
panel, and calibration—not a silent replacement.
