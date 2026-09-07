## 2026-09-06 confirmation allocation and public research-story update

**Measured simulation training integrity and allocation:** at 22:17 EDT, ten of
12 confirmation training runs complete and independently replay over 410 saved
checkpoint states. All seeds 21/22 arms plus R23/D23 pass; U23 is running and A23
queued. No held-out endpoint has opened. Per-seed mean post-warm-up allocation TV:

| Arm | Seed 21 | Seed 22 | Seed 23 |
| --- | ---: | ---: | ---: |
| U | 0.0 | 0.0 | Pending |
| A | 0.029759170164293084 | 0.02933859420427059 | Pending |
| R | 0.08348494896009954 | 0.0824919974124211 | 0.08233284378057906 |
| D | 0.08391068947163956 | 0.08586509252074585 | 0.08398385293466296 |

Each complete run has 41 replayed states and zero invalid/censored events. The
TV mean uses 37 states from iteration 400 through 3999. Allocation histories are
correlated within runs and establish exposure contrast, not tracking improvement.
Public artifacts: `docs/assets/progress-2026-09-06/research_snapshot.json`,
`allocation_snapshots.csv` and `confirmation_allocation.png`/`.pdf` in that directory.
Original gate paths and SHA-256 identities are included in the JSON export.

**Measured development / pending outcomes:** the public development summary records
completed D31/D32 calibration, freeze prerequisites, H1 CPU evaluation/provenance
and CPU lifecycle checks. It does not establish full H1 benefit, forgetting recovery,
physical robustness or hardware transfer. Existing repair and E4 findings retain
separate exploratory/sealed labels. Scope, claim-to-evidence map, statistical
contract and next research decisions: `plan/PAGES_RESEARCH_STORY_2026-09-06.md`.

