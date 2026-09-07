"""Verify a completed Pages build and exact public content bytes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[2]
COMMIT='99cb95ad9965956e5aaca36d99e5d32fc114cf8d'
BASE='https://linjiw.github.io/climb-feasibility-first/'
# Bounded polling; an unfinished build is not reported as a deployment pass.
for attempt in range(6):
    build=json.loads(subprocess.check_output(['gh','api','repos/linjiw/climb-feasibility-first/pages/builds/latest'],text=True))
    if build['commit']==COMMIT and build['status']=='built': break
    if build['status']=='errored': raise RuntimeError(build)
    if attempt==5: raise RuntimeError('Pages build is not yet complete')
    time.sleep(7)
files=['index.html','relative-progress.html','archive-2026-09-05.html','flagship.html','companion.html','segment-native.html','assets/research-story.css','assets/research-story.js','assets/research-update.css']
files += [str(p.relative_to(ROOT/'docs')) for p in (ROOT/'docs/assets/progress-2026-09-06').iterdir() if p.is_file()]
def check(name):
    expected=(ROOT/'docs'/name).read_bytes()
    req=Request(BASE+name+'?revision='+COMMIT[:8],headers={'Cache-Control':'no-cache'})
    with urlopen(req,timeout=30) as response:
        actual=response.read(); status=response.status
    result={'url':BASE+name,'http_status':status,'bytes':len(actual),'matches_local_bytes':actual==expected,'sha256':hashlib.sha256(actual).hexdigest()}
    if actual!=expected: raise ValueError('Public bytes differ: '+name)
    return result
with ThreadPoolExecutor(max_workers=5) as pool: checked=list(pool.map(check,files))
result={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'deployed_commit':COMMIT,'pages_build':build['status'],'files':checked}
(ROOT/'reports/pages_update_2026-09-06/deployment_verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'pages_build':build['status'],'deployed_commit':COMMIT,'exact_public_file_matches':len(checked)}))
