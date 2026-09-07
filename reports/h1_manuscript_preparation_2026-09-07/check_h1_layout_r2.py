"""SYNTHETIC layout check in an isolated paper copy; no measured H1 outcomes."""
from pathlib import Path
from unittest.mock import patch
import json
import shutil
import sys
import subprocess

import numpy as np
from scipy.stats import t

ROOT = Path('/home/linjiw/climb-feasibility-first')
sys.path.insert(0, str(ROOT / 'paper/icra'))
import report_h1
import integrate_h1

out = ROOT / 'reports/h1_manuscript_preparation_2026-09-07/synthetic_layout_r2'
out.mkdir(exist_ok=False)
mirror = out / 'workspace'
shutil.copytree(ROOT / 'paper/icra', mirror / 'paper/icra', ignore=shutil.ignore_patterns('build', '__pycache__'))
shutil.copytree(ROOT / 'paper/figures', mirror / 'paper/figures')
report = out / 'SYNTHETIC_REPORT'
seeds = report_h1.SEEDS
shifts = np.array([-.01, .01, .02, -.02, 0.])
mean = float(shifts.mean()); half = float(t.ppf(.975, 4)*shifts.std(ddof=1)/np.sqrt(5))
panel = {'paired_seed_deltas':dict(zip(map(str,seeds),shifts.tolist())), 'mean':mean,
         'seed_t_95ci':[mean-half,mean+half], 'independent_units':5, 'df':4}
training={}
for seed in seeds:
 for arm in ('on','off'):
  training[f'{arm}_s{seed}']={'completed_trials':100,'mechanism':[
   {'iteration':i,'positive_excess_total':.1,'positive_excess_rejected':.04 if arm=='off' else 0.,
    'top1_rejected':False,'top1_unit':{'clip':'SYNTHETIC','unit_id':0}}
   for i in [*range(1000,4000,100),3999]],
   'final_allocation':{'uncapped_prior_rejected_mass':.115 if arm=='off' else 0.,
                       'post_cap_rejected_mass':.16 if arm=='off' else 0.,
                       'rejected_completed_trials':16 if arm=='off' else 0}}
result={'schema_version':'h1_fable_result/2','evaluated_cells':40,'episode_rows':112000,
        'status':'inconclusive','classification':'SYNTHETIC layout only; no measured H1 result',
        'contract':{'sha256':report_h1.CONTRACT_SHA256},'primary_on_minus_off':panel,
        'all_panel_on_minus_off':panel,'reference_effect':.02,'all_panel_pass_fail_guard':None,
        'training_transitions_per_policy':49152000,'limitations':['SYNTHETIC ONLY'],
        'training':training,'hard_indices':list(range(25)),
        'clip_scores':{str(i):{'on':(np.full((5,100),.5)+shifts[:,None]).tolist(),
                              'off':np.full((5,100),.5).tolist()} for i in report_h1.ITERATIONS}}
report_h1.export(result,report)
proof=out/'SYNTHETIC_PROOF.txt';proof.write_text('SYNTHETIC layout fixture, not an experiment authorization\n')
binding=report_h1.record(proof)
verification={'status':'exact_H1_replay_pass','contract':result['contract'],
              **{name:binding for name in ('terminal','analysis','reporter','analyzer')}}
(report/'verification.json').write_text(json.dumps(verification))
with patch.object(integrate_h1,'ROOT',mirror), patch.object(integrate_h1,'terminal_input',return_value=({},result)):
 integrate_h1.integrate(report)
p=mirror/'paper/icra/root.tex';text=p.read_text();text=text.replace('\\thispagestyle{empty}','\\thispagestyle{plain}').replace('\\pagestyle{empty}','\\pagestyle{plain}')
footer=r'''\makeatletter
\def\ps@plain{\def\@oddhead{}\def\@evenhead{}\def\@oddfoot{\hfil\small SYNTHETIC H1 LAYOUT TEST --- NO MEASURED H1 RESULT\hfil}\let\@evenfoot\@oddfoot}
\makeatother
'''
text=text.replace('\\begin{document}',footer+'\\begin{document}');p.write_text(text)
with (out/'build.log').open('w') as log:
 run=subprocess.run([str(mirror/'paper/icra/build.sh')],cwd=mirror,stdout=log,stderr=subprocess.STDOUT)
info=subprocess.check_output(['pdfinfo',str(mirror/'paper/icra/build/root.pdf')],text=True) if (mirror/'paper/icra/build/root.pdf').exists() else ''
(out/'result.json').write_text(json.dumps({'classification':'SYNTHETIC isolated layout check; no H1 policy outcome','build_returncode':run.returncode,'pdfinfo':info},indent=2)+'\n')
print('synthetic build',run.returncode);print('\n'.join(line for line in info.splitlines() if line.startswith(('Pages:','Page size:'))))
raise SystemExit(run.returncode)
