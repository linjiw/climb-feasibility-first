"""Check that incomplete H1 cannot become a manuscript result."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import report_h1 as report


class ReportChecks(unittest.TestCase):
    def test_partial_terminal_rejected_before_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'terminal_status.json').write_text(json.dumps({'status': 'stopped_without_complete_H1'}))
            (root / 'analysis.json').write_text('INVALID MUST NEVER READ')
            with self.assertRaisesRegex(ValueError, 'non-complete'):
                report.terminal_input(root)

    def test_foreign_contract_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'terminal_status.json').write_text(json.dumps({'status': 'completed', 'contract': {'path': 'absent', 'sha256': 'foreign'}}))
            with self.assertRaisesRegex(ValueError, 'unexpected'):
                report.terminal_input(root)

    def test_modified_analysis_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'terminal_status.json').write_text(json.dumps({'status': 'completed', 'contract': {'path': 'contract', 'sha256': report.CONTRACT_SHA256}, 'analysis': {'path': str(root / 'analysis.json'), 'sha256': 'different'}}))
            with patch.object(report, 'digest', return_value=report.CONTRACT_SHA256), self.assertRaisesRegex(ValueError, 'analysis differs'):
                report.terminal_input(root)

    def test_allocation_ratio_zero_mass_and_top1(self):
        training = {}
        for seed in report.SEEDS:
            for arm in ('on', 'off'):
                snapshots = [{'iteration': i, 'positive_excess_total': 2. if arm == 'off' else 0.,
                              'positive_excess_rejected': 1. if arm == 'off' else 0.,
                              'top1_rejected': arm == 'off', 'top1_unit': {'synthetic': True}}
                             for i in [*range(1000, 4000, 100), 3999]]
                training[f'{arm}_s{seed}'] = {'mechanism': snapshots, 'completed_trials': 10,
                    'final_allocation': {'uncapped_prior_rejected_mass': .115 if arm == 'off' else 0.,
                                        'post_cap_rejected_mass': .17 if arm == 'off' else 0.,
                                        'rejected_completed_trials': 2 if arm == 'off' else 0}}
        rows = report.mechanism(training)
        self.assertEqual(len(rows), 10)
        for row in rows:
            self.assertEqual(row['rejected_share_of_positive_excess'], .5 if row['arm'] == 'off' else None)
            self.assertEqual(row['top1_rejected_state_fraction'], 1. if row['arm'] == 'off' else 0.)
        training['off_s1041']['mechanism'].pop()
        with self.assertRaisesRegex(ValueError, 'grid changed'):
            report.mechanism(training)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReportChecks))
    out = report.ROOT / 'reports/h1_manuscript_preparation_2026-09-07/reporter_tests.json'
    out.write_text(json.dumps({'status': 'pass' if result.wasSuccessful() else 'failed', 'tests': result.testsRun,
                              'classification': 'SYNTHETIC manuscript ingestion checks only'}, indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
