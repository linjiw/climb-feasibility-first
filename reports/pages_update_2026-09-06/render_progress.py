"""Render the dated public snapshot and standalone allocation figure."""
import csv
from datetime import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / 'docs'
ASSETS = DOCS / 'assets/progress-2026-09-06'
data = json.loads((ASSETS / 'research_snapshot.json').read_text())
assert data['endpoint_access_exists'] is False
complete = {(r['arm'], r['seed']):r for r in data['completed_runs']}
pending = {(r['arm'], r['seed']):r for r in data['pending_training']}
labels = {'U':'Uniform prior', 'A':'Absolute progress', 'R':'Relative progress', 'D':'Conditional failure'}
rows=[]
for arm in ('U','A','R','D'):
    cells=[]
    for seed in (21,22,23):
        if (arm,seed) in complete:
            cells.append('<td class="done">Complete · pass</td>')
        elif pending[(arm,seed)]['latest_saved_iteration'] is not None:
            cells.append('<td class="active">Running</td>')
        else:
            cells.append('<td class="waiting">Queued</td>')
    rows.append(f'<tr><th scope="row">{arm} · {labels[arm]}</th>'+''.join(cells)+'</tr>')
active = [f"{r['arm']}{r['seed']} is running (latest saved checkpoint {r['latest_saved_iteration']:,});" for r in pending.values() if r['latest_saved_iteration'] is not None]
queued = [f"{r['arm']}{r['seed']}" for r in pending.values() if r['latest_saved_iteration'] is None]
running = ' '.join(active) + (' '+', '.join(queued)+' remains queued.' if queued else '')
replacements={'@COMPLETE@':str(data['training_jobs_complete']), '@ISO@':data['snapshot_time'], '@TIME@':datetime.fromisoformat(data['snapshot_time']).strftime('%H:%M'), '@RUNNING@':running,'@STATUS_ROWS@':''.join(rows), '@STATES@':str(data['verified_checkpoint_states'])}
p=DOCS/'index.html'
html=p.read_text()
for before,after in replacements.items(): html=html.replace(before,after)
p.write_text(html)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
with (ASSETS/'allocation_snapshots.csv').open() as handle: states=list(csv.DictReader(handle))
colors={'U':'#546878','A':'#bd7a27','R':'#087e8b','D':'#7654a2'}
styles={21:'-',22:'--',23:':'}
fig, axes=plt.subplots(1,3,figsize=(13.2,4.1),sharey=True,constrained_layout=True)
for ax,seed in zip(axes,(21,22,23)):
    for arm in ('U','A','R','D'):
        subset=[r for r in states if r['arm']==arm and int(r['seed'])==seed]
        if subset: ax.plot([int(r['iteration']) for r in subset],[float(r['tv']) for r in subset],color=colors[arm],linewidth=1.9,label=arm)
    ax.axhline(.05,color='#828b8e',linestyle='--',linewidth=.9)
    ax.set_title(f'Seed {seed}'+(' · U / A incomplete' if seed==23 else ''),fontsize=12,loc='left')
    ax.set(xlim=(0,4000),ylim=(-.003,.155),xlabel='PPO iteration',xticks=(0,1000,2000,3000,4000))
    ax.tick_params(labelsize=9); ax.grid(axis='y',alpha=.16)
    ax.spines[['top','right']].set_visible(False)
axes[0].set_ylabel('Allocation TV from deployment prior')
handles=[Line2D([0],[0],color=colors[a],lw=2,label=f'{a} · {labels[a]}') for a in colors]
fig.legend(handles=handles,loc='outside lower center',ncol=4,frameon=False,fontsize=10)
fig.suptitle('Changed training exposure · policy benefit remains untested',fontsize=15,fontweight='bold',x=.01,ha='left')
fig.savefig(ASSETS/'confirmation_allocation.png',dpi=180,facecolor='white')
fig.savefig(ASSETS/'confirmation_allocation.pdf',facecolor='white')
plt.close(fig)
print('Rendered',data['training_jobs_complete'],'runs and',len(states),'states')
