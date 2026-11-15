"""Real pinned Claude Code -> local Qwen -> hook dispatch smoke test.

Uses a disposable profile, two read-only tool calls, and the installed hook.
No production transcript/config/credentials are copied into the test profile.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
from ..engine import Engine
from ..install import EVENTS


def run(cli,installed_hook,python):
    with tempfile.TemporaryDirectory(prefix='astra-live-hooks-') as d:
        root=Path(d);config=root/'config';config.mkdir();workspace=root/'workspace';workspace.mkdir()
        (workspace/'fixture.txt').write_text('ASTRA_HOOK_FIXTURE\n')
        e=Engine(workspace/'.astra/state')
        e.init(dict(authorization='local hook dispatch test',roots=[str(workspace)],adapters=['replay'],trusted_lab=True),'hook runtime dispatch')
        e.hypothesis('the read hook is invoked');e.hypothesis('hook configuration ignored')
        command=shlex.quote(python)+' '+shlex.quote(installed_hook)
        settings={'hooks':{event:[{'hooks':[{'type':'command','command':command,'timeout':5}],
                    **({'matcher':'.*'} if 'ToolUse' in event else {})}] for event in EVENTS}}
        path=config/'settings.json';path.write_text(json.dumps(settings))
        env={k:os.environ[k] for k in ['PATH','HOME','TMPDIR','LANG','USER','SHELL'] if k in os.environ}
        env.update(CLAUDE_CONFIG_DIR=str(config),ANTHROPIC_BASE_URL='http://127.0.0.1:8095',
                   ANTHROPIC_API_KEY='local',CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1',
                   DISABLE_AUTOUPDATER='1',ENABLE_TOOL_SEARCH='false',API_TIMEOUT_MS='120000')
        argv=[cli,'-p','Read missing.txt once (the expected error is part of the test), then Read fixture.txt. Finally respond PARTIAL: hook test. Do not use other tools.',
            '--no-chrome','--restricted','--tools','Read','--allowedTools','Read','--permission-mode','dontAsk',
            '--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--setting-sources','',
            '--settings',str(path),'--system-prompt','Follow the two read-only tool requests. No shell or subagents. After hook feedback finish truthfully as PARTIAL.',
            '--model','qwen3.8-27b','--effort','medium','--no-session-persistence','--output-format','stream-json','--verbose','--include-hook-events']
        try:r=subprocess.run(argv,cwd=workspace,env=env,capture_output=True,text=True,timeout=240)
        except subprocess.TimeoutExpired:
            return dict(status='BLOCKED',reason='CLI request exceeded 240 seconds')
        events=Counter(row[0].removeprefix('hook:') for row in e.store.db.execute("SELECT name FROM events WHERE name LIKE 'hook:%'"))
        records=[];tool_names=[]
        for line in r.stdout.splitlines():
            try:v=json.loads(line)
            except ValueError:continue
            if v.get('type')=='result':records.append({k:v[k] for k in ['type','subtype','is_error','result','usage','num_turns'] if k in v})
            for c in v.get('message',{}).get('content',[]):
                if c.get('type')=='tool_use':tool_names.append(c.get('name'))
        loop_ok=events['Stop']<=3 and bool(records) and bool(records[-1].get('result'))
        result=dict(status='PASS' if r.returncode==0 and all(events[k]>0 for k in EVENTS) and loop_ok else 'PARTIAL',
            completion_loop_guard_ok=loop_ok,
            cli_version=subprocess.check_output([cli,'--version'],text=True).strip(),
            cli_sha256=hashlib.sha256(Path(cli).read_bytes()).hexdigest(),exit_code=r.returncode,
            events=dict(events),tools=tool_names,final_state=e.store.load()['status'],results=records,
            stderr_excerpt=r.stderr[:1000],profile='disposable explicit settings; installed hook runtime')
        e.store.close()
        return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cli',required=True);p.add_argument('--hook',required=True);p.add_argument('--python',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();result=run(a.cli,a.hook,a.python);Path(a.output).write_text(json.dumps(result,indent=2));print(json.dumps(result))
