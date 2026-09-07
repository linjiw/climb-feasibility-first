"""Render manuscript-only figures with embedded TrueType fonts."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'paper/icra/figures'
OUT.mkdir(exist_ok=True)
fig, ax = plt.subplots(figsize=(10.6, 2.05))
ax.set(xlim=(0, 1), ylim=(0, 1))
ax.axis('off')
labels = [
    ('Screen references', 'Declared robot + scene\nContact and torque capacity'),
    ('Enforce exact support', '1,184 units / 368,951 starts\nFull temporal-access contract'),
    ('Allocate practice', 'U / A / R / D\nSame learner and budget'),
    ('Evaluate the policy', 'Unchanged held-out references\nRegistered result: inconclusive'),
]
for index, (title, body) in enumerate(labels):
    x = .012 + index * .25
    box = FancyBboxPatch((x, .34), .225, .50, boxstyle='round,pad=0.005',
                         edgecolor='#37616c', facecolor='#edf4f5', linewidth=1)
    ax.add_patch(box)
    ax.text(x + .1125, .68, title, ha='center', va='center', fontsize=10, weight='bold')
    ax.text(x + .1125, .49, body, ha='center', va='center', fontsize=8.2, linespacing=1.45)
    if index < 3:
        ax.annotate('', xy=(x + .244, .60), xytext=(x + .231, .60),
                    arrowprops=dict(arrowstyle='->', color='#37616c'))
ax.text(.125, .14, 'Repair is a separate\ntarget-changing route', ha='center', fontsize=8)
ax.text(.62, .14, 'Outcome feedback changes allocation.\nA control benefit must be measured independently.',
        ha='center', fontsize=8)
fig.savefig(OUT / 'f1_evidence_interface.pdf', bbox_inches='tight')
fig.savefig(OUT / 'f1_evidence_interface.png', dpi=180, bbox_inches='tight')
plt.close(fig)

# Keep the original measured figure generator and artifacts unchanged. Only the
# manuscript output destination and PDF font embedding are adapted here.
source = ROOT / 'reports/relative_confirmation_results_2026-09-06/plot_results.py'
code = source.read_text().replace('OUT=Path(__file__).resolve().parent',
                                "OUT=ROOT/'paper/icra/figures'")
exec(compile(code, str(source), 'exec'), {'__file__': str(source), '__name__': '__main__'})
