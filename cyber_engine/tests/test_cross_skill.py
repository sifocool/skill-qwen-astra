import json
from pathlib import Path
import tempfile
import unittest
from cyber_engine.engine import Engine,SKILLS


class CrossSkillTests(unittest.TestCase):
    def test_one_investigation_four_skills_shared_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            # Local harmless reconstruction dispatch: only increments a marker.
            old='''import sys,json
def marker():
    return 1
def reconstruct(verified):
    count=marker()
    return count
def main():
    x=json.load(sys.stdin)
    if isinstance(x,list):
        print(json.dumps([reconstruct(v) for v in x]))
    else:
        n=reconstruct(x['verified'])
        print(json.dumps({'label':'violation' if n and not x['verified'] else 'clean','markers':n},sort_keys=True))
if __name__=='__main__': main()
'''
            (root/'old.py').write_text(old)
            (root/'new.py').write_text(old.replace('count=marker()','count=marker() if verified else 0'))
            e=Engine(root/'.astra/state')
            try:
                e.init(dict(authorization='cross-skill local marker lab',roots=[d],adapters=list(SKILLS),trusted_lab=True),'can an unverified record invoke marker?')
                h1=e.hypothesis('unverified record reaches marker');h2=e.hypothesis('verification prevents marker')
                specs=[
                    ('protocol',dict(script='old.py',traces=[dict(role='unverified',steps=[False],expected=[0])]),{h1:'transition_violation',h2:'transitions_valid'},'discriminate'),
                    ('deserialize_trace',dict(script='old.py',input='{"verified":false}'),{h1:'callbacks_observed',h2:'no_callbacks'},'explore'),
                    ('replay',dict(script='old.py',input='{"verified":false}'),{h1:'violation',h2:'clean'},'discriminate'),
                    ('replay',dict(script='old.py',input='{"verified":true}'),{h1:'clean',h2:'clean'},'control'),
                    ('compare',dict(before='old.py',after='new.py',input='{"verified":false}',control='{"verified":true}'),{h1:'fixed',h2:'not_fixed'},'regression'),
                ]
                ids=[]
                for adapter,args,predictions,kind in specs:
                    eid=e.plan(adapter,args,predictions,'verify one edge of reconstruction contract',kind=kind)['id']
                    e.run(eid);ids.append(eid)
                e.run(ids[2],repeat=True);e.reject(h2,ids[2])
                e.challenge('marker is never callable in this harness',ids[3],'verified control invokes marker normally')
                self.assertEqual(e.conclude(h1,'Unverified record invokes marker; guard before dispatch preserves valid control.',fix=True)['status'],'PASS')
                state=e.store.load();skills={v['skill'] for v in state['experiments'].values()}
                self.assertEqual(skills,{'blackbox-recon','patch-diffing','fuzz-crash-triage','gadget-deserialization'})
                proofs=[e.store.get(sha) for exp in state['experiments'].values() for sha in exp['evidence']]
                self.assertEqual({p['investigation'] for p in proofs},{state['id']})
                self.assertTrue(e.knowledge()['evidence'])
            finally:e.store.close()

if __name__=='__main__':unittest.main()
