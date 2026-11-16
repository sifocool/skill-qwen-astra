"""Execute unmodified CPython 3.9.4/3.9.5 module snapshots, not recreated bugs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from ..adapters import execute
from ..scope import Scope


def verify():
    root=Path(__file__).with_name('vendor')/'cpython'
    results=[]
    for family,method,witness,control,expected_fixed in [
            ('ipaddress','str(m.IPv4Address(value))','010.0.0.1','10.0.0.1',True),
            ('parse','m.urlsplit(value).hostname','https://exa\nmple.invalid/','https://example.invalid/',True),
            # Keep the initially failed verification: 3.9.5 sanitizes after scheme extraction.
            ('parse','m.urlsplit(value).scheme','ht\ntps://example.invalid/','https://example.invalid/',False)]:
        with tempfile.TemporaryDirectory(prefix='astra-historical-') as d:
            d=Path(d)
            for version in ['old','new']:
                # Whole pinned module is loaded, no patched/reconstructed implementation.
                module=root/(family+'-'+version+'.py')
                (d/(version+'.py')).write_text('import importlib.util,json,sys\n'+
                    's=importlib.util.spec_from_file_location("historical",'+repr(str(module))+')\n'+
                    'm=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nvalue=sys.stdin.read()\n'+
                    'try:\n result='+method+'\nexcept ValueError:\n result="rejected"\n'+
                    'print(json.dumps({"label":"clean","result":result},sort_keys=True))\n')
            scope=Scope(dict(authorization='local historical parser replay',roots=[str(d)],adapters=['compare'],trusted_lab=True))
            args=dict(before='old.py',after='new.py',input=witness,control=control)
            runs=[execute('compare',args,scope) for _ in range(3)]
            assert all(r['regression_ok']==expected_fixed for r in runs),runs
            assert runs[0]==runs[1]==runs[2]
            results.append(dict(family=family,status='PASS',expected_fixed=expected_fixed,repeat='3/3',result=runs[0],
                snapshots={v:hashlib.sha256((root/(family+'-'+v+'.py')).read_bytes()).hexdigest() for v in ['old','new']},
                limitation='historical modules run under current Python, not full historical interpreter builds',
                finding='before/after and valid control verified' if expected_fixed else 'initial 3.9.5 patch does not normalize scheme before parsing; retained negative result'))
    return dict(status='PASS',cases=results,provenance=json.loads((root/'provenance.json').read_text()))


if __name__=='__main__':print(json.dumps(verify(),indent=2))
