"""Plot the independently reproduced frozen result without changing its decision."""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
source=ROOT/'reports/continuous_execution_preparation_2026-09-06/serialized_confirmation_replay/verification.json'
verified=json.loads(source.read_text());assert verified['status']=='complete_serialized_analysis_reproduced'
a=verified['analysis'];seeds=[21,22,23];iterations=[1000,2000,3000,3999]
transitions=np.array([(i+1)*512*24/1e6 for i in iterations])
colors={'U':'#546878','A':'#bd7a27','R':'#087e8b','D':'#7654a2'}
fig,axes=plt.subplots(1,3,figsize=(12.6,4.3),constrained_layout=True)
for ax,key,title in zip(axes[:2],('primary_R_minus_U','all_panel_nonregression'),('Final feasible-hard R − U','Final all-panel R − U')):
 r=a[key];d=[r['paired_seed_deltas'][str(s)] for s in seeds]
 ax.axhline(0,color='#666',lw=.8)
 ax.axhline(.02 if key.startswith('primary') else -.01,color='#b57627',ls='--',lw=1)
 ax.scatter(range(3),d,color=['#546878','#546878','#087e8b'],s=42,zorder=4)
 lower,upper=r['seed_t_95ci'];ax.errorbar(3.2,r['mean'],yerr=[[r['mean']-lower],[upper-r['mean']]],fmt='D',capsize=5,color='#202a32',ms=6)
 ax.set(xticks=[0,1,2,3.2],xticklabels=['21','22','23','Mean + CI'],ylim=(-.13,.12),title=title,ylabel='TrackingScore difference')
 ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15)
for arm in colors:
 values=np.array([a['learning_curves_descriptive'][str(i)][arm]['feasible_hard_per_seed'] for i in iterations])
 for j in range(3):axes[2].plot(transitions,values[:,j],color=colors[arm],alpha=.2,lw=.7)
 axes[2].plot(transitions,values.mean(axis=1),'-o',color=colors[arm],label=arm,ms=4,lw=1.8)
axes[2].set(xlabel='Simulator transitions (millions)',ylabel='Feasible-hard TrackingScore',title='Learning curves · exploratory',xticks=transitions,xticklabels=['12.30','24.59','36.88','49.15'])
axes[2].legend(ncol=4,frameon=False,loc='lower left');axes[2].spines[['top','right']].set_visible(False)
fig.suptitle('Frozen confirmation: inconclusive · no registered benefit established',fontsize=14,fontweight='bold',x=.01,ha='left')
fig.savefig(OUT/'paired_results_and_learning_curves.png',dpi=190,facecolor='white')
fig.savefig(OUT/'paired_results_and_learning_curves.pdf',facecolor='white');plt.close(fig)
with (OUT/'learning_curves.csv').open('w',newline='') as handle:
 writer=csv.DictWriter(handle,fieldnames=['iteration','transitions','arm','seed','feasible_hard','all_panel'],lineterminator='\n');writer.writeheader()
 for i in iterations:
  for arm in colors:
   for j,seed in enumerate(seeds):
    r=a['learning_curves_descriptive'][str(i)][arm];writer.writerow({'iteration':i,'transitions':(i+1)*512*24,'arm':arm,'seed':seed,'feasible_hard':r['feasible_hard_per_seed'][j],'all_panel':r['all_panel_per_seed'][j]})
summary={k:a[k] for k in ('status','primary_R_minus_U','all_panel_nonregression','secondary_descriptive','AULC_R_minus_U_descriptive','analysis')}
summary.update(classification='measured frozen simulation result; all secondary analyses descriptive',source_analysis_sha256=verified['analysis_sha256'],replay_verification_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),training_runs=12,evaluation_cells=48,evaluation_rows=48*2800,conditions_per_cell=2800)
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(OUT/'efficiency_descriptive.json').write_text(json.dumps(verified['efficiency'],indent=2)+'\n')
print(json.dumps({'status':a['status'],'primary_mean':a['primary_R_minus_U']['mean'],'aulc_mean':a['AULC_R_minus_U_descriptive']['mean']}))
