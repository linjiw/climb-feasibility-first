"""Execute one explicit development correction; preserve failed prior attempts."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
WORK=Path('/home/linjiw/climb-icra-evidence-2026-09-06')
OUT=WORK/'reports/device_lifecycle_optional_sense_2026-09-06'
PARENT=WORK/'reports/device_lifecycle_gpu_2026-09-06/design.json'
PYTHON=ROOT/'mjlab-1.6.0/.venv/bin/python'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
campaign=ROOT/'reports/relative_progress_2026-09-05/confirmation_freeze/campaign_gpu_reentry_2026-09-06'
pilot=Path('/home/linjiw/climb-signal-quality-2026-09-06/reports/frozen_progress_pilot_2026-09-06/queue_gpu_reentry_2026-09-06/terminal_status.json')
assert json.loads((campaign/'terminal_status.json').read_text())['status']=='completed'
assert json.loads(pilot.read_text())['status']=='development_pilot_completed'
assert sha(PARENT)=='6d445e068966dae661e10679d4e9d44ffac8a6e0321351f22e1df7ed6ed40b46'
design=json.loads(PARENT.read_text())
OUT.mkdir(exist_ok=False)
design.update(graph_protocol='optional_sensor_context/1',parent_design={'path':str(PARENT),'sha256':sha(PARENT)},classification='development assertion correction; unchanged physical conditions and policy; prior failed run preserved')
wrapper=WORK/'tools/device_optional_sense.py';design['bindings'][str(wrapper)]=sha(wrapper)
path=OUT/'design.json';path.write_text(json.dumps(design,indent=2)+'\n')
completed=[]
try:
 for condition in design['conditions']:
  free,util=map(int,subprocess.check_output(['nvidia-smi','--query-gpu=memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True).strip().split(','))
  if free<14000 or util>60:raise RuntimeError(f'GPU gate unavailable: {free} MiB, {util}%')
  cmd=[str(PYTHON),str(wrapper),'--design',str(path),'--design-sha256',sha(path),'--condition',condition,'--out-dir',str(OUT/condition)]
  (OUT/f'{condition}_launch.json').write_text(json.dumps({'argv':cmd,'started':datetime.now().astimezone().isoformat(),'gpu_free_mib':free,'gpu_utilization':util},indent=2)+'\n')
  with (OUT/f'{condition}.log').open('x') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
  completed.append(condition);print(condition,'completed',flush=True)
 sys.path.insert(0,str(WORK/'tools'))
 import analyze_device_lifecycle as analyzer
 from device_optional_sense import verify_graphs
 analyzer.verify_graphs=verify_graphs
 result=analyzer.analyze(OUT)
 (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
 terminal={'status':result['status'],'completed_cells':completed,'full_evaluation_enabled':False}
except Exception as exc:
 terminal={'status':'execution_stopped','reason':str(exc),'completed_cells':completed,'automatic_retries':0,'full_evaluation_enabled':False}
(OUT/'terminal_status.json').write_text(json.dumps(terminal,indent=2)+'\n');print(json.dumps(terminal))
