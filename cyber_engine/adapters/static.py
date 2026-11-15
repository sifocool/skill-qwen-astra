"""Conservative Python AST hints and artifact analysis; never an exploit verdict."""
import ast
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path


def name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return name(node.value) + "." + node.attr
    return "<dynamic>"


def python_ast(args, scope):
    path = scope.path(args["path"])
    tree = ast.parse(path.read_text())
    sinks = set(args.get("sinks", ["eval", "exec", "pickle.loads", "pickle.load", "yaml.load", "subprocess.run", "os.system"]))
    aliases = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            aliases.update({a.asname or a.name: a.name for a in n.names})
        elif isinstance(n, ast.ImportFrom):
            aliases.update({a.asname or a.name: (n.module or "") + "." + a.name for a in n.names})
    findings, calls, callbacks = [], [], []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        tainted = {a.arg for a in fn.args.args + fn.args.posonlyargs + fn.args.kwonlyargs}
        # Monotone fixed point intentionally over-approximates branches/loops.
        # No claim of path sensitivity, sanitizer correctness or interprocedural flow.
        nodes = list(ast.walk(fn))
        for _ in range(len(nodes) + 1):
            old = set(tainted)
            for n in nodes:
                if isinstance(n, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and n.value is not None:
                    if any(isinstance(x, ast.Name) and x.id in tainted for x in ast.walk(n.value)):
                        targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                        tainted.update(x.id for t in targets for x in ast.walk(t) if isinstance(x, ast.Name))
            if old == tainted:
                break
        if fn.name in ("__reduce__", "__reduce_ex__", "__setstate__", "__getattr__", "__call__"):
            callbacks.append(dict(name=fn.name, line=fn.lineno))
        for n in nodes:
            if not isinstance(n, ast.Call):
                continue
            callee = name(n.func)
            head, *tail = callee.split(".")
            callee = ".".join([aliases.get(head, head)] + tail)
            calls.append(dict(caller=fn.name, callee=callee, line=n.lineno))
            source_args = n.args + [k.value for k in n.keywords]
            sources = sorted({x.id for a in source_args for x in ast.walk(a) if isinstance(x, ast.Name) and x.id in tainted})
            if callee in sinks and sources:
                findings.append(dict(path=str(path), line=n.lineno, function=fn.name,
                                     sink=callee, sources=sources, status="candidate"))
    return dict(status="PASS", label="candidate_flow" if findings else "no_candidate_flow",
                flows=findings, calls=calls, callbacks=callbacks,
                limitations=["Python only", "flow-insensitive intraprocedural over-approximation",
                             "nested functions may over-approximate scope", "absence is not safety proof"])


def semantic_diff(args, scope):
    def symbols(path):
        tree = ast.parse(scope.path(path).read_text())
        result = {}
        def walk(node, prefix=""):
            for n in ast.iter_child_nodes(node):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    key = prefix + n.name
                    result[key] = dict(ast=ast.dump(n, include_attributes=False), line=n.lineno)
                    walk(n, key + ".")
                else:
                    walk(n, prefix)
        walk(tree)
        result["<module>"] = dict(ast=ast.dump(tree, include_attributes=False), line=1)
        return result
    old, new = symbols(args["before"]), symbols(args["after"])
    changed = [dict(symbol=k, before_line=old.get(k, {}).get("line"), after_line=new.get(k, {}).get("line"))
               for k in sorted(set(old) | set(new)) if old.get(k, {}).get("ast") != new.get(k, {}).get("ast")]
    return dict(status="PASS", label="changed" if changed else "unchanged", changed=changed,
                limitation="AST structural comparison, not semantic equivalence; comments ignored, literals retained")


def dependencies(args, scope):
    p = scope.path(args["path"])
    if p.suffix == ".py":
        items = []
        for n in ast.walk(ast.parse(p.read_text())):
            if isinstance(n, ast.Import):
                items.extend(dict(name=a.name, line=n.lineno) for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                items.append(dict(name=n.module, level=n.level, line=n.lineno))
        return dict(status="PASS", label="imports", dependencies=items, resolved_versions=False)
    data = json.loads(p.read_text())
    packages = data.get("packages", {})
    return dict(status="PASS", label="lockfile", dependencies=[dict(path=k, version=v.get("version"),
        integrity=v.get("integrity"), dependencies=v.get("dependencies", {})) for k,v in sorted(packages.items())],
        resolved_versions=True, limitation="npm package-lock packages; loaded runtime not inferred")


def binary(args, scope):
    p = scope.path(args["path"])
    raw = p.read_bytes()
    fmt, details = "unknown", {}
    if raw.startswith(b"\x7fELF") and len(raw) >= 20:
        fmt = "ELF"
        endian = "<" if raw[5] == 1 else ">"
        details = dict(bits={1:32,2:64}.get(raw[4]), machine=struct.unpack(endian+"H", raw[18:20])[0])
    elif raw.startswith(b"MZ") and len(raw) >= 64:
        off = int.from_bytes(raw[60:64], "little")
        if raw[off:off+4] == b"PE\x00\x00" and len(raw) >= off+24:
            fmt = "PE"
            details = dict(machine=int.from_bytes(raw[off+4:off+6], "little"), sections=int.from_bytes(raw[off+6:off+8], "little"))
    elif raw[:4] in [bytes.fromhex(x) for x in ["feedface","cefaedfe","feedfacf","cffaedfe","cafebabe","bebafeca"]]:
        fmt = "Mach-O"
        details = dict(magic=raw[:4].hex())
    return dict(status="PASS", label=fmt, sha256=hashlib.sha256(raw).hexdigest(), size=len(raw), **details)


def external(args, scope, tool):
    binary_path = scope.path(args["path"])
    executable = scope.spec.get('tools',{}).get(tool) or shutil.which("r2" if tool == "radare2" else "analyzeHeadless")
    if not executable:
        return dict(status="BLOCKED", label="unavailable", reason=tool + " is not installed")
    if tool == "radare2":
        p = subprocess.run([executable, "-2", "-q", "-c", "ij", str(binary_path)], capture_output=True, timeout=30)
        info = json.loads(p.stdout)
        if p.returncode or not info.get("bin"):
            raise ValueError("radare2 did not return binary metadata")
        return dict(status="PASS", label="binary_metadata", info=info["bin"])
    # Headless analysis in a disposable project. Import has no custom scripts.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="astra-ghidra-") as d:
        p = subprocess.run([executable,d,"astra","-import",str(binary_path),"-deleteProject"],
                           capture_output=True, timeout=120)
        text = (p.stdout+p.stderr).decode(errors="replace")
        if p.returncode or "ANALYZING" not in text:
            raise ValueError("Ghidra analysis not confirmed")
        return dict(status="PASS", label="analyzed", output_sha256=hashlib.sha256(p.stdout+p.stderr).hexdigest())
