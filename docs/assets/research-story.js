'use strict';
const picker = document.querySelector('.question-picker');
if (picker) {
  const content = {
    recovery: ['Recoverable decline', 'A previously learned skill deteriorates and extra practice restores it.', 'After independently measuring signal stability, branch matched policies into equal-budget targeted and control practice, then score both on independent paired trials.', 'Retain revisiting of declining skills if the extra practice causes recovery. The queued frozen-policy pilot first checks instrumentation; it cannot establish this mechanism.'],
    noise: ['Estimator noise', 'Finite trials or changing sampled conditions create apparent progress even when the policy has not changed.', 'Hold policy weights and normalization fixed; use independent repeated scoring with declared condition seeds to estimate variability. The queued pilot first verifies the instrumentation; it is not yet this stationarity study.', 'If noise explains the ranking, test uncertainty-aware estimation in a separately frozen follow-up. Keep the current confirmation sampler unchanged.'],
    persistent: ['Persistent difficulty', 'Repeated failure reflects a reference, support or control limitation that the current extra practice does not resolve.', 'Compare equal-budget practice branches and retain all failures, then relate independent outcomes to reference diagnostics and motion characteristics. Failure alone cannot prove irrecoverability.', 'Prioritize a reference, coverage or representation intervention when practice does not help under the tested budget; evaluate its policy effect independently.']
  };
  const detail = document.querySelector('#mechanism-detail');
  picker.hidden = false;
  picker.addEventListener('click', event => {
    const button = event.target.closest('button[data-question]');
    if (!button) return;
    picker.querySelectorAll('button').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    const selected = content[button.dataset.question];
    const heading = document.createElement('h3');
    heading.textContent = selected[0];
    const paragraphs = selected.slice(1).map((text, index) => {
      const p = document.createElement('p');
      const label = document.createElement('strong');
      label.textContent = ['Hypothesis: ', 'Discriminating test: ', 'Possible use: '][index];
      p.append(label, document.createTextNode(text));
      return p;
    });
    detail.replaceChildren(heading, ...paragraphs);
  });
}
