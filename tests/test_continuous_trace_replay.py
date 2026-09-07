"""Reject hidden restarts, omitted failures and corrupted continuous outcomes."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from verify_continuous_trace import replay_trace


def fixture():
    conditions = [dict(condition_id=f'u{i}', start_frame=0, support_stop=h+1,
                       horizon_steps=h) for i, h in enumerate((3, 5))]
    steps = []
    for step in range(1, 6):
        active = [step <= 2, True]
        remaining = [step < 2, step < 5]
        steps.append(dict(step=step, active=active, remaining=remaining,
                          before=[step-1, step-1], after=[step, step],
                          failed=[step == 2, False]))
    trace = dict(steps=steps, resets=[dict(step=2, ids=[0])],
                 reference_writes=[dict(step=2, ids=[0])])
    rows = [dict(condition_id=f'u{i}', success=str(i), survival_s=str(d / 50),
                 actual_window_s=str(h / 50), termination_causes='' if i else 'ee_body_pos',
                 common_root_relative_mpkpe_m_mean='0.1',
                 common_anchor_orientation_error_rad_mean='0.2')
            for i, (d, h) in enumerate(((2, 3), (5, 5)))]
    return conditions, trace, rows


def test_failure_and_completion_replay_with_retired_housekeeping():
    result = replay_trace(*fixture())
    assert result['failed_attempts'] == result['completed_attempts'] == 1
    assert result['partial_active_steps'] == 3
    assert result['rows'][0]['failure_frame'] == 2
    assert result['rows'][1]['failure_frame'] is None


@pytest.mark.parametrize('corruption', ['reactivate', 'early_retire', 'hide_failure',
                                      'active_reset', 'unfinished', 'wrap',
                                      'extra_step', 'wrong_success', 'late_survival',
                                      'missing_cause', 'duplicate', 'nonfinite'])
def test_invalid_execution_rejected(corruption):
    conditions, trace, rows = deepcopy(fixture())
    if corruption == 'reactivate':
        trace['steps'][2]['active'][0] = True
    elif corruption == 'early_retire':
        trace['steps'][0]['remaining'][1] = False
    elif corruption == 'hide_failure':
        trace['steps'][1]['failed'][0] = False
    elif corruption == 'active_reset':
        trace['resets'][0]['ids'] = [1]
    elif corruption == 'unfinished':
        trace['steps'].pop()
    elif corruption == 'wrap':
        trace['steps'][1]['after'][1] = 0
    elif corruption == 'extra_step':
        trace['steps'].append(deepcopy(trace['steps'][-1]))
    elif corruption == 'wrong_success':
        rows[0]['success'] = '1'
    elif corruption == 'late_survival':
        rows[0]['survival_s'] = '0.06'
    elif corruption == 'missing_cause':
        rows[0]['termination_causes'] = ''
    elif corruption == 'duplicate':
        conditions[1]['condition_id'] = 'u0'
    elif corruption == 'nonfinite':
        rows[0]['common_root_relative_mpkpe_m_mean'] = 'nan'
    with pytest.raises(ValueError):
        replay_trace(conditions, trace, rows)


def test_failure_on_horizon_is_failure_not_success():
    conditions, trace, rows = fixture()
    trace['steps'][-1]['failed'][1] = True
    rows[1]['success'] = '0'
    rows[1]['termination_causes'] = 'ee_body_pos'
    result = replay_trace(conditions, trace, rows)
    assert result['failed_attempts'] == 2
    assert result['rows'][1]['failure_frame'] == 5
