"""Publish the complete outcome while retaining explicitly dated prior exports."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / 'reports/relative_confirmation_results_2026-09-06'
target = ROOT / 'docs/assets/confirmation-2026-09-06'
for name in ('summary.json', 'learning_curves.csv', 'efficiency_descriptive.json',
             'paired_results_and_learning_curves.png', 'paired_results_and_learning_curves.pdf'):
    shutil.copyfile(source / name, target / name)

p = ROOT / 'docs/index.html'
s = p.read_text()


def replace(old: str, new: str) -> None:
    global s
    assert old in s, old[:90]
    s = s.replace(old, new)


replace('<a href="#findings">Findings</a>', '<a href="#results">Results</a>')
replace('A difficult motion can expose a bad reference, missing experience, or a skill the robot has yet to learn. CLIMB studies how to separate these causes and allocate training to useful practice.', 'Given a fixed training budget, how should a humanoid practice model-admissible motion segments so that additional experience becomes transferable tracking skill?')
replace('href="#findings">Read the findings', 'href="#results">Read the completed result')
replace('<div class="v">10 / 12</div>', '<div class="v">12 / 12</div>')
replace('<div class="v">0 / 48</div><div class="k">held-out evaluation cells started at this snapshot', '<div class="v">48 / 48</div><div class="k">held-out evaluation cells complete and verified')
replace('<div class="v">Pending</div><div class="k">tracking benefit, sample-efficiency gains and hardware transfer', '<div class="v">Inconclusive</div><div class="k">frozen policy result; registered benefit not established')
start = s.index('<div class="snapshot">')
end = s.index('<main id="main"', start)
s = s[:start] + '''<div class="snapshot"><div class="wrap"><p><strong>Complete evidence · <time datetime="2026-09-06T23:47:19-04:00">23:47 EDT, 6 September 2026</time>.</strong> All training and held-out evaluation finished. The complete analysis reproduces exactly. This dated result supersedes the 22:17 pending snapshot; hardware transfer remains unconfirmed.</p></div></div>
''' + s[end:]
replace('Our current hypothesis is that <strong>relative progress over exact admissible support</strong> can direct practice toward learnable skills while keeping broad exposure. The four-arm confirmation tests the resulting policy, using the same learner, motion support and training budget.', 'CLIMB separates <strong>reference admission from practice allocation</strong>. The four-arm confirmation holds the learner, references, support and training budget fixed. It does not establish the proposed relative-progress benefit. A coverage floor cannot create a missing behavior, and apparent progress alone cannot identify intrinsic difficulty or forgetting.')
result_section = '''<section id="results"><span class="numeral">Completed confirmation · measured simulation</span><h2>Changed practice did not establish a better tracker.</h2>
<p class="lead">Final feasible-hard R−U TrackingScore is <strong>−0.01507</strong>, with two-sided seed-level 95% confidence interval <strong>[−0.09436, +0.06422]</strong>. Two seeds favor U and one favors R. The frozen decision is <strong>inconclusive</strong>.</p>
<div class="scroll" role="region" aria-label="Paired confirmation results" tabindex="0"><table><caption>Final checkpoint 3999 · three independently trained seed pairs</caption><thead><tr><th scope="col">R−U panel</th><th scope="col">Seed 21</th><th scope="col">Seed 22</th><th scope="col">Seed 23</th><th scope="col">Mean</th><th scope="col">95% t interval</th></tr></thead><tbody>
<tr><th scope="row">Feasible-hard · primary</th><td>−0.03400</td><td>−0.03299</td><td>+0.02178</td><td>−0.01507</td><td>[−0.09436, +0.06422]</td></tr>
<tr><th scope="row">All-panel · guard</th><td>−0.04892</td><td>−0.01402</td><td>+0.03500</td><td>−0.00932</td><td>[−0.11405, +0.09542]</td></tr></tbody></table></div>
<p>The +0.02 point-estimate target and positive lower primary bound do not pass. The all-panel lower bound also fails the −0.01 non-regression guard. These wide intervals establish neither benefit nor harm nor equivalence; they do not rule out a target-sized benefit.</p>
<figure><a class="chart-link" href="assets/confirmation-2026-09-06/paired_results_and_learning_curves.pdf"><img src="assets/confirmation-2026-09-06/paired_results_and_learning_curves.png" width="2394" height="817" alt="Final hard and all-panel paired R minus U results have negative means and wide confidence intervals spanning zero. Uniform sampling has a higher mean feasible-hard score at all four observed checkpoints."></a><figcaption>Points are paired seeds; diamonds and bars show means and two-sided 95% t intervals (df=2). Dashed lines mark the hard point target and all-panel lower-bound margin. Thin learning curves are seeds; thick curves are means. Training transitions are the cost axis. <a href="assets/confirmation-2026-09-06/learning_curves.csv">Curve data</a> · <a href="assets/confirmation-2026-09-06/paired_results_and_learning_curves.pdf">PDF</a>.</figcaption></figure>
<p><strong>No efficiency-accelerator claim:</strong> exploratory normalized hard learning-curve area R−U is lower in all three seeds (mean −0.02898; descriptive 95% interval [−0.05774, −0.00023]). Two R seeds never reach their paired U final score on the observed grid. Four checkpoints cannot identify a precise crossover. This secondary analysis does not replace the registered decision.</p>
<p>Descriptive final hard R−D is −0.00675, interval [−0.02189, +0.00840]. This compares allocator designs and does not establish a progress-specific advantage. The supplementary hierarchical bootstrap likewise does not rescue the primary decision. <a href="assets/confirmation-2026-09-06/summary.json">Full-precision results and source identities</a> · <a href="assets/confirmation-2026-09-06/efficiency_descriptive.json">Attainment including non-attainment</a>.</p>
<div class="callout"><p><strong>Research consequence:</strong> preserve this result and diagnose the value of additional practice. Continuous execution asks whether local tracking survives a full reference; H1 tests admission under D; independent scoring and matched practice branches test whether the progress signal predicts recoverable skill. Any new sampler or seed extension needs a separate prospective study.</p></div>
</section>
'''
replace('<section id="findings">', result_section + '<section id="findings">')
replace('All 10 completed confirmation runs pass replay', 'All 12 confirmation runs pass replay')
replace('These results establish that the interventions occurred; their tracking value is still pending.', 'These results establish that the interventions occurred. The completed held-out comparison does not establish the registered tracking benefit.')
replace('compare R with U to test utility, A to examine the scale correction, and D to ask whether a progress signal offers more than practicing failures.', 'keep the measured allocation contrast separate from the inconclusive policy result. Compare R with U, A and D under the stated limits; R−D is not a pure ranking-only intervention.')
replace('03 · The experiment now running', '03 · The completed controlled experiment')
replace('Every training gate must pass before any of the 48 held-out cells opens.', 'All training gates passed before the 48 held-out cells opened. The complete campaign uses 49,152,000 simulator transitions per policy.')
replace('<td class="active">Running</td>', '<td class="done">Complete · pass</td>')
replace('<td class="waiting">Queued</td>', '<td class="done">Complete · pass</td>')
replace('The queued frozen-policy pilot first checks instrumentation; it cannot establish this mechanism.', 'The completed frozen-policy pilot checks instrumentation; it does not establish this mechanism or the estimator’s noise floor.')
start = s.index('<ol class="roadmap">')
end = s.index('</ol>', start) + len('</ol>')
s = s[:start] + '''<ol class="roadmap">
<li><div class="phase-status">COMPLETE<br>Confirmation</div><div><h3>Preserve the inconclusive policy result.</h3><p>All 12 runs and 48 cells are complete and independently reproduced. No registered benefit or efficiency-accelerator claim is supported. Do not append seeds or change thresholds to obtain a favorable decision.</p></div></li>
<li><div class="phase-status">NEXT<br>C1 · continuous</div><div><h3>Test usable execution beyond short windows.</h3><p>The existing held-out test already uses uninterrupted three-second windows. A new CPU development adapter completes four attempts on two entire admitted training references lasting 8.58 and 6.12 seconds, with one fixed development policy and no intermediate resets. This is pipeline evidence only. Validate failure retirement and CUDA execution, fix reference-only selection, then compare U/D/R on the same continuous sequences. Never join disconnected admitted intervals across rejected transitions.</p></div></li>
<li><div class="phase-status">NEXT<br>H1 · admission</div><div><h3>Measure whether excluding rejected practice helps learning.</h3><p>Compare D with admission on/off over the same 800 clips and candidate partition, disclosing normalization. CPU training, evaluation and provenance checks pass; full study remains disabled pending the remaining production checks and separate freeze. This tests admission under D, not an admission-by-relative-progress interaction.</p></div></li>
<li><div class="phase-status">PILOT COMPLETE<br>Signal value</div><div><h3>Distinguish recoverable skill from apparent progress.</h3><p>Instrumentation passes; stationarity and the noise floor remain unestablished. Use independent repeated scoring at training-relevant sample counts. A proposed three-development-seed, two-checkpoint, targeted/control design gives twelve equal-budget practice branches. Freeze selection and analysis before their outcomes. Reliability-calibrated progress is a candidate only if diagnosis warrants a change.</p></div></li>
<li><div class="phase-status">DEVELOPMENT<br>Physical sensitivity</div><div><h3>Validate the runtime before interpreting perturbation results.</h3><p>CPU lifecycle checks cover delay, torque caps, friction and policy immutability. CUDA validation stopped on an assertion about an optional camera/raycast graph. The separately bound correction is queued behind the unchanged GPU-capacity gate; full sensitivity evaluation remains disabled. No robustness benefit follows from development checks.</p></div></li>
<li><div class="phase-status">UNCONFIRMED<br>Hardware</div><div><h3>Test the same allocation claim on a common robot interface.</h3><p>First audit actor observations, export and actions. Proposed nominal references: turning, crouching and dynamic stepping, two per family, selected before comparing policies. Use U/D/R with common adaptation and initial conditions; retain every attempt, intervention and failure. Hardware access and CLIMB transfer are unconfirmed.</p></div></li>
</ol>
<p><strong>Submission milestones:</strong> September 10 claim selection; September 12 evidence cutoff; September 13–15 paper integration. The <a href="https://2027.ieee-icra.org/contribute/call-for-icra-2027-papers-now-accepting-submissions/">official ICRA 2027 call</a> sets September 15, 2026 as the paper deadline and an eight-page limit including references. Essential evidence must fit in the paper; reviewers need not inspect external links. These milestones do not promise favorable or completed studies.</p>''' + s[end:]
start = s.index('<article class="draft-box">')
end = s.index('</article>', start) + len('</article>')
s = s[:start] + '''<article class="draft-box"><span class="tag measured">Working abstract · complete simulation result</span><h3>CLIMB: Exact-Support Curriculum Learning for Humanoid Motion Tracking</h3>
<p>A failed tracking attempt does not establish that additional practice is valuable. CLIMB separates model-based reference admission from learner-dependent allocation, binding each training trial to exact temporal support under a declared screen. We compare uniform, absolute-progress, relative-progress and conditional-failure allocation with unchanged references, a common learner and matched training budgets. Across three training seeds, relative progress changes exposure but does not establish the registered held-out tracking benefit: final feasible-hard R−U TrackingScore is −0.01507, with two-sided seed-level 95% interval [−0.09436, +0.06422]. The all-panel non-regression criterion also does not pass. Exploratory learning curves do not support an efficiency-accelerator claim. These findings motivate separate tests of admission value, signal reliability and the causal value of targeted practice. Continuous-execution development verifies longer reference traversal on two training motions; comparative continuous execution and hardware transfer remain pending.</p></article>''' + s[end:]
replace('All completed run summaries, 410 replayed checkpoint states, source hashes and explicitly incomplete arms.', 'All 12 trained policies, 48 held-out cells and 492 replayed checkpoint states. Full-precision results preserve the inconclusive decision.')
replace('<a href="assets/progress-2026-09-06/research_snapshot.json">Dated JSON export</a>', '<a href="assets/confirmation-2026-09-06/summary.json">Complete policy results</a> · <a href="assets/progress-2026-09-06/research_snapshot.json">Archived 22:17 allocation snapshot</a>')
replace('plan/PAGES_RESEARCH_STORY_2026-09-06.md', 'plan/USEFUL_PRACTICE_SUBMISSION_2026-09-06.md')
p.write_text(s)

p = ROOT / 'docs/assets/research-story.js'
s = p.read_text().replace('The queued frozen-policy pilot first checks instrumentation; it cannot establish this mechanism.', 'The completed frozen-policy pilot checks instrumentation; it does not establish this mechanism or the estimator’s noise floor.').replace('The queued pilot first verifies the instrumentation; it is not yet this stationarity study.', 'The completed pilot verifies the instrumentation; it is not this stationarity study.')
p.write_text(s)

p = ROOT / 'docs/relative-progress.html'
s = p.read_text()
assert '<body>' in s
s = s.replace('<body>', '<body>\n<div class="archive-banner" role="note"><strong>New complete result · 6 September, 23:47 EDT:</strong> all 12 training runs and 48 held-out cells finished. The registered policy result is inconclusive; the all-panel guard does not pass. <a href="index.html#results">Read paired policy results and the revised research plan</a>. The allocation progress snapshots below retain their earlier timestamps.</div>', 1)
p.write_text(s)
print('Updated public result, abstract, research plan and historical detail notice')
