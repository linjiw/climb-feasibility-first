"""Update the research detail page without altering historical measurements."""
from datetime import datetime
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DOCS=ROOT/'docs'
data=json.loads((DOCS/'assets/progress-2026-09-06/research_snapshot.json').read_text())
p=DOCS/'relative-progress.html'; h=p.read_text()
h=h.replace('assets/research-update.css','assets/research-story.css')
h=h.replace('two replicated relative-progress allocation runs, a calibrated failure baseline, and the fixed four-arm experiment for held-out humanoid tracking.','ten verified confirmation training runs, per-seed allocation histories, and the frozen held-out humanoid tracking experiment.')
h=h.replace('Relative progress: evidence and next experiment · CLIMB','Relative progress: confirmation evidence and protocol · CLIMB')
h=h.replace('Next experiment</a>','Confirmation protocol</a>')
h=h.replace('Research update · 5 September 2026','Confirmation update · 6 September 2026')
h=h.replace('A curriculum that keeps changing what the robot practices.','Changed exposure. Tracking benefit still to test.')
h=h.replace('Relative-progress sampling sustains allocation contrast in two full training runs. <b>The next test is whether that changes held-out tracking quality.</b>','All three relative-progress confirmation seeds pass the allocation gate. <b>The fixed four-arm campaign will test whether that exposure improves held-out tracking.</b>')
h=h.replace('<div class="v">2 / 2</div><div class="k">relative-progress development runs pass the allocation gate</div>','<div class="v">10 / 12</div><div class="k">confirmation training runs complete and independently verified</div>')
h=h.replace('<div class="v">0.0832 · 0.0827</div><div class="k">mean post-warm-up TV from the deployment prior</div>','<div class="v">410</div><div class="k">saved checkpoint states replayed across completed runs</div>')
a=h.index('<section id="status">'); b=h.index('<section id="evidence">',a)
h=h[:a]+'''<section id="status"><span class="numeral">Current checkpoint</span><h2>The intervention is measurable; the policy comparison remains unopened.</h2>
<p>All U/A/R/D runs for seeds 21 and 22, plus R23 and D23, have completed 4,000 iterations and passed their declared training gates. Every saved sampler state replays exactly, with zero recorded invalid-start, invalid-reference or censored-reset events. A is retained under its frozen comparator rule even when allocation contrast is weak.</p>
<div class="callout"><p><strong>Static snapshot · 6 September 2026, 22:17 EDT.</strong> U23 is running, with checkpoint 1100 saved; A23 is queued. The scheduler and follow-on workers remain active. No held-out evaluation cell has started. Both D calibration seeds and all four seed-51 confirmation-entrypoint smokes passed before the immutable freeze. The original overnight attempt timed out waiting for GPU capacity before any scientific job; its record is preserved. The active operational re-entry uses the same scientific contract and schedule.</p></div>
<p><a href="index.html#roadmap">Read how this experiment fits the wider research plan →</a></p></section>
''' + h[b:]
a=h.index('<section id="evidence">')+len('<section id="evidence">')
rows=''
for arm in ('U','A','R','D'):
 for seed in (21,22,23):
  matches=[r for r in data['completed_runs'] if r['arm']==arm and r['seed']==seed]
  if matches:
   r=matches[0]
   rows+=f'<tr><th scope="row">{arm} · seed {seed}</th><td>{r["mean_tv"]:.9f}</td><td>{r["completed_trials"]:,}</td><td>Training gate pass</td></tr>\n'
