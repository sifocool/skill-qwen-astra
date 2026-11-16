import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from cyber_engine.adapters import execute,REGISTRY
from cyber_engine.scope import Scope


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.scope=Scope(dict(authorization='test fixtures only',roots=[str(self.root)],adapters=list(REGISTRY),trusted_lab=True))

    def tearDown(self):self.tmp.cleanup()
    def write(self,name,content):
        p=self.root/name;p.write_text(content);return str(p)
    def call(self,name,**kwargs):return execute(name,kwargs,self.scope)

    def test_ast_alias_flow_branch_and_safe_control(self):
        p=self.write('a.py','from pickle import loads as decode\ndef f(data):\n x=data\n if data:\n  x=b""\n return decode(x)\n')
        r=self.call('python_ast',path=p)
        self.assertEqual(r['flows'][0]['line'],6);self.assertEqual(r['flows'][0]['sink'],'pickle.loads')
        p=self.write('b.py','import json\ndef f(data):\n return json.loads(data)\n')
        self.assertEqual(self.call('python_ast',path=p)['flows'],[])

    def test_semantic_diff_ignores_whitespace_not_constants(self):
        a=self.write('a.py','def f(x):\n return x+1\n')
        b=self.write('b.py','# comment\ndef f(x):\n    return x + 1\n')
        self.assertEqual(self.call('semantic_diff',before=a,after=b)['label'],'unchanged')
        Path(b).write_text('def f(x):\n return x+2\n')
        self.assertIn('f',[r['symbol'] for r in self.call('semantic_diff',before=a,after=b)['changed']])

    def test_dependencies_ast_and_lock(self):
        p=self.write('a.py','import pickle\nfrom json import loads\n')
        self.assertEqual(len(self.call('dependencies',path=p)['dependencies']),2)
        p=self.write('package-lock.json',json.dumps({'packages':{'node_modules/a':{'version':'1.2.3'}}}))
        self.assertEqual(self.call('dependencies',path=p)['dependencies'][0]['version'],'1.2.3')

    def test_binary_elf_pe_macho_and_malformed(self):
        elf=bytearray(64);elf[:6]=b'\x7fELF\x02\x01';elf[18:20]=struct.pack('<H',62)
        pe=bytearray(160);pe[:2]=b'MZ';pe[60:64]=struct.pack('<I',80);pe[80:84]=b'PE\0\0'
        for fmt,data in [('ELF',elf),('PE',pe),('Mach-O',bytes.fromhex('cffaedfe')+b'\0'*24),('unknown',b'MZ')]:
            p=self.root/'bin';p.write_bytes(data)
            self.assertEqual(self.call('binary',path=str(p))['label'],fmt)

    def harness(self):
        return self.write('h.py','import sys\ns=sys.stdin.read()\nif "!" in s: raise ValueError("fixture")\nprint("ok")\n')

    def test_replay_fuzz_minimize_functionally(self):
        p=self.harness()
        self.assertEqual(self.call('replay',script=p,input='good')['label'],'clean')
        self.assertEqual(self.call('replay',script=p,input='!')['signature'],'ValueError')
        r=self.call('fuzz',script=p,seeds=['ok'],alphabet='!',seed=7,iterations=4)
        self.assertEqual(r['label'],'anomaly')
        r=self.call('minimize',script=p,input='abc!def')
        self.assertEqual(r['input'],'!')

    def test_dynamic_timeout_and_environment(self):
        p=self.write('hang.py','while True: pass\n')
        self.assertTrue(self.call('replay',script=p,input='',timeout=.1)['timeout'])
        p=self.write('env.py','import os\nassert "ANTHROPIC_API_KEY" not in os.environ\nprint("ok")\n')
        self.assertEqual(self.call('replay',script=p)['exit_code'],0)

    def test_compare_regression_control(self):
        a=self.harness();b=self.write('fixed.py','print("ok")\n')
        self.assertTrue(self.call('compare',before=a,after=b,input='!',control='valid')['regression_ok'])
        Path(b).write_text('print("regression")\n')
        self.assertFalse(self.call('compare',before=a,after=b,input='!',control='valid')['regression_ok'])

    def test_real_sanitizer_on_local_c_fixture(self):
        if not shutil.which('clang'):self.skipTest('BLOCKED clang absent')
        p=self.write('bad.c','#include <stdlib.h>\n#include <stdio.h>\nint main(void){int *p=malloc(sizeof(int)); volatile int i=3; p[i]=9; printf("%d\\n",p[i]); free(p);return 0;}\n')
        r=self.call('sanitizer',path=p)
        self.assertEqual(r['status'],'PASS',r)
        self.assertEqual(r['label'],'sanitizer_error',r)
        p=self.write('good.c','int main(void){return 0;}\n')
        r=self.call('sanitizer',path=p)
        self.assertEqual(r['label'],'clean',r)

    def test_protocol_role_and_state_violation(self):
        p=self.write('proto.py','import sys,json\na=json.load(sys.stdin)\nprint(json.dumps(["ok" if x=="login" else "denied" for x in a]))\n')
        r=self.call('protocol',script=p,traces=[dict(role='guest',steps=['read'],expected=['denied']),dict(role='user',steps=['login'],expected=['ok'])])
        self.assertEqual(r['label'],'transitions_valid')
        r=self.call('protocol',script=p,traces=[dict(steps=['read'],expected=['ok'])])
        self.assertEqual(r['mismatches'],[0])

    def test_sanitizer_timeout_is_not_reported_as_crash(self):
        if not shutil.which('clang'):self.skipTest('BLOCKED clang absent')
        p=self.write('hang.c','int main(void){for(;;){__asm__ volatile("");}}\n')
        r=self.call('sanitizer',path=p,timeout=.1)
        self.assertTrue(r['timeout'],r)
        self.assertEqual(r['label'],'timeout',r)

    def test_deserialization_actual_harmless_callback(self):
        p=self.write('callbacks.py','import pickle\nseen=[]\nclass Record:\n def __setstate__(self,state):\n  seen.append("marker")\nx=Record();x.a=1\npickle.loads(pickle.dumps(x))\nassert seen==["marker"]\n')
        r=self.call('deserialize_trace',script=p)
        self.assertEqual(r['exit_code'],0,r)
        self.assertTrue(any('__setstate__' in n for n in r['functions']),r)

    def test_optional_reverse_tools_have_real_smoke_tests(self):
        import sys
        local=self.root/'python';shutil.copyfile(sys.executable,local)
        for adapter,binname in [('radare2','r2'),('ghidra','analyzeHeadless')]:
            r=self.call(adapter,path=str(local))
            if shutil.which(binname):self.assertEqual(r['status'],'PASS',r)
            else:self.assertEqual(r['status'],'BLOCKED',r)

if __name__=='__main__':unittest.main()
