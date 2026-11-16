import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from cyber_engine.engine import Engine,SKILLS,route
from cyber_engine.hooks import handle
from cyber_engine.scope import Scope


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.script=self.root/'probe.py'
        self.script.write_text('import sys,json\ns=sys.stdin.read()\nprint(json.dumps({"label":"bad" if s=="x" else "good"}))\n')
        self.e=Engine(self.root/'.astra/state')
        self.scope=dict(authorization='user-owned unit laboratory',roots=[str(self.root)],
                        adapters=list(SKILLS),trusted_lab=True)
        self.e.init(self.scope,'is x mishandled?')
        self.h1=self.e.hypothesis('only x violates the contract')
        self.h2=self.e.hypothesis('all input is accepted normally')

    def tearDown(self):
        self.e.store.close();self.tmp.cleanup()

    def plan(self,value,kind='discriminate',cost=1):
        return self.e.plan('replay',dict(script=str(self.script),input=value),
                           {self.h1:'bad' if value=='x' else 'good',self.h2:'good'},
                           'distinguish input-specific failure from general failure',cost,kind)['id']

    def confirm(self):
        test=self.plan('x');self.e.run(test);self.e.run(test,repeat=True)
        self.e.reject(self.h2,test)
        control=self.plan('y','control');self.e.run(control)
        self.e.challenge('harness fails for every input',control,'y is accepted')
        return test,control

    def test_shared_evidence_routing_and_confirmation(self):
        test,control=self.confirm()
        s=self.e.store.load()
        self.assertEqual(s['experiments'][test]['skill'],'fuzz-crash-triage')
        sha=s['experiments'][test]['evidence'][0]
        self.assertEqual(self.e.store.get(sha)['experiment'],test)
        self.assertEqual(self.e.conclude(self.h1,'only x violates contract')['status'],'PASS')
        self.assertEqual(len(self.e.knowledge()['evidence']),3)

    def test_selector_information_per_cost_dedup_and_stop(self):
        expensive=self.plan('x',cost=5)
        # Different arguments produce a genuinely separate experiment.
        cheap=self.e.plan('replay',dict(script=str(self.script),input='x',timeout=2),
                         {self.h1:'bad',self.h2:'good'},'cheap discriminant',1)['id']
        self.assertEqual(self.e.select()['id'],cheap)
        self.assertEqual(self.plan('x'),expensive)
        self.e.run(cheap);self.e.reject(self.h2,cheap)
        self.assertEqual(self.e.select()['action'],'stop')

    def test_missing_prediction_cannot_inflate_information(self):
        self.e.plan('replay',dict(script=str(self.script),input='x'),{self.h1:'bad'},'incomplete model')
        self.assertEqual(self.e.select()['action'],'stop')

    def test_no_claim_without_proof_and_no_fake_rejection(self):
        test=self.plan('x')
        self.assertEqual(self.e.conclude(self.h1,'DONE')['status'],'PARTIAL')
        with self.assertRaises(ValueError):self.e.reject(self.h2,test)
        self.e.run(test)
        with self.assertRaises(ValueError):self.e.reject(self.h1,test)
        with self.assertRaises(ValueError):self.e.knowledge()

    def test_input_change_invalidation(self):
        self.confirm();self.script.write_text('print("changed")\n')
        self.assertTrue(any('stale' in p for p in self.e.gate(self.h1)))

    def test_rejected_input_and_symlink_escape(self):
        with self.assertRaises(ValueError):Scope(dict(roots=[str(self.root)]))
        with tempfile.TemporaryDirectory() as outside:
            f=Path(outside)/'secret';f.write_text('private')
            (self.root/'link').symlink_to(f)
            with self.assertRaises(ValueError):Scope(self.scope).path('link')
        with self.assertRaises(ValueError):Scope(self.scope).adapter('shell')
        with self.assertRaises(ValueError):Scope(self.scope).url('http://example.com')

    def test_regression_guard_requires_actual_comparison(self):
        self.confirm()
        self.assertTrue(any('Regression Guard' in x for x in self.e.gate(self.h1,fix=True)))

    def test_hook_events_no_tool_denial_and_completion_gate(self):
        payload=dict(cwd=str(self.root),session_id='session-private')
        for event in ['UserPromptSubmit','PreToolUse','PostToolUse','PostToolUseFailure']:
            result=handle(dict(payload,hook_event_name=event,tool_input={'command':'secret'}))
            self.assertEqual(result['hookSpecificOutput']['hookEventName'],event)
            self.assertNotIn('permissionDecision',json.dumps(result))
        r=handle(dict(payload,hook_event_name='Stop',last_assistant_message='DONE'))
        self.assertEqual(r['decision'],'block')
        handle(dict(payload,hook_event_name='Stop',last_assistant_message='DONE',stop_hook_active=True))
        self.assertEqual(self.e.store.load()['status'],'PARTIAL')
        self.assertEqual(handle(dict(payload,hook_event_name='Stop',last_assistant_message='PARTIAL: unresolved')), {})

    def test_hook_recorder_on_validated_conclusion(self):
        self.confirm();self.e.conclude(self.h1,'x violates contract')
        self.assertEqual(handle(dict(cwd=str(self.root),hook_event_name='Stop')), {})
        self.assertEqual(self.e.store.load()['knowledge']['status'],'verified-local')

    def test_unrelated_hook_does_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(handle(dict(cwd=d,hook_event_name='Stop',last_assistant_message='DONE')), {})

    def test_partial_stop_accepts_explicit_limit_without_loop(self):
        result=handle(dict(cwd=str(self.root),hook_event_name='Stop',last_assistant_message='PARTIAL: rien de confirmé, tests incomplets'))
        self.assertEqual(result,{})
        self.assertEqual(self.e.store.load()['status'],'PARTIAL')

    def test_initial_routing_uses_only_visible_question(self):
        for question,skill in [('Investigate a parser crash','fuzz-crash-triage'),('Compare versions before/after patch','patch-diffing'),
            ('Check tenant roles and API states','blackbox-recon'),('Which deserialization callback runs?','gadget-deserialization')]:
            self.assertEqual(route(question)['skill'],skill)

    def test_cli_read_only_actions_do_not_create_state(self):
        path=self.root/'new-state'
        for action,payload,expected in [('route','{"question":"parser crash"}',0),('status','{}',1)]:
            r=subprocess.run([sys.executable,'-m','cyber_engine','--state',str(path),action,payload],capture_output=True,text=True)
            self.assertEqual(r.returncode,expected,r.stderr)
            self.assertFalse(path.exists())

    def test_uninitialized_database_does_not_activate_hook(self):
        with tempfile.TemporaryDirectory() as d:
            orphan=Engine(Path(d)/'.astra/state');orphan.store.close()
            self.assertEqual(handle(dict(cwd=d,hook_event_name='Stop',last_assistant_message='DONE')), {})

    def test_evidence_tampering_detected(self):
        test=self.plan('x');self.e.run(test)
        sha=self.e.store.load()['experiments'][test]['evidence'][0]
        self.e.store.db.execute('UPDATE evidence SET value=? WHERE sha=?',('{}',sha));self.e.store.db.commit()
        with self.assertRaises(ValueError):self.e.store.get(sha)

    def test_cli_and_hook_subprocess_contract(self):
        r=subprocess.run([sys.executable,'-m','cyber_engine','--state',str(self.root/'.astra/state'),'select'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout)['action'],'stop')
        r=subprocess.run([sys.executable,'-m','cyber_engine.hooks'],input=json.dumps(dict(cwd=str(self.root),hook_event_name='Stop')),
                         capture_output=True,text=True)
        self.assertEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout)['decision'],'block')
        self.assertEqual(os.stat(self.root/'.astra/state/investigation.sqlite').st_mode&0o777,0o600)

if __name__=='__main__':unittest.main()
