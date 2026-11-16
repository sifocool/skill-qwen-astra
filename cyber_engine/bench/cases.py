"""New local diagnosis tasks. Oracle and mutation metadata never enter model context.

Twenty tasks, five families, fifteen defects and five negative controls. These
are synthetic programs, not CyberGym tasks or twenty independent real CVEs.
"""
import hashlib
import json
from pathlib import Path
import textwrap


def make_case(cid,family,contract,source,old=None,new=None,witness=None,control=None,domain=None):
    source=textwrap.dedent(source.replace('\n        ','\n')).strip()+'\n'
    reference=source.replace(old,new,1) if old is not None else source
    assert old is None or source.count(old)==1,(cid,old)
    root_line=source[:source.index(old)].count('\n')+1 if old is not None else None
    return dict(id=cid,family=family,contract=contract,source=source,reference=reference,
                bug=old is not None,root_line=root_line,witness=witness,control=control,
                domain=domain or [control,witness],source_sha256=hashlib.sha256(source.encode()).hexdigest())


def holdout():
    return [
      make_case('L01','authorization','Input has tenant, owner_tenant and role. Grant only when the tenant matches AND role is exactly editor.',
        '''def solve(x):
            same = x['tenant'] == x['owner_tenant']
            return same or x['role'] == 'editor'
        ''','same or','same and',dict(tenant='a',owner_tenant='b',role='editor'),dict(tenant='a',owner_tenant='a',role='editor')),
      make_case('L02','authorization','roles is a list of exact role names. Grant only if admin is an element.',
        '''def solve(x):
            roles = ','.join(x['roles'])
            return 'admin' in roles
        ''',"roles = ','.join(x['roles'])","roles = x['roles']",dict(roles=['notadmin']),dict(roles=['admin'])),
      make_case('L03','authorization','An explicit deny overrides all grants. Otherwise grant if any ACL record for the same user has allow=true.',
        '''def solve(x):
            for rule in x['acl']:
                if rule['user'] == x['user'] and rule['allow']:
                    return True
            return False
        ''',"for rule in x['acl']:","if any(r['user'] == x['user'] and not r['allow'] for r in x['acl']): return False\n    for rule in x['acl']:",
        dict(user='u',acl=[dict(user='u',allow=True),dict(user='u',allow=False)]),dict(user='u',acl=[dict(user='u',allow=True)])),
      make_case('L04','authorization','Only matching tenant and exact admin role grant access; all other inputs return false.',
        '''def solve(x):
            return x['tenant']==x['owner_tenant'] and x['role']=='admin'
        ''',control=dict(tenant='a',owner_tenant='a',role='admin'),domain=[dict(tenant=a,owner_tenant=b,role=r) for a in ['a','b'] for b in ['a','b'] for r in ['admin','user','notadmin']]),
      make_case('L05','bounds','items is a nonempty list, index is an integer. Return items[index] only for 0 <= index < len(items); otherwise return null.',
        '''def solve(x):
            i=x['index']; items=x['items']
            if i < len(items):
                return items[i]
            return None
        ''','if i < len(items):','if 0 <= i < len(items):',dict(items=[4,7],index=-1),dict(items=[4,7],index=0)),
      make_case('L06','bounds','Return true only for integer count in [0,1024] when count*width <= 4096. width is an integer in [1,65536]. Arithmetic must not wrap.',
        '''def solve(x):
            total=(x['count']*x['width']) & 65535
            return 0 <= x['count'] <= 1024 and total <= 4096
        ''',"total=(x['count']*x['width']) & 65535","total=x['count']*x['width']",dict(count=1024,width=64),dict(count=2,width=8)),
      make_case('L07','bounds','Input is a string. Accept when UTF-8 encoded size is at most 8 bytes.',
        '''def solve(x):
            return len(x) <= 8
        ''','len(x)','len(x.encode("utf-8"))','ééééé','abc'),
      make_case('L08','bounds','Return the requested slice only when 0 <= start <= end <= len(items), else null. start/end are integers.',
        '''def solve(x):
            a,b=x['start'],x['end']
            return x['items'][a:b] if 0<=a<=b<=len(x['items']) else None
        ''',control=dict(items=[1,2],start=0,end=1),domain=[dict(items=[1,2],start=a,end=b) for a in [-1,0,1,2,3] for b in [-1,0,1,2,3]]),
      make_case('L09','canonicalization','Decode percent escapes once, then accept paths having no slash-separated component equal to ..; return decoded path if accepted, null otherwise.',
        '''from urllib.parse import unquote
        def solve(x):
            if '..' in x.split('/'):
                return None
            return unquote(x)
        ''',"if '..' in x.split('/'):","if '..' in unquote(x).split('/'):",'%2e%2e/file','docs/a'),
      make_case('L10','canonicalization','Compare hostname to example.test case-insensitively after removing at most one trailing dot. No subdomains, superdomains, or userinfo accepted.',
        '''def solve(x):
            host=x.lower().removesuffix('.')
            return host.endswith('example.test')
        ''',"host.endswith('example.test')","host == 'example.test'",'evilexample.test','EXAMPLE.TEST.'),
      make_case('L11','canonicalization','A request contains a list of Content-Length strings. Return their common nonnegative decimal value if all parsed values agree. Empty, negative or conflicting values return null.',
        '''def solve(x):
            try: values=[int(s) for s in x]
            except (TypeError,ValueError): return None
            if not values or any(v<0 for v in values): return None
            return values[0]
        ''','return values[0]','return values[0] if len(set(values))==1 else None',['2','9'],['2','02']),
      make_case('L12','canonicalization','Percent decode exactly once, reject any .. component, otherwise return decoded path. Double-encoded .. remains encoded and is allowed.',
        '''from urllib.parse import unquote
        def solve(x):
            p=unquote(x)
            return None if '..' in p.split('/') else p
        ''',control='a/b',domain=['a/b','../x','%2e%2e/x','%252e%252e/x','a/../b','a%2fb','..x','']),
      make_case('L13','state','Operations are login, logout, read. Start unauthenticated. login authenticates, logout revokes, read returns current auth boolean. Return only read results.',
        '''def solve(x):
            auth=False; cached=None; out=[]
            for op in x:
                if op=='login': auth=True
                elif op=='logout': auth=False
                elif op=='read':
                    if cached is None: cached=auth
                    out.append(cached)
            return out
        ''','out.append(cached)','out.append(auth)',['login','read','logout','read'],['login','read']),
      make_case('L14','state','Operations are dictionaries with tenant and key. Return the string tenant:key for each operation; cached values must never cross tenants.',
        '''def solve(x):
            cache={}; out=[]
            for r in x:
                key=r['key']
                if key not in cache: cache[key]=r['tenant']+':'+r['key']
                out.append(cache[key])
            return out
        ''',"key=r['key']","key=(r['tenant'],r['key'])",[dict(tenant='a',key='k'),dict(tenant='b',key='k')],[dict(tenant='a',key='k')]),
      make_case('L15','state','login with ok=true authenticates; ANY login with ok=false revokes previous authentication. read returns current auth state. Start false.',
        '''def solve(x):
            auth=False; out=[]
            for r in x:
                if r['op']=='login' and r['ok']: auth=True
                elif r['op']=='read': out.append(auth)
            return out
        ''',"if r['op']=='login' and r['ok']: auth=True","if r['op']=='login': auth=bool(r['ok'])",[dict(op='login',ok=True),dict(op='login',ok=False),dict(op='read')],[dict(op='login',ok=True),dict(op='read')]),
      make_case('L16','state','A one-time nonce can succeed once. use marks it used; repeat use returns false. peek returns whether unused and must not consume it. Return a boolean for every operation.',
        '''def solve(x):
            used=False; out=[]
            for op in x:
                out.append(not used)
                if op=='use': used=True
            return out
        ''',control=['peek','use'],domain=[[],['use'],['peek'],['peek','peek','use','use'],['use','peek','use']]),
      make_case('L17','deserialization','Input is JSON object with type and payload_type strings. Only type=record AND payload_type=record may invoke marker; return true for marker, false otherwise.',
        '''def solve(x):
            allowed=x['type']=='record'
            dispatch=x['payload_type']
            return allowed or dispatch=='record'
        ''',"allowed or dispatch=='record'","allowed and dispatch=='record'",dict(type='record',payload_type='callback'),dict(type='record',payload_type='record')),
      make_case('L18','deserialization','Input has count. Accept exact JSON integers 0..4; reject booleans, strings and floats. Do not coerce types.',
        '''def solve(x):
            n=x['count']
            return isinstance(n,int) and 0<=n<=4
        ''','isinstance(n,int)','type(n) is int',dict(count=True),dict(count=2)),
      make_case('L19','deserialization','Input has verified boolean and callback boolean. If unverified, no callback may run. Return number of harmless marker callbacks executed (0 or 1).',
        '''def solve(x):
            markers=int(x['callback'])
            if not x['verified']: return markers
            return markers
        ''',"if not x['verified']: return markers","if not x['verified']: return 0",dict(verified=False,callback=True),dict(verified=True,callback=True)),
      make_case('L20','deserialization','Input is a list of type names. Return true only when every element is exactly record; empty list is valid. No implicit subtype accepted.',
        '''def solve(x):
            return all(type(t) is str and t=='record' for t in x)
        ''',control=['record'],domain=[[],['record'],['record','record'],['callback'],['record','callback'],['Record'],[True],[None]]),
    ]


