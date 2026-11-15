"""An experiment ledger and a transparent expected-partition selector.

Probabilities are declared planning assumptions, never measured confidence.
Adapters produce observations; hypotheses cannot manufacture evidence.
"""
import math
import time
import uuid
import subprocess
import re
from .store import Store, digest
from .scope import Scope

SKILLS = {
    "python_ast": "gadget-deserialization", "dependencies": "gadget-deserialization",
    "deserialize_trace": "gadget-deserialization", "semantic_diff": "patch-diffing",
    "compare": "patch-diffing", "binary": "patch-diffing",
    "ghidra": "patch-diffing", "radare2": "patch-diffing",
    "replay": "fuzz-crash-triage", "fuzz": "fuzz-crash-triage",
    "minimize": "fuzz-crash-triage", "sanitizer": "fuzz-crash-triage",
    "http_probe": "blackbox-recon", "protocol": "blackbox-recon",
}


def route(question):
    """Initial capability choice uses only visible task text, never benchmark labels."""
    q=question.lower()
    for skill,pattern in [
        ('gadget-deserialization',r'deserial|callback|pickle|type names|payload_type|exact json|reconstruct'),
        ('patch-diffing',r'patch|before.?after|versions|percent|decode|hostname|canonical'),
        ('blackbox-recon',r'tenant|role|auth|login|logout|nonce|endpoint|acl|operations'),
        ('fuzz-crash-triage',r'crash|byte|length|count|index|slice|parse|integer|size')]:
        if re.search(pattern,q):return dict(skill=skill,reason='visible task terms match '+pattern)
    return dict(skill='blackbox-recon',reason='unknown surface: start with observable contract')


