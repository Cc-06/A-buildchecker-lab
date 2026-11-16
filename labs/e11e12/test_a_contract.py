"""Additional A-track consumer contract regressions, independent of Docker."""
import copy
import unittest
import pipeline


class AContracts(unittest.TestCase):
    def test_process_evidence_does_not_change_finding_identity(self):
        one = [{'type': 'MISSING', 'target': 'main.o', 'dependency': 'extra.h',
                'evidence': [{'pid': 10, 'trace_file': 't.10'}]}]
        two = copy.deepcopy(one)
        two[0]['evidence'] = [{'pid': 999, 'trace_file': 't.999'}]
        self.assertEqual(pipeline.normalized(one), pipeline.normalized(two))

    def test_comparison_scope_is_object_targets(self):
        one = [{'type': 'MISSING', 'target': 'main.o', 'dependency': 'config.h'}]
        two = one + [{'type': 'MISSING', 'target': 'app', 'dependency': 'main.o'}]
        self.assertEqual(pipeline.normalized(one), pipeline.normalized(two))

    def test_changed_dependency_cannot_pass_comparison(self):
        one = [{'type': 'MISSING', 'target': 'main.o', 'dependency': 'config.h'}]
        two = [{'type': 'MISSING', 'target': 'main.o', 'dependency': 'extra.h'}]
        self.assertNotEqual(pipeline.normalized(one), pipeline.normalized(two))

    def test_redundant_and_missing_are_distinct(self):
        one = [{'type': 'MISSING', 'target': 'main.o', 'dependency': 'config.h'}]
        two = [{'type': 'REDUNDANT', 'target': 'main.o', 'dependency': 'config.h'}]
        self.assertNotEqual(pipeline.normalized(one), pipeline.normalized(two))

    def test_B_handoff_rejects_baseline_commit(self):
        envelope = {'schema_version': 'e11e12-1', 'kind': 'incremental-check',
                    'status': 'SUCCEEDED', 'commit': 'a' * 40}
        with self.assertRaises(pipeline.Failure) as raised:
            pipeline.check_envelope(envelope, 'b' * 40, 'incremental-check')
        self.assertEqual(raised.exception.code, 'STALE_REPORT')


if __name__ == '__main__':
    unittest.main()
