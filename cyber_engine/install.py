"""Install into an explicit Claude Code profile, preserving every existing hook.

Backups include only overwritten files, stay private and never enter the repo.
Settings are replaced atomically after a concurrent-change check.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
import uuid


EVENTS=['UserPromptSubmit','PreToolUse','PostToolUse','PostToolUseFailure','Stop']


def install(profile,python=sys.executable):
    profile=Path(profile).resolve(strict=True)
    settings=profile/'settings.json';original=settings.read_text();data=json.loads(original)
    if data.get('disableAllHooks'):raise ValueError('profile explicitly disables hooks')
    source=Path(__file__).parent
    backup=profile/'backups'/('astra-v2-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])
    backup.mkdir(mode=0o700,parents=True)
    saved=[]
    def save(path):
        if path.exists():
            dest=backup/path.relative_to(profile);dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            shutil.copy2(path,dest);dest.chmod(0o600);saved.append(str(path.relative_to(profile)))
    save(settings)
    stage=profile/('.astra-runtime-'+uuid.uuid4().hex)
    stage.mkdir(mode=0o700)
    shutil.copytree(source,stage/'cyber_engine',ignore=shutil.ignore_patterns('__pycache__','reports'))
    (stage/'run.py').write_text('from cyber_engine.__main__ import main\nraise SystemExit(main())\n')
    (stage/'hook.py').write_text('from cyber_engine.hooks import main\nraise SystemExit(main())\n')
    runtime=profile/'astra-runtime'
    if runtime.exists():runtime.rename(backup/'astra-runtime')
    stage.rename(runtime)
    installed=[]
    for skill in (source/'skills').iterdir():
        if not skill.is_dir():continue
        for file in skill.rglob('*'):
            if not file.is_file() or '__pycache__' in file.parts:continue
            dest=profile/'skills'/file.relative_to(source/'skills')
            content=file.read_text().replace('../../network_hooks/network-journal.md','../../hooks/network-journal.md')
            if dest.exists() and dest.read_text()==content:continue
            save(dest);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(content);installed.append(str(dest.relative_to(profile)))
    command=shlex.quote(str(Path(python).resolve()))+' '+shlex.quote(str(runtime/'hook.py'))
    hooks=data.setdefault('hooks',{})
    for event in EVENTS:
        entries=hooks.setdefault(event,[])
        if not any(h.get('command')==command for e in entries for h in e.get('hooks',[])):
            entry={'hooks':[{'type':'command','command':command,'timeout':5}]}
            if event in ['PreToolUse','PostToolUse','PostToolUseFailure']:entry['matcher']='.*'
            entries.append(entry)
    match=re.search(r'(?m)^(\s*)"hooks"\s*:\s*',original)
    if match:
        start=match.end();_,length=json.JSONDecoder().raw_decode(original[start:])
        replacement=json.dumps(hooks,ensure_ascii=False,indent=2).replace('\n','\n'+match.group(1))
        updated=original[:start]+replacement+original[start+length:]
    else:updated=json.dumps(data,indent=2,ensure_ascii=False)+'\n'
    if settings.read_text()!=original:raise ValueError('settings changed concurrently; backup retained, hooks not replaced')
    temp=profile/('.settings-astra-'+uuid.uuid4().hex)
    with temp.open('x') as f:
        f.write(updated);f.flush();os.fsync(f.fileno())
    temp.chmod(settings.stat().st_mode&0o777);os.replace(temp,settings)
    # Metadata contains hashes and relative paths, never original configuration values.
    manifest=dict(status='PASS',backup=str(backup),installed=installed,
                  settings_before_sha256=hashlib.sha256(original.encode()).hexdigest(),
                  settings_after_sha256=hashlib.sha256(updated.encode()).hexdigest(),
                  hook_events=EVENTS,python=str(Path(python).resolve()))
    (backup/'manifest.json').write_text(json.dumps(manifest,indent=2));(backup/'manifest.json').chmod(0o600)
    return manifest


def main():
    p=argparse.ArgumentParser();p.add_argument('--profile',required=True);p.add_argument('--python',default=sys.executable)
    a=p.parse_args();print(json.dumps(install(a.profile,a.python),indent=2))

if __name__=='__main__':main()
