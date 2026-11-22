"""Regression tests for defects exposed by exchanging B17's project."""
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch as mock

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'labs/e11e12'), str(ROOT/'labs/e8e10')]
import pipeline
from lab import fixture, scan, patch, validate, commit, run


class ExchangeRegressions(unittest.TestCase):
    def test_command_timeout_kills_descendant(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            code="import subprocess,time,pathlib; p=subprocess.Popen(['sleep','120']); pathlib.Path('child.pid').write_text(str(p.pid)); time.sleep(120)"
            with self.assertRaises(subprocess.TimeoutExpired):
                run([sys.executable,'-c',code],root,timeout=0.3)
            pid=int((root/'child.pid').read_text())
            status=Path('/proc')/str(pid)/'stat'
            # An unreaped zombie has exited and cannot continue work.
            self.assertTrue(not status.exists() or status.read_text().split()[2]=='Z')

    def test_external_report_hash_checked_before_repair(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root/'project'
            project.mkdir()
            report = root/'report.json'
            report.write_text(json.dumps({'schema_version':'e11e12-1','kind':'fixed-md',
                'commit':'a'*40,'status':'SUCCEEDED','data':{'commit':'a'*40,'findings':[]}}))
            request = {'mode':'e11-b','repo':str(project),'base':'a'*40,'target':'a'*40,
                       'candidate':str(root/'candidate'),'fixed_report':str(report),
                       'fixed_report_sha256':'0'*64}
            def drafted(*args, **kwargs):
                folder = args[2]
                folder.mkdir(parents=True)
                (folder/'result.json').write_text('{"status":"SUCCEEDED"}')
                return {'status':'SUCCEEDED'}
            with mock.object(pipeline,'snapshot',return_value='a'*40), mock('draft.autobuild.auto_build',side_effect=drafted):
                result = pipeline.execute(request,root/'out')
            self.assertEqual(result['status'],'FAILED')
            self.assertEqual(result['error']['code'],'ARTIFACT_HASH_MISMATCH')

    def test_value_prefix_output_is_validated_without_editing_program(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root/'project'
            fixture(project)
            source = project/'main.c'
            source.write_text(source.read_text().replace('printf("%d','printf("VALUE=%d'))
            commit(project,'Use B17 output format')
            diff, _ = patch(project,scan(project))
            candidate = root/'candidate.patch'
            candidate.write_text(diff)
            before = source.read_bytes()
            result = validate(project,candidate,root/'validation',
                              expected_output='VALUE=1',header_change_output='VALUE=2')
            self.assertTrue(result['accepted'],result)
            self.assertEqual(before,source.read_bytes())

    def test_failed_output_assertion_preserves_original(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root/'project'
            fixture(project)
            before = (project/'Makefile').read_bytes()
            diff, _ = patch(project,scan(project))
            candidate = root/'candidate.patch'
            candidate.write_text(diff)
            result = validate(project,candidate,root/'validation',fail_test=True)
            self.assertFalse(result['accepted'])
            self.assertTrue(result['rollback'])
            self.assertEqual(before,(project/'Makefile').read_bytes())


if __name__ == '__main__':
    unittest.main()
