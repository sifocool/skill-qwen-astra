import tempfile
import unittest
from cyber_engine.bench.cases import holdout,development,materialize
from cyber_engine.bench.run import judge,parse,instruction
from cyber_engine.scope import Scope


class BenchmarkTests(unittest.TestCase):
    def test_all_ground_truth_witnesses_and_controls(self):
        for case in development()+holdout():
            with self.subTest(case=case['id']),tempfile.TemporaryDirectory() as d:
                materialize(case,d)
                scope=Scope(dict(authorization='fixture validation',roots=[d],adapters=['replay'],trusted_lab=True))
                r=judge(case,dict(verdict='bug' if case['bug'] else 'clean',witness=case['witness'],control=case['control'],
                    line=case['root_line'],root_cause='known fixture cause for test'),scope)
                self.assertTrue(r['correct'],r);self.assertTrue(r['reproducible'],r)

    def test_judge_does_not_accept_claim_without_witness_or_correct_line(self):
        case=development()[0]
        with tempfile.TemporaryDirectory() as d:
            materialize(case,d);scope=Scope(dict(authorization='fixture',roots=[d],adapters=['replay'],trusted_lab=True))
            for witness,line in [(case['control'],case['root_line']),(case['witness'],999)]:
                r=judge(case,dict(verdict='bug',witness=witness,control=case['control'],line=line,root_cause='a convincing sounding claim'),scope)
                self.assertFalse(r['correct'])

    def test_no_oracle_or_witness_in_instructions(self):
        for c in holdout():
            text=instruction('enhanced',c)
            self.assertNotIn(c['reference'],text)
            self.assertNotIn('reference.py',text)

if __name__=='__main__':unittest.main()
