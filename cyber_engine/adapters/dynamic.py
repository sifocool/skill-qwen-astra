"""Bounded local execution on explicitly authorized harnesses.

No shell strings. Clean environment. These limits do not replace container/OS
isolation for hostile native code; the scope requires trusted_lab=True.
"""
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile


def run_process(argv, data=b"", timeout=3, cwd=None):
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG":"C", "LC_ALL":"C",
           "PYTHONDONTWRITEBYTECODE":"1", "PYTHONHASHSEED":"0", "ASAN_OPTIONS":"detect_leaks=0:symbolize=0",
           "TMPDIR":tempfile.gettempdir()}
    # Temporary files avoid unbounded PIPE memory. Child file-size and CPU limits
    # are set by a tiny exec wrapper, without unsafe preexec_fn in threaded clients.
    wrapper = Path(__file__).with_name("limited_exec.py")
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err, tempfile.TemporaryFile() as inp:
        inp.write(data); inp.seek(0)
        p = subprocess.Popen([sys.executable, str(wrapper), *map(str,argv)], stdin=inp,stdout=out,stderr=err,
                             cwd=cwd,env=env,start_new_session=True)
        timed_out = False
        try:
            p.wait(timeout=min(max(float(timeout),0.1),30))
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(p.pid,signal.SIGKILL)
            p.wait()
        out.seek(0); err.seek(0)
        stdout, stderr = out.read(32768),err.read(32768)
    # Stable signature deliberately excludes addresses and source temp paths.
    diagnostic = stderr.decode(errors="replace")
    match = re.search(r'(?:ERROR: AddressSanitizer:|runtime error:)\s*([^\n]+)', diagnostic)
    signature = re.sub(r'0x[0-9a-fA-F]+', '<addr>', match.group(1)).split(' on address')[0] if match else None
    exception = re.findall(r'^([A-Za-z_][\w.]*(?:Error|Exception)):', diagnostic, re.M)
    if exception and not signature:
        signature = exception[-1]
    return dict(exit_code=p.returncode, timeout=timed_out, stdout=stdout.decode(errors="replace"),
                stderr_sha256=hashlib.sha256(stderr).hexdigest(), signature=signature,
                **({"unclassified_diagnostic": diagnostic} if p.returncode and not signature else {}))


def trusted(scope):
    if scope.spec.get("trusted_lab") is not True:
        raise ValueError("dynamic execution needs an explicitly authorized trusted lab or external OS sandbox")


def replay(args, scope):
    trusted(scope)
    p = scope.path(args["script"])
    if p.suffix != ".py":
        raise ValueError("replay expects a Python stdin harness")
    data = args.get("input", "").encode()
    if len(data) > 65536:
        raise ValueError("input too large")
    r = run_process([sys.executable,"-I",p], data, args.get("timeout",3), p.parent)
    label = "timeout" if r["timeout"] else "crash" if r["exit_code"] else "clean"
    # stdout may carry a harness's explicit observable label, never arbitrary code.
    if r["exit_code"] == 0:
        try:
            parsed = json.loads(r["stdout"])
            if isinstance(parsed,dict) and isinstance(parsed.get("label"),str):
                label = parsed["label"]
        except ValueError:
            pass
    return dict(status="PASS", label=label, **r)


def compare(args, scope):
    records = []
    for key in ("before","after"):
        records.append([replay(dict(script=args[key],input=x),scope) for x in (args["input"],args["control"])])
    b,a = records
    if any(r["timeout"] for pair in records for r in pair):
        return dict(status="PASS", label="inconclusive", regression_ok=False, versions=records)
    observable = lambda r:(r["exit_code"],r["stdout"],r["signature"])
    differs = observable(b[0]) != observable(a[0])
    control_ok = observable(b[1]) == observable(a[1]) and b[1]["exit_code"] == 0
    fixed_ok = a[0]["exit_code"] == 0 and a[0]["label"] == args.get("expected_after", "clean")
    ok = differs and control_ok and fixed_ok
    return dict(status="PASS",label="fixed" if ok else "not_fixed",regression_ok=ok,versions=records)


