"""Bounded origin-scoped HTTP and deterministic state-machine replay."""
import hashlib
import json
import urllib.error
import urllib.request
from .dynamic import replay


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None


def http_probe(args, scope):
    url=scope.url(args["url"])
    req=urllib.request.Request(url,method="GET",headers={"User-Agent":"Astra-local-investigation/2"})
    try:
        response=urllib.request.build_opener(NoRedirect).open(req,timeout=3)
    except urllib.error.HTTPError as e:
        response=e
    with response:
        data=response.read(65537)
        code=response.code
    return dict(status="PASS",label=str(code),status_code=code,
                body_sha256=hashlib.sha256(data[:65536]).hexdigest(),truncated=len(data)>65536,
                limitation="GET only, redirects not followed, response body not persisted")


def protocol(args, scope):
    traces=args["traces"]
    if not 1<=len(traces)<=20 or any(len(t["steps"])>20 for t in traces):
        raise ValueError("protocol replay limit exceeded")
    results=[]; mismatches=[]
    for i,trace in enumerate(traces):
        r=replay(dict(script=args["script"],input=json.dumps(trace["steps"])),scope)
        try:
            actual=json.loads(r["stdout"])
        except ValueError:
            actual=None
        match=r["exit_code"]==0 and actual==trace["expected"]
        results.append(dict(index=i,role=trace.get("role"),actual=actual,matches=match))
        if not match:mismatches.append(i)
    return dict(status="PASS",label="transition_violation" if mismatches else "transitions_valid",
                traces=results,mismatches=mismatches,
                limitation="contract supplied by investigator; checks do not prove exhaustive authorization")
