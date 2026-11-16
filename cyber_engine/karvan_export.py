"""Prepare declarative Karvan candidates with actual local interface validation.

No live ledger mutation, no weight update, no automatic promotion to verified.
The external author's words and authorship remain explicit in provenance.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile
from .engine import Engine


def bundle(engine):
    k=engine.knowledge()
    statement=k['statement'];domain=k['domain']
    applies='Applies to the exact tested contract and input preconditions of investigation '+k['investigation']+'.'
    text='\n'.join([statement,domain,applies,*k['limits']])
    return dict(schema=1,source_text=text,statement=statement,domain=domain,applies_when=applies,
                limits=k['limits'],investigation=k['investigation'],evidence=k['evidence'],
                source_author=k['attribution'],karvan_status='candidate',weights_changed=False)


def validate_with_karvan(data,package_root):
    root=Path(package_root).resolve(strict=True)
    if not (root/'karvan/knowledge.py').is_file():raise ValueError('Karvan knowledge interface missing')
    sys.path.insert(0,str(root))
    from karvan.ledger import Ledger
    from karvan.knowledge import item,ITEM_FIELDS
    with tempfile.TemporaryDirectory(prefix='astra-karvan-') as d:
        ledger=Ledger(str(Path(d)/'validation.sqlite'))
        try:
            source=ledger.knowledge.add_source(data['source_text'],'external-reviewed-investigation',
                dict(author=data['source_author'],evidence=data['evidence']))
            draft={key:[] for key in ITEM_FIELDS}
            draft.update(statement=item(data['statement'],source),domain=item(data['domain'],source),
                applies_when=[item(data['applies_when'],source)],limits=[item(x,source) for x in data['limits']],
                provenance=dict(author=data['source_author'],sources=[source],
                                episodes=[dict(id=data['investigation'],task_id='astra-cyber')]))
            admitted=ledger.knowledge.admit(draft,by='astra-export-validation')
            return dict(status='PASS',candidate_id=admitted.id,admitted_status=admitted.status.value,
                        interface='KnowledgeStore.add_source + admit',live_ledger_modified=False,draft=draft)
        finally:ledger.db.close()


def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--output',required=True)
    p.add_argument('--karvan-package');a=p.parse_args();e=Engine(a.state)
    try:
        data=bundle(e)
        if a.karvan_package:data['interface_test']=validate_with_karvan(data,a.karvan_package)
        path=Path(a.output)
        with path.open('x') as f:json.dump(data,f,indent=2,ensure_ascii=False)
        path.chmod(0o600)
        print(json.dumps(dict(status='PASS',output=str(path),karvan_status='candidate')))
    finally:e.store.close()

if __name__=='__main__':main()
