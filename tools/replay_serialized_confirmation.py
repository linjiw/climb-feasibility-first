#!/usr/bin/env python3
"""Compare a complete frozen analysis in its serialized JSON representation."""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(root: Path, campaign: Path, binding_path: Path, binding_hash: str, out: Path) -> dict:
    if sha(binding_path) != binding_hash:
        raise ValueError('original efficiency binding changed')
    binding = json.loads(binding_path.read_text())
    for name, digest in binding['sources'].items():
        if sha(Path(name)) != digest:
            raise ValueError('bound source changed')
    if Path(binding['campaign']).resolve() != campaign.resolve():
        raise ValueError('campaign is not the original bound reentry')
    terminal = json.loads((campaign/'terminal_status.json').read_text())
    if terminal['status'] != 'completed' or len(terminal['completed_jobs']) != 60:
        raise ValueError('original campaign is incomplete')
    sys.path[:0] = [str(root/'tools'), str(root)]
    from analyze_relative_campaign import analyze
    manifest = campaign/'campaign_manifest.json'
    if json.loads(manifest.read_text())['contract'] != binding['contract']:
        raise ValueError('manifest contract link differs')
    reproduced = analyze(manifest)
    saved_path = campaign/'analysis.json'
    saved = json.loads(saved_path.read_text())
    # JSON represents Python tuples as arrays. Require exact semantic JSON,
    # including every numeric value, rather than weakening numeric tolerances.
    normalized = json.loads(json.dumps(reproduced, allow_nan=False))
    if normalized != saved:
        raise ValueError('serialized complete original analysis does not reproduce')
    differences = []
    def compare(first, second, path='$'):
        if type(first) != type(second):
            differences.append({'path':path,'recomputed_type':type(first).__name__,'saved_type':type(second).__name__})
        if isinstance(first, dict):
            for key in first: compare(first[key],second[key],path+'.'+str(key))
        elif isinstance(first,(tuple,list)):
            for index,(a,b) in enumerate(zip(first,second,strict=True)):compare(a,b,path+f'[{index}]')
    compare(reproduced,saved)
    from analyze_icra_efficiency import summarize
    efficiency = summarize(saved)
    out.mkdir(parents=True,exist_ok=False)
    result={'status':'complete_serialized_analysis_reproduced','checked_at':datetime.now().astimezone().isoformat(),
            'classification':'exact JSON replay; unchanged scientific analysis and thresholds',
            'representation_differences':differences,'analysis_sha256':sha(saved_path),
            'manifest_sha256':sha(manifest),'binding_sha256':binding_hash,
            'verifier_sha256':sha(Path(__file__)),'analysis':saved,'efficiency':efficiency}
    (out/'verification.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--campaign',type=Path,required=True)
    p.add_argument('--binding',type=Path,required=True)
    p.add_argument('--binding-sha256',required=True)
    p.add_argument('--out-dir',type=Path,required=True)
    a=p.parse_args();r=replay(a.root,a.campaign,a.binding,a.binding_sha256,a.out_dir)
    print(json.dumps({k:v for k,v in r.items() if k not in ('analysis','efficiency')}))
