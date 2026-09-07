"""Synthetic decisions and scheduler boundaries; no policy outcomes or GPU use."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import protocol as p
import campaign


class H1Tests(unittest.TestCase):
    def scores(self, shifts):
        return {'on': np.full((5, 100), .5) + np.array(shifts)[:, None], 'off': np.full((5, 100), .5)}

    def test_positive_negative_inconclusive_zero(self):
        for expected, shifts in [('positive', [.04, .041, .042, .039, .038]),
                                 ('negative', [-.04, -.041, -.042, -.039, -.038]),
                                 ('inconclusive', [-.08, .02, .06, -.01, .03]),
                                 ('inconclusive', [0, 0, 0, 0, 0])]:
            result = p.analyze(self.scores(shifts), np.arange(25))
            self.assertEqual(result['status'], expected)
            self.assertEqual(result['primary_on_minus_off']['df'], 4)

    def test_no_target_or_all_panel_guard(self):
        scores = self.scores([-.1] * 5)
        scores['on'][:, :25] = .501
        result = p.analyze(scores, np.arange(25))
        self.assertEqual(result['status'], 'positive')
        self.assertLess(result['all_panel_on_minus_off']['mean'], 0)

    def test_incomplete_nonfinite_or_invalid_panel(self):
        for scores, hard in [(self.scores([0] * 5), np.arange(24)),
                             (self.scores([0] * 5), np.zeros(25, dtype=int)),
                             (self.scores([np.nan] * 5), np.arange(25)),
                             ({'on': np.zeros((3, 100)), 'off': np.zeros((3, 100))}, np.arange(25))]:
            with self.assertRaises(ValueError):
                p.analyze(scores, hard)

    def test_exact_order_and_unique_jobs(self):
        jobs = p.schedule()
        self.assertEqual(len(jobs), 52)
        self.assertEqual(len({j['id'] for j in jobs}), 52)
        self.assertEqual([j['stage'] for j in jobs], ['smoke'] * 2 + ['train'] * 10 + ['evaluate'] * 40)
        self.assertEqual({j['seed'] for j in jobs[2:12]}, set(p.SEEDS))

    def test_training_gate_prevents_outcome_reads(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(p, 'verify_training', side_effect=ValueError('missing checkpoint')) as verify:
            with self.assertRaises(ValueError):
                p.all_training({'campaign': directory}, 'digest')
            self.assertEqual(verify.call_count, 1)

    def test_calendar_gates(self):
        contract = {'specification': p.SPEC}
        for date, stage, started in [('2026-09-09T03:00:00+00:00', 'train', False),
                                      ('2026-09-11T17:00:00+00:00', 'train', True),
                                      ('2026-09-13T05:00:00+00:00', 'evaluate', True)]:
            with patch.object(campaign, 'now', return_value=datetime.fromisoformat(date)), self.assertRaises(RuntimeError):
                campaign.deadline(contract, stage, started)

    def test_resource_gate_and_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(campaign, 'deadline'), patch.object(campaign.subprocess, 'check_output', return_value='14000,60\n'):
                campaign.free_gpu({'specification': p.SPEC}, 'train', True, root)
            (root / 'STOP').touch()
            with patch.object(campaign, 'deadline'), self.assertRaises(RuntimeError):
                campaign.free_gpu({'specification': p.SPEC}, 'train', True, root)

    def test_resource_timeout(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(campaign, 'deadline'), patch.object(campaign.time, 'monotonic', side_effect=[0, 7201]), patch.object(campaign.subprocess, 'check_output', return_value='13999,0\n'):
            with self.assertRaises(RuntimeError):
                campaign.free_gpu({'specification': p.SPEC}, 'train', True, Path(directory))


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(H1Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    output = p.ROOT / 'reports/h1_fable_preparation_2026-09-07'
    output.mkdir(exist_ok=True)
    target = output / 'tests.json'
    target.write_text(json.dumps({'status': 'pass' if result.wasSuccessful() else 'failed', 'tests': result.testsRun,
                     'classification': 'SYNTHETIC protocol and scheduling validation; no policy data',
                     'failures': [str(v) for v in result.failures + result.errors]}, indent=2) + '\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
