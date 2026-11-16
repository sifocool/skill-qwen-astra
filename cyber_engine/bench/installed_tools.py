"""Exercise the installed CLI and native tool bindings on a harmless local binary."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def check(profile, python):
    launcher = Path(profile).resolve() / 'astra-runtime/run.py'
    with tempfile.TemporaryDirectory(prefix='astra-installed-tools-') as d:
        root = Path(d)
        def call(action, payload=None):
            r = subprocess.run([python, str(launcher), action, json.dumps(payload or {})],
                               cwd=root, capture_output=True, text=True, timeout=150)
            if r.returncode:
                raise RuntimeError(r.stdout[-1000:] + r.stderr[-1000:])
            return json.loads(r.stdout)
        routed = call('route', {'question': 'compare binary versions'})
        assert not (root / '.astra').exists(), 'read-only route created state'
        source = root / 'fixture.c'
        source.write_text('int add(int a,int b){return a+b;}\nint main(void){return add(1,2)==3?0:1;}\n')
        compiler = shutil.which('clang')
        if not compiler:
            return dict(status='BLOCKED', reason='clang missing for native smoke fixture')
        binary = root / 'fixture'
        subprocess.run([compiler, '-g', str(source), '-o', str(binary)], check=True, timeout=30,
                       capture_output=True)
        call('init', dict(question='Do installed native adapters actually analyze this local fixture?',
             scope=dict(authorization='user requested installation validation; generated harmless binary only',
                        roots=[d], adapters=['radare2', 'ghidra'], trusted_lab=True)))
        h1 = call('hypothesis', dict(claim='native adapter analyzes the fixture'))
        h2 = call('hypothesis', dict(claim='native adapter is unavailable'))
        results = {}
        for adapter, label in [('radare2', 'binary_metadata'), ('ghidra', 'analyzed')]:
            call('plan', dict(adapter=adapter, args=dict(path=str(binary)),
                 predictions={h1:label, h2:'unavailable'}, purpose='exercise installed native binding'))
            result = call('run-next')
            assert result['selection']['skill'] == 'patch-diffing', result
            assert result['result']['status'] == 'PASS' and result['result']['label'] == label, result
            results[adapter] = result
        call('stop', dict(reason='installation checks executed; no vulnerability conclusion',
                          uncertainties=['native metadata analysis does not prove program security']))
        return dict(status='PASS', invocation='installed run.py; no per-investigation tool overrides',
                    read_only_route_created_state=False, route=routed,
                    fixture_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(), results=results)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--profile', required=True)
    p.add_argument('--python', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    result = check(args.profile, args.python)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