class Engine:
    def __init__(self, directory):
        self.store = Store(directory)

    def init(self, scope, question, max_experiments=30):
        Scope(scope)
        if not question or not 1 <= max_experiments <= 500:
            raise ValueError("question and bounded budget required")
        with self.store.db:
            if self.store.db.execute("SELECT 1 FROM state").fetchone():
                raise ValueError("already initialized")
            s = dict(schema=2, id=str(uuid.uuid4()), question=question, scope=scope,
                     observations=[], hypotheses={}, experiments={}, rejected=[], uncertainties=[],
                     challenges=[], status="ACTIVE", max_experiments=max_experiments,
                     created=time.time(), conclusion=None)
            self.store.save(s, "init")
        return s

    def change(self, event, fn):
        # BEGIN IMMEDIATE makes concurrent CLI updates serializable.
        self.store.db.execute("BEGIN IMMEDIATE")
        try:
            s = self.store.load()
            out = fn(s)
            self.store.save(s, event)
            self.store.db.commit()
            return out
        except BaseException:
            self.store.db.rollback()
            raise

    def observe(self, note, locations=None):
        def apply(s):
            locs = []
            for loc in locations or []:
                p = Scope(s["scope"]).path(loc["path"])
                start, end = loc["start"], loc.get("end", loc["start"])
                if not 1 <= start <= end <= len(p.read_text().splitlines()):
                    raise ValueError("invalid source lines")
                locs.append(dict(path=str(p), start=start, end=end,
                                 sha256=Scope(s["scope"]).fingerprint({"path": str(p)})[str(p)]))
            entry = dict(note=note, locations=locs, kind="unverified_observation")
            s["observations"].append(entry)
            return entry
        return self.change("observation", apply)

    def hypothesis(self, claim, prior=1):
        def apply(s):
            if not claim or not math.isfinite(prior) or prior <= 0:
                raise ValueError("claim and positive finite planning weight required")
            for h, v in s["hypotheses"].items():
                if v["claim"] == claim:
                    return h
            hid = "H" + str(len(s["hypotheses"]) + 1)
            s["hypotheses"][hid] = dict(claim=claim, prior=prior, status="open", evidence=[])
            return hid
        return self.change("hypothesis", apply)

    def plan(self, adapter, args, predictions, purpose, cost=1, kind="discriminate"):
        def apply(s):
            scope = Scope(s["scope"])
            scope.adapter(adapter)
            if adapter not in SKILLS or kind not in ("discriminate", "control", "regression", "explore"):
                raise ValueError("unknown adapter or experiment kind")
            if not purpose or not math.isfinite(cost) or cost <= 0:
                raise ValueError("purpose and finite positive cost required")
            if any(h not in s["hypotheses"] or not isinstance(v, str) or not v for h, v in predictions.items()):
                raise ValueError("predictions must map known hypotheses to observable labels")
            inputs = scope.fingerprint(args)
            key = digest(dict(adapter=adapter, args=args, inputs=inputs))
            for eid, e in s["experiments"].items():
                if e["key"] == key:
                    return dict(id=eid, duplicate=True)
            eid = "E" + str(len(s["experiments"]) + 1)
            s["experiments"][eid] = dict(adapter=adapter, skill=SKILLS[adapter], args=args,
                predictions=predictions, purpose=purpose, cost=cost, kind=kind,
                inputs=inputs, key=key, status="pending", evidence=[], results=[])
            s["status"] = "ACTIVE"
            return dict(id=eid, duplicate=False)
        return self.change("plan", apply)

    def select(self):
        s = self.store.load()
        executed = sum(len(e["results"]) for e in s["experiments"].values())
        if executed >= s["max_experiments"]:
            return dict(action="stop", reason="experiment budget exhausted", status="PARTIAL")
        open_h = {h: v for h, v in s["hypotheses"].items() if v["status"] == "open"}
        ranked = []
        for eid, e in s["experiments"].items():
            if e["status"] != "pending":
                continue
            predicted = {h: e["predictions"][h] for h in open_h if h in e["predictions"]}
            groups = {}
            total = sum(h["prior"] for h in open_h.values())
            for h, v in open_h.items():
                label = predicted.get(h, "__unpredicted__")
                groups[label] = groups.get(label, 0) + v["prior"]
            # Missing predictions do not count as an informative partition.
            gain = 0.0
            if total and len(predicted) == len(open_h):
                gain = -sum((w/total) * math.log2(w/total) for w in groups.values())
            bonus = 0.25 if e["kind"] in ("control", "regression") else 0
            if e["kind"] == "explore" and not s["observations"]:
                bonus = 0.1
            if gain + bonus > 0:
                ranked.append(dict(id=eid, skill=e["skill"], score=(gain+bonus)/e["cost"],
                                   partition_bits=gain, purpose=e["purpose"]))
        ranked.sort(key=lambda e: (-e["score"], e["id"]))
        if ranked:
            return dict(action="run", **ranked[0], alternatives=ranked[1:3])
        return dict(action="stop", reason="no pending experiment distinguishes live hypotheses or checks a control",
                    status="PARTIAL" if open_h else "REVIEW")

    def run(self, eid, repeat=False):
        from .adapters import execute
        # Keep lock through bounded execution to prevent double execution.
        def apply(s):
            e = s["experiments"][eid]
            if e["status"] != "pending" and not repeat:
                raise ValueError("already executed; request explicit repeat")
            if sum(len(v["results"]) for v in s["experiments"].values()) >= s["max_experiments"]:
                raise ValueError("experiment budget exhausted")
            scope = Scope(s["scope"])
            if scope.fingerprint(e["args"]) != e["inputs"]:
                raise ValueError("inputs changed: plan a new experiment")
            started = time.monotonic()
            try:
                result = execute(e["adapter"], e["args"], scope)
            except (OSError,subprocess.TimeoutExpired) as exc:
                result = dict(status="BLOCKED",label="adapter_error",error_type=type(exc).__name__)
            if scope.fingerprint(e["args"]) != e["inputs"]:
                raise ValueError("adapter modified its input; result not admitted")
            proof = dict(investigation=s["id"], experiment=eid, adapter=e["adapter"],
                         args=e["args"], inputs=e["inputs"], result=result,
                         elapsed_seconds=time.monotonic()-started)
            sha = self.store.put(proof)
            e["evidence"].append(sha)
            e["results"].append(result)
            e["status"] = "blocked" if result.get("status") == "BLOCKED" else "executed"
            return dict(evidence=sha, **result)
        return self.change("experiment", apply)

    def reject(self, hid, eid):
        def apply(s):
            h, e = s["hypotheses"][hid], s["experiments"][eid]
            if not e["results"] or hid not in e["predictions"]:
                raise ValueError("missing predicted observation")
            labels = {r.get("label") for r in e["results"] if r.get("status") == "PASS"}
            if len(labels) != 1 or len(labels) != len({r.get("label") for r in e["results"]}):
                raise ValueError("unreliable or blocked result")
            if next(iter(labels)) == e["predictions"][hid]:
                raise ValueError("experiment does not reject this hypothesis")
            h.update(status="rejected", evidence=e["evidence"][:])
            s["rejected"].append(dict(hypothesis=hid, experiment=eid))
            return hid
        return self.change("reject", apply)

    def challenge(self, rival, test, resolution=None):
        def apply(s):
            if not rival or test not in s["experiments"]:
                raise ValueError("challenger needs a concrete rival and registered counter-test")
            s["challenges"].append(dict(rival=rival, test=test, resolution=resolution))
            return s["challenges"][-1]
        return self.change("challenge", apply)

    def gate(self, hid, fix=False):
        s = self.store.load()
        problems = []
        if hid not in s["hypotheses"] or s["hypotheses"][hid]["status"] != "open":
            return ["selected hypothesis is absent or rejected"]
        if len(s["hypotheses"]) < 2:
            problems.append("Hypothesis Challenger: competing hypothesis missing; use avocat-du-diable")
        if any(h != hid and v["status"] == "open" for h,v in s["hypotheses"].items()):
            problems.append("Hypothesis Challenger: plausible alternatives remain")
        for rejection in s['rejected']:
            rejected=rejection['hypothesis'];test=s['experiments'][rejection['experiment']]
            if any(r.get('status')!='PASS' or r.get('label')==test['predictions'].get(rejected) for r in test['results']):
                problems.append('Hypothesis Challenger: rejection invalidated by later result '+rejected)
        supporting = []
        for eid, e in s["experiments"].items():
            if not e["results"]:
                continue
            if Scope(s["scope"]).fingerprint(e["args"]) != e["inputs"]:
                problems.append("Evidence Gate: stale inputs " + eid)
            for sha in e["evidence"]:
                self.store.get(sha)
            if all(r.get("status") == "PASS" and r.get("label") == e["predictions"].get(hid)
                   for r in e["results"]):
                supporting.append((eid,e))
        discriminants = [(i,e) for i,e in supporting if e["kind"] == "discriminate"
                         and len(set(e["predictions"].values())) >= 2]
        if not any(len(e["results"]) >= 2 and len({digest(r) for r in e["results"]}) == 1 for _,e in discriminants):
            problems.append("Evidence Gate: repeated stable discriminating experiment missing")
        controls = {i for i,e in supporting if e["kind"] == "control"}
        if not controls:
            problems.append("Evidence Gate: independent control missing")
        if not any(c["test"] in controls and c["resolution"] for c in s["challenges"]):
            problems.append("Hypothesis Challenger: counter-verification unresolved; use avocat-du-diable")
        if fix and not any(e["kind"] == "regression" and all(r.get("regression_ok") is True for r in e["results"])
                           for _, e in supporting):
            problems.append("Regression Guard: valid control and before/after reproduction required")
        return problems

    def conclude(self, hid, statement, fix=False):
        def apply(s):
            problems=self.gate(hid,fix)
            if problems:return dict(status='PARTIAL',gates=problems)
            s.update(status="PASS", conclusion=dict(hypothesis=hid, statement=statement, fix=fix))
            s["uncertainties"] = ["Conclusion is limited to tested inputs and declared predictions; semantic relevance requires review."]
            return dict(status="PASS", investigation=s["id"], conclusion=s["conclusion"])
        return self.change("conclusion", apply)

    def stop(self, reason, uncertainties):
        if not reason or not uncertainties:
            raise ValueError("stopping requires reason and remaining uncertainties")
        def apply(s):
            s.update(status="PARTIAL", uncertainties=uncertainties, stop_reason=reason)
            return dict(status=s["status"], reason=reason)
        return self.change("stop", apply)

    def knowledge(self):
        s = self.store.load()
        if s["status"] != "PASS" or self.gate(s["conclusion"]["hypothesis"], s["conclusion"]["fix"]):
            raise ValueError("Knowledge Recorder: validated current evidence required")
        return dict(schema=1, investigation=s["id"], statement=s["conclusion"]["statement"],
                    domain="cybersecurity investigation", status="verified-local",
                    limits=s["uncertainties"], evidence=[sha for e in s["experiments"].values() for sha in e["evidence"]],
                    attribution="investigation author", weights_changed=False)
