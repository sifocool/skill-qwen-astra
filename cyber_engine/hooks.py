"""Claude Code lifecycle hooks, active only inside an initialized investigation.

No tool is denied by this hook. Evidence/conclusion gates live in Engine. Stop
requires a truthful terminal state; an unresolved session may finish PARTIAL.
No transcript, tool arguments, stdout, or prompt are journaled here.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from .engine import Engine


def handle(payload):
    cwd=Path(payload.get("cwd", ".")).resolve()
    directory=cwd/".astra"/"state"
    if not (directory/"investigation.sqlite").is_file():return {}
    if (cwd/".astra").is_symlink() or directory.is_symlink():return {}
    engine=Engine(directory)
    try:
        s=engine.store.load()
        event=payload.get("hook_event_name")
        if event not in ("UserPromptSubmit","PreToolUse","PostToolUse","PostToolUseFailure","Stop"):return {}
        # Hashed session ties real invocations to evidence without logging content.
        receipt={"event":event,"session_sha256":hashlib.sha256(str(payload.get("session_id","")).encode()).hexdigest()}
        engine.change("hook:"+event,lambda state:state.update(last_hook=receipt))
        if event=="Stop":
            message=payload.get("last_assistant_message","")
            explicit_partial=bool(re.match(r'^\s*(?:\*\*)?(?:PARTIAL|BLOCKED|FAIL)\b',message,re.I))
            if explicit_partial:
                if s['status']!='PARTIAL':
                    engine.stop('explicit non-success report',['investigation remains unresolved; inspect evidence before resuming'])
                return {}
            problems=[]
            if s["status"]=="PASS":
                problems=engine.gate(s["conclusion"]["hypothesis"],s["conclusion"]["fix"])
                if not problems:
                    knowledge=engine.knowledge()
                    # Recorder persists verified data inside the existing private DB.
                    engine.change("Knowledge Recorder",lambda state:state.update(knowledge=knowledge))
                    return {}
            definitive=bool(re.match(r'^\s*(?:\*\*)?(?:DONE|PASS|termin[ée]|confirm[ée]|corrig[ée])\b',message,re.I))
            if s["status"]=="PARTIAL" and not definitive:return {}
            if payload.get("stop_hook_active") and s["status"]=="ACTIVE":
                engine.stop("completion gate: unresolved investigation",["evidence incomplete; resume with a justified test"])
            return {"decision":"block","reason":"Completion Gate: " + "; ".join(problems or [
                "investigation unresolved. Use the engine to conclude with evidence, or begin the final report with PARTIAL: and remaining uncertainties. Do not claim DONE."])}
        if s["status"]!="ACTIVE":return {}
        selected=engine.select()
        context="ASTRA " + json.dumps(dict(investigation=s["id"],next=selected,
            challenger="avocat-du-diable if alternatives remain",evidence="conclusions require engine gate"),ensure_ascii=False)
        return {"hookSpecificOutput":{"hookEventName":event,"additionalContext":context}}
    finally:engine.store.close()


def main():
    payload={}
    try:
        raw=sys.stdin.buffer.read(1024*1024+1)
        if len(raw)>1024*1024:raise ValueError("payload size")
        payload=json.loads(raw)
        out=handle(payload)
        if out:print(json.dumps(out,ensure_ascii=False))
        return 0
    except Exception as e:
        if isinstance(payload,dict) and payload.get('hook_event_name')=='Stop':
            print(json.dumps({'decision':'block','reason':'Completion Gate unavailable: '+type(e).__name__+'. Report BLOCKED/PARTIAL and repair the investigation evidence; no verified completion is available.'}))
            return 0
        # Nonblocking failure, visible but with no secret-bearing exception text.
        print("Astra hook unavailable: "+type(e).__name__,file=sys.stderr)
        return 1

if __name__=="__main__":sys.exit(main())
