"""Publish bounded development summaries with source identities, excluding payloads."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/assets/progress-2026-09-06/development_evidence.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def record(p):
 p=p.resolve()
 return {'workspace':p.parts[3], 'artifact':'/'.join(p.parts[4:]),'sha256':sha(p)}
def bound(p,key):
 outer=json.loads(p.read_text()); link=outer[key]; q=Path(link['path']);assert sha(q)==link['sha256'];return q,json.loads(q.read_text())
f=ROOT/'reports/relative_progress_2026-09-05/confirmation_freeze/freeze_result.json'
fr=json.loads(f.read_text());assert fr['all_prerequisites_reproduced'] and fr['configuration_digests_verified']==12
c=ROOT/'reports/research_next_2026-09-06/calibration_verification.json';cal=json.loads(c.read_text());assert cal['both_decisions_reproduced']
h,h1=bound(ROOT/'reports/gate_evaluator_development_2026-09-06/verification.json','measured_verification')
n,natural=bound(ROOT/'reports/natural_lifecycle_2026-09-06/verification.json','measured_verification')
d,device=bound(ROOT/'reports/device_lifecycle_queue_2026-09-06/verification.json','cpu_verification')
p=ROOT/'reports/h1_provenance_preparation_2026-09-06/verification.json';prov=json.loads(p.read_text())
for path,digest in prov['artifacts'].items():assert sha(Path(path))==digest
fields=('status','classification','episode_rows','partial_reset_events','entity_reset_events','motion_resample_events','natural_failure_rows','early_success_rows','previous_csvs_exact_match','original_unchanged_csv_exact_match','policy_immutability_pass','confirmation_endpoints_opened','full_evaluation_enabled')
out={'classification':'development instrumentation only; no H1 benefit, robustness or transfer conclusion',
 'phase_a':{'status':fr['status'],'all_prerequisites_reproduced':True,'configuration_digests_verified':12,'source':record(f)},
 'D_calibration':{'results':cal['seeds'],'source':record(c)},
 'H1_CPU_evaluation':{'summary':{k:h1[k] for k in fields if k in h1},'source':record(h)},
 'H1_cell_provenance':{'status':prov['status'],'tests_passed':prov['tests_passed'],'production_manifest_ingestion_enabled':False,'full_training_enabled':False,'source':record(p)},
 'natural_CPU_lifecycle':{'summary':{k:natural[k] for k in fields if k in natural},'source':record(n)},
 'device_entrypoint_CPU':{'summary':{k:device[k] for k in fields if k in device},'source':record(d)},
 'pending':['Confirmation held-out policy results','Frozen-policy independent stationarity study','Full H1 gate-on/off comparison','Nine-cell CUDA lifecycle validation','Full S1 physical-sensitivity study','Hardware/HIL motion tracking']}
OUT.write_text(json.dumps(out,indent=2)+'\n')
print('Exported development evidence from hash-verified source records')