new='''
<span class="numeral">01 · Current confirmation measurements</span><h2>Relative progress and conditional failure sustain allocation contrast.</h2>
<p>Each completed run below has 512 environments, 4,000 PPO iterations and 41 verified saved states. Mean TV averages the 37 saved states at iterations 400–3999. Incomplete U23/A23 runs are excluded from the measured table and figure; no value is imputed.</p>
<div class="scroll" role="region" aria-label="Verified confirmation training results" tabindex="0"><table><caption>Measured training allocation · no policy-utility inference</caption><thead><tr><th scope="col">Arm and seed</th><th scope="col">Mean TV</th><th scope="col">Completed trials</th><th scope="col">Decision</th></tr></thead><tbody>'''+rows+'''</tbody></table></div>
<figure><a href="assets/progress-2026-09-06/confirmation_allocation.png"><img src="assets/progress-2026-09-06/confirmation_allocation.png" width="2376" height="738" alt="Allocation TV histories by training seed. Relative-progress R and conditional-failure D sustain higher exposure contrast than absolute-progress A; U remains at the prior. Seed 23 currently includes only completed R and D runs."></a><figcaption><strong>All 410 verified confirmation snapshots.</strong> Lines show within-run histories, not independent replications or tracking learning curves. The dashed 0.05 line is a mean-TV gate for R/D, not a per-checkpoint requirement and not A's gate. Similar mean TV does not make R and D identical treatments. <a href="assets/progress-2026-09-06/allocation_snapshots.csv">CSV data</a> · <a href="assets/progress-2026-09-06/confirmation_allocation.pdf">PDF figure</a> · <a href="assets/progress-2026-09-06/research_snapshot.json">Verified summary and source hashes</a>.</figcaption></figure>
<h3 class="tight">Interpretation before policy outcomes</h3><p>R passes in all three confirmation seeds (mean TV 0.083485, 0.082492, 0.082333); D also passes in all three. A's completed runs remain near 0.029–0.030. This reproduces the exposure distinction that motivated relative normalization. It does not show that R selects learnable motions better than D or that either improves tracking.</p>
'''
h=h[:a]+new+h[a:]
h=h.replace('01 · What changed','Development evidence · before confirmation')
h=h.replace('<tr><th scope="row">Failure D · seed 31</th><td>0.084955</td><td>625.06</td><td>1,113,773</td><td>Calibration pass</td></tr>','<tr><th scope="row">Failure D · seed 31</th><td>0.084955</td><td>625.06</td><td>1,113,773</td><td>Calibration pass</td></tr>\n      <tr><th scope="row">Failure D · seed 32</th><td>0.085939</td><td>624.29</td><td>1,118,388</td><td>Calibration pass</td></tr>')
h=h.replace('positive lower seed-level 95% t-confidence bound','positive lower two-sided seed-level 95% t-confidence bound (df = 2)')
a=h.index('  <div class="grid">',h.index('<section id="experiment">'));b=h.index('  <p><strong>Precision',a)
h=h[:a]+'''  <div class="grid">
<article class="card"><h3>Complete: calibrate and freeze</h3><p>D31/D32 and all four seed-51 confirmation-entrypoint smokes passed. Source bindings, replay logs and all 12 configuration hashes were verified before sealing the current contract. Scientific settings remain fixed.</p></article>
<article class="card"><h3>Running: finish all training</h3><p>Ten training gates pass at this snapshot. U23 is running, followed by A23. The scheduler opens policy evaluation only after all twelve gates pass; a failure retains its declared disposition.</p></article>
<article class="card"><h3>Next: measure policy utility</h3><p>Run the 48 evaluation cells and validate all training, pairing and provenance records before aggregation. The queued efficiency postprocessor requires exact reproduction of the original complete analysis.</p></article>
</div>
''' + h[b:]
h=h.replace('The implementation now includes checkpoint-linked sampler telemetry, complete history replay, paired-evaluation provenance checks, a strict campaign analyzer, and the finalization command. Four short seed-41 simulator smokes passed. The successful synthetic freeze test establishes software behavior; actual seed-51 smokes and the policy experiment remain pending.','The implementation includes checkpoint-linked sampler telemetry, complete history replay, paired-evaluation provenance checks and a strict campaign analyzer. All four actual seed-51 smokes passed before the contract freeze. Sample-efficiency analysis, the frozen-policy pilot and CUDA lifecycle checks are queued with separate prerequisites; these queued stages are not completed evidence.')
h=h.replace('The live partial run is excluded from the completed-run comparison.','Incomplete training runs are excluded from the completed-run comparison. No held-out policy outcomes were read by the public exporter.')
h=h.replace('<li><a href="assets/relative-progress/research_snapshot.json">Research snapshot (JSON)</a>: completed-run metrics, E4 disposition, repair result, pending prerequisites, and source identities.</li>','<li><a href="assets/progress-2026-09-06/research_snapshot.json">6 September confirmation snapshot (JSON)</a>: ten completed runs, incomplete arms, 410 verified states and source hashes; <a href="assets/progress-2026-09-06/allocation_snapshots.csv">all confirmation snapshots (CSV)</a>.</li>\n    <li><a href="assets/relative-progress/research_snapshot.json">5 September historical snapshot (JSON)</a>: development metrics, E4 disposition, repair result, and prerequisite status at that earlier date.</li>')
h=h.replace('all saved R11, R12 and D31 allocation snapshots.','all saved R11, R12 and D31 allocation snapshots; the historical figure predates D32 completion.')
p.write_text(h)
# Keep older pages discoverable while making their date and scope unambiguous.
for name in ('archive-2026-09-05.html','flagship.html','companion.html','segment-native.html'):
 p=DOCS/name; html=p.read_text()
 banner='<div role="note" style="padding:1rem;background:#fff0cf;color:#43351a;font:15px/1.5 system-ui,sans-serif"><strong>Historical research record.</strong> This page preserves an earlier study or working draft; its status statements are dated. <a style="color:#174c5c" href="index.html">Read the latest findings and research plan</a> · <a style="color:#174c5c" href="relative-progress.html">Current confirmation progress</a>.</div>'
 if '<body>' in html: html=html.replace('<body>','<body>\n'+banner,1)
 else:
  # The original project archive is a legacy document without explicit body tags.
  pos=html.index('<header'); html=html[:pos]+banner+html[pos:]
 p.write_text(html)