def development():
    return [
      make_case('D01','authorization','Grant only when authenticated=true and owner=true.',
        'def solve(x):\n return x["authenticated"] or x["owner"]',
        'or','and',dict(authenticated=True,owner=False),dict(authenticated=True,owner=True)),
      make_case('D02','bounds','Accept byte length at most 3. Input is list of integers.',
        'def solve(x):\n return len(x)<3','<3','<=3',[1,2,3],[1]),
      make_case('D03','state','Start locked. unlock clears lock, reset sets it. Return locked boolean after all operations.',
        '''def solve(x):
            locked=True
            for op in x:
                if op=='unlock': locked=False
            return locked
        ''',"if op=='unlock': locked=False","if op=='unlock': locked=False\n        elif op=='reset': locked=True",['unlock','reset'],['unlock']),
      make_case('D04','deserialization','Accept count only if exact int from 0 to 3 inclusive; booleans invalid.',
        'def solve(x):\n return type(x) is int and 0<=x<=3',control=2,domain=[False,True,-1,0,3,4,'2',2.0]),
    ]


def materialize(case,directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=True)
    (root/'subject.py').write_text(case['source'])
    (root/'reference.py').write_text(case['reference'])
    # This harness is evaluator-controlled, not exposed by the model's read tool.
    (root/'probe.py').write_text('''import importlib.util,json,pathlib,sys
root=pathlib.Path(__file__).parent
def load(n):
 s=importlib.util.spec_from_file_location(n,root/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
x=json.load(sys.stdin)
def result(fn):
 try:return {'value':fn(x)}
 except Exception as e:return {'error':type(e).__name__}
a=result(load('subject').solve);b=result(load('reference').solve)
print(json.dumps({'label':'conformant' if a==b else 'violation','actual':a},sort_keys=True))
''')
    return root
