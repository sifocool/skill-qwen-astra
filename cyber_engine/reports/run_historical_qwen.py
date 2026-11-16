"""Separate historical calibration, never included in the 20 unseen local cases.

Run after the main campaign to avoid concurrent load on the model server.
The executed octet parser method is copied verbatim from pinned CPython sources.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from cyber_engine.bench.client import Client
from cyber_engine.bench.run import solve,summarize


def cases():
    vendor=Path(__file__).resolve().parents[1]/'bench/vendor/cpython'
    def extracted(version):
        text=(vendor/('ipaddress-'+version+'.py')).read_text()
        node=next(n for n in ast.walk(ast.parse(text)) if isinstance(n,ast.FunctionDef) and n.name=='_parse_octet')
        lines=text.splitlines(keepends=True)
        method=''.join(lines[node.lineno-2:node.end_lineno])
        return 'class Parser:\n'+method+'\ndef solve(x):\n    try: return Parser._parse_octet(x)\n    except ValueError: return None\n'
    before,after=extracted('old'),extracted('new')
    contract='Known patch invariant: parse a string representing one IPv4 decimal octet. Return integer 0..255 only for 1..3 ASCII digits with no leading zero except the single string "0". Reject everything else by returning null.'
    return [dict(id='H01',family='historical-ipaddress',contract=contract,source=before,reference=after,bug=True,
                 root_line=before[:before.index('octet_int = int')].count('\n')+1,witness='010',control='10',domain=['010','10'],
                 source_sha256=hashlib.sha256(before.encode()).hexdigest()),
            dict(id='H02',family='historical-ipaddress-patched',contract=contract,source=after,reference=after,bug=False,
                 root_line=None,witness=None,control='10',domain=['0','10','255','256','00','01','','-1','a','١'],
                 source_sha256=hashlib.sha256(after.encode()).hexdigest())]


if __name__=='__main__':
    os.umask(0o077)
    output=Path(sys.argv[1]);output.mkdir(mode=0o700,parents=True,exist_ok=False)
    client=Client();items=cases()
    (output/'manifest.json').write_text(json.dumps(dict(model=client.model,cases=[dict(id=c['id'],source_sha256=c['source_sha256']) for c in items],
        category='public historical calibration, excluded from unseen count',source='CPython 3.9.4/3.9.5 _parse_octet, method verbatim, wrapper added'),indent=2))
    results=[]
    for i,case in enumerate(items):
        for condition in (['baseline','enhanced'] if i==0 else ['enhanced','baseline']):
            r=solve(client,case,condition,output);results.append(r)
            print(json.dumps({k:r[k] for k in ['case','condition','evaluation','usage','seconds','error']}),flush=True)
    (output/'summary.json').write_text(json.dumps(summarize(results),indent=2))
