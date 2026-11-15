import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from cyber_engine.install import install,EVENTS
from cyber_engine.karvan_export import bundle,validate_with_karvan
from cyber_engine.tests import test_engine


class InstallTests(unittest.TestCase):
    def test_preserves_settings_hooks_idempotent_and_installed_execution(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);old=dict(env={'PRIVATE_TOKEN':'not-real'},hooks={'Stop':[{'hooks':[{'type':'command','command':'true'}]}]})
            (p/'settings.json').write_text(json.dumps(old))
            first=install(p);second=install(p)
            after=json.loads((p/'settings.json').read_text())
            self.assertEqual(after['env'],old['env']);self.assertEqual(after['hooks']['Stop'][0],old['hooks']['Stop'][0])
            self.assertEqual(len(after['hooks']['Stop']),2)
            self.assertNotIn('not-real',json.dumps(first))
            for event in EVENTS:
                cmd=after['hooks'][event][-1]['hooks'][0]['command']
                r=subprocess.run(shlex.split(cmd),input=json.dumps(dict(cwd=d,hook_event_name=event)),capture_output=True,text=True)
                self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout,'')
            self.assertTrue(Path(first['backup'],'settings.json').exists())


class KarvanTests(unittest.TestCase):
    setUp=test_engine.EngineTests.setUp
    tearDown=test_engine.EngineTests.tearDown
    plan=test_engine.EngineTests.plan
    confirm=test_engine.EngineTests.confirm
    def test_actual_karvan_interface_in_disposable_ledger(self):
        root=Path('/Users/apple/karvan-e34/karvan_e34')
        if not root.exists():self.skipTest('BLOCKED Karvan package absent')
        self.confirm();self.e.conclude(self.h1,'The x input fails while the y control succeeds in the fixture.')
        data=bundle(self.e);r=validate_with_karvan(data,root)
        self.assertEqual(r['status'],'PASS');self.assertEqual(r['admitted_status'],'candidate')
        self.assertFalse(r['live_ledger_modified'])

if __name__=='__main__':unittest.main()
