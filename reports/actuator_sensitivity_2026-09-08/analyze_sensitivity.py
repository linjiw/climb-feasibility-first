#!/usr/bin/env python
"""Analyze the actuator-model sensitivity run against its pre-declared design.

Written before the tightened-condition outcomes were inspected.
Design: plan/ACTUATOR_SENSITIVITY_2026-09-08.md

Gates, in order. Any failure prints its disposition and stops before the sensitivity numbers.
  1. Completeness: 900 clips at each of the three levels, zero errors.
  2. Reproduction: the 139 baseline must match the published 10,705-clip screen to 1e-12 on
     infeasible_frac, airborne_frac and torque_infeasible_frac. This licenses attributing any
     measured change to the actuator limit alone.
  3. Monotonicity: no clip's infeasible_frac may fall by more than 1e-9 under tightening.
     A violation falsifies the lower-bound argument in the manuscript and on the public page.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

OUT = Path('/home/linjiw/climb-feasibility-first/reports/actuator_sensitivity_2026-09-08')
PUBLISHED = Path('/home/linjiw/climb-feasibility-first/reports/feasibility_all/feasibility.csv')
LEVELS = ('139', '120', '90')
RULE = 0.10
REPRO_TOL = 1e-12
MONO_TOL = 1e-9


def main() -> None:
    data = json.loads((OUT / 'sensitivity.json').read_text())
    manifest = json.loads((OUT / 'manifest.json').read_text())
    result: dict = {
        'design': 'plan/ACTUATOR_SENSITIVITY_2026-09-08.md',
        'classification': 'measured CPU screen sensitivity on the 900-clip Phase-G bank',
        'rule': 'infeasible_frac > 0.10',
        'levels_nm': [int(x) for x in LEVELS],
        'screen_sha256': manifest['screen_sha256'],
        'model_sha256': manifest['model_sha256'],
    }

    # ---- gate 1: completeness
    counts = {l: len(data[l]) for l in LEVELS}
    result['completed'] = counts
    result['errors'] = len(manifest.get('errors', []))
    if result['errors'] or len(set(counts.values())) != 1 or counts['139'] != 900:
        result['status'] = 'not_tested'
        result['reason'] = f'incomplete run: {counts}, {result["errors"]} errors'
        emit(result); return

    # ---- gate 2: reproduction of the published screen at the baseline limit
    pub = {r['clip']: r for r in csv.DictReader(open(PUBLISHED))}
    worst, missing, checked = 0.0, 0, 0
    for clip, row in data['139'].items():
        p = pub.get(clip)
        if p is None:
            missing += 1
            continue
        checked += 1
        for k in ('infeasible_frac', 'airborne_frac', 'torque_infeasible_frac'):
            worst = max(worst, abs(float(row[k]) - float(p[k])))
    result['reproduction'] = {'clips_checked': checked, 'clips_absent_from_published': missing,
                              'max_abs_delta': worst, 'tolerance': REPRO_TOL}
    if missing or worst > REPRO_TOL:
        result['status'] = 'not_tested'
        result['reason'] = f'baseline does not reproduce the published screen (max delta {worst:g}, {missing} absent)'
        emit(result); return

    # ---- gate 3: monotonicity under tightening
    viol = []
    for a, b in (('139', '120'), ('120', '90'), ('139', '90')):
        for clip in data[a]:
            d = float(data[b][clip]['infeasible_frac']) - float(data[a][clip]['infeasible_frac'])
            if d < -MONO_TOL:
                viol.append({'clip': clip, 'from': a, 'to': b, 'delta': d})
    result['monotonicity'] = {'violations': len(viol), 'tolerance': MONO_TOL,
                              'examples': viol[:5]}
    if viol:
        result['status'] = 'monotonicity_falsified'
        result['reason'] = ('the lower-bound argument in the manuscript and on the public page '
                            'must be withdrawn and the cause diagnosed')
        emit(result); return

    # ---- sensitivity readouts
    per = {}
    for l in LEVELS:
        rows = data[l]
        flagged = [c for c, r in rows.items() if float(r['infeasible_frac']) > RULE]
        ti = [float(r['torque_infeasible_frac']) for r in rows.values()]
        inf = [float(r['infeasible_frac']) for r in rows.values()]
        per[l] = {
            'flagged': len(flagged), 'of': len(rows),
            'flagged_fraction': len(flagged) / len(rows),
            'mean_infeasible_frac': sum(inf) / len(inf),
            'mean_torque_infeasible_frac': sum(ti) / len(ti),
            'max_torque_infeasible_frac': max(ti),
            'clips_with_torque_infeasible': sum(1 for v in ti if v > 0),
        }
    result['per_level'] = per
    base = set(c for c, r in data['139'].items() if float(r['infeasible_frac']) > RULE)
    for l in ('120', '90'):
        now = set(c for c, r in data[l].items() if float(r['infeasible_frac']) > RULE)
        result.setdefault('flag_changes', {})[l] = {
            'newly_flagged': len(now - base), 'no_longer_flagged': len(base - now),
            'newly_flagged_examples': sorted(now - base)[:5],
        }
    deltas = sorted((float(data['90'][c]['infeasible_frac']) - float(data['139'][c]['infeasible_frac'])
                     for c in data['139']), reverse=True)
    result['infeasible_frac_delta_139_to_90'] = {
        'max': deltas[0], 'mean': sum(deltas) / len(deltas),
        'clips_increased': sum(1 for d in deltas if d > MONO_TOL),
    }
    result['status'] = 'measured'
    result['scope'] = ('900-clip Phase-G bank only; not the 10,705-clip corpus behind the '
                       'manuscript headline. Levels are recorded vendor figures used as declared '
                       'stress points, not calibrated hardware values.')
    emit(result)


def emit(result: dict) -> None:
    (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
