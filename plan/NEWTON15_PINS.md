# Newton 1.5 recertification pins

**Recorded:** 2026-08-26 EDT  
**Status:** unsealed environment record; exact-unit recertification passed 2026-08-26
(`plan/NEWTON15_RECERT_RESULT.md`).  
**Environment:** `/data/robotixx/climb/newton15/.venv` (isolated; ignored by Git)

## Core physics stack

| component | exact pin | source |
|---|---:|---|
| Python | 3.13.9 | uv-managed CPython |
| Newton | 1.5.0 | PyPI wheel |
| Warp | 1.16.0 | PyPI wheel |
| MuJoCo | 3.11.0 | PyPI wheel |
| MuJoCo Warp | 3.11.0 | PyPI wheel |

The four modules import together and report the versions above. `uv pip check` reports that all
installed packages are compatible.

## Conformance-side pins

| component | exact pin / identity |
|---|---|
| mjlab | 1.6.0, editable source commit `0fb8a681136be94ffc636a3dd423cabb97d91f10` (clean nested worktree at capture) |
| PyTorch | 2.9.0+cu128 |
| G1 MJCF | `mjlab-1.6.0/src/mjlab/asset_zoo/robots/unitree_g1/xmls/g1.xml`, SHA-256 `febdcbeffbbf84051556ae41a5ac1b43fb479a5d76bdb3f54824dbc2721c20aa` |
| S1 harness baseline | `tools/s1_newton_conformance.py`, SHA-256 `c1a234f6e91eaf12bd944de7a767537dd9327618a09b4ea69d51f8885172435f` |
| DFRP v1 exact unit table | file SHA-256 `b91e6342049dea90410052e75ccbe5d450887c102ea90812a23d5204e7cd4c48`; embedded canonical payload SHA-256 `0df66390ceb6c9258c64c50bb4c31a9ee33d0412a3635d8dab72f0b789bdd2ff` |

The complete sorted `uv pip freeze` stream hashes to
`7757af167571d53a9f649c18bac5aca8a8e4648fc0c84f8d81ca1f4cd3a69fda`.
The venv's `pyvenv.cfg` hashes to
`993420c1d6639c5e18ae38e62ad88e49402710d9492b027203a2584d1c48a986`.

## Isolation check

Before and after creating and populating `newton15/.venv`, the existing trainer environment had:

- identical sorted-freeze SHA-256:
  `4ae272ca6fde454d5fb0dd282550977a7789b6e970611d955518bde9bd2bdcbd`;
- identical `mjlab-1.6.0/.venv/pyvenv.cfg` SHA-256:
  `5a91d2ffbab69150a8aad9fedce3a6a586ddb3aeb5b5eadddbd0d7534dd16d16`;
- unchanged `pyvenv.cfg` timestamp: `2026-08-15 02:12:40.650214311 -0400`.

Therefore the pinned `mjlab-1.6.0/.venv` was not modified by Phase N environment setup.

## Reproduction commands

```bash
uv venv --python 3.13 newton15/.venv
uv pip install --python newton15/.venv/bin/python \
  'newton[sim]==1.5.0' 'warp-lang==1.16.0' \
  'mujoco==3.11.0' 'mujoco-warp==3.11.0'
VIRTUAL_ENV=/data/robotixx/climb/newton15/.venv \
  uv sync --project mjlab-1.6.0 --active --extra cu128 --inexact
uv pip install --python newton15/.venv/bin/python 'warp-lang==1.16.0'
uv pip check --python newton15/.venv/bin/python
```

The final explicit Warp install is required because the mjlab 1.6.0 lock records Warp 1.14.0,
while Newton 1.5.0 requires Warp at least 1.16.0. mjlab itself accepts Warp 1.16.0.