def fuzz(args, scope):
    trusted(scope)
    seed = int(args.get("seed",0)); rng = random.Random(seed)
    budget = int(args.get("iterations",64))
    if not 1 <= budget <= 256:
        raise ValueError("iterations must be 1..256")
    corpus = args.get("seeds", ["", "0", "{}"])
    if not isinstance(corpus,list) or not corpus or any(not isinstance(s,str) or len(s)>4096 for s in corpus):
        raise ValueError("bounded text seed corpus required")
    alphabet = args.get("alphabet", "0123456789{}[]:/\\\"-+abc")
    if not alphabet or len(alphabet)>256:
        raise ValueError("bounded nonempty alphabet required")
    crashes = []
    for i in range(budget):
        value = corpus[i] if i < len(corpus) else rng.choice(corpus)
        if i >= len(corpus):
            pos = rng.randrange(len(value)+1)
            value = value[:pos]+rng.choice(alphabet)+value[pos:]
        r = replay(dict(script=args["script"],input=value,timeout=min(args.get("timeout",0.5),0.5)),scope)
        if r["label"] in ("crash","timeout"):
            crashes.append(dict(input=value, signature=r["signature"], label=r["label"]))
    return dict(status="PASS",label="anomaly" if crashes else "no_anomaly", seed=seed,
                iterations=budget, anomalies=crashes, coverage_measured=False)


def minimize(args, scope):
    value = args["input"]
    base = replay(dict(script=args["script"],input=value),scope)
    if base["label"] != "crash" or not base["signature"]:
        raise ValueError("minimize requires a reproducible exception/sanitizer signature")
    signature = base["signature"]; trials=0; width=max(1,len(value)//2)
    while width and trials < 100:
        changed = False
        for start in range(0,len(value),width):
            candidate = value[:start]+value[start+width:]
            r = replay(dict(script=args["script"],input=candidate),scope); trials+=1
            if r["label"] == "crash" and r["signature"] == signature:
                value=candidate;changed=True;break
            if trials>=100: break
        if not changed: width//=2
    return dict(status="PASS",label="minimized",input=value,signature=signature,trials=trials,
                limitation="same exception class is provisional identity; confirm stack/root cause manually")


def sanitizer(args, scope):
    trusted(scope)
    cc=shutil.which("clang")
    if not cc:
        return dict(status="BLOCKED", label="unavailable",reason="clang missing")
    p=scope.path(args["path"])
    with tempfile.TemporaryDirectory(prefix="astra-asan-") as d:
        binary=Path(d)/"probe"
        c=run_process([cc,"-g","-O1","-fsanitize=address,undefined","-fno-omit-frame-pointer",p,"-o",binary],timeout=30)
        if c["exit_code"]:
            return dict(status="BLOCKED",label="build_failed",build=c)
        # A newly linked instrumented binary may take several seconds to start.
        # This is a bounded allowance, not a retry that hides failed executions.
        r=run_process([binary],args.get("input","").encode(),args.get("timeout",10))
    return dict(status="PASS",label="timeout" if r["timeout"] else "sanitizer_error" if r["signature"] else "clean" if r["exit_code"]==0 else "unclassified_crash",
                exit_code=r["exit_code"],signature=r["signature"],stdout=r["stdout"],timeout=r["timeout"],
                **({"unclassified_diagnostic": r["unclassified_diagnostic"]}
                   if "unclassified_diagnostic" in r else {}))


def deserialize_trace(args, scope):
    # Instrument a supplied harmless stdin harness. Never accepts a pickle payload
    # to execute in this process; calls are observed by Python's trace module.
    trusted(scope)
    p=scope.path(args["script"])
    tracer=Path(__file__).with_name("trace_exec.py")
    r=run_process([sys.executable,"-I",tracer,p],args.get("input","").encode(),3,p.parent)
    functions=[]
    for line in r["stdout"].splitlines():
        if line.startswith('ASTRA_TRACE='):
            functions=json.loads(line[len('ASTRA_TRACE='):])
    return dict(status="PASS",label="trace_failed" if r['exit_code'] else "callbacks_observed" if functions else "no_callbacks",
                functions=sorted(set(functions)),exit_code=r["exit_code"],timeout=r["timeout"],
                limitation="observed calls in this harness, not arbitrary dependency reachability")
