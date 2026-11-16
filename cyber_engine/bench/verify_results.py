"""Offline replay of published answers; never calls Qwen or changes the score.

Verify the frozen Git tree, trace hashes, usage totals and every deterministic
judgment. A successful replay proves fixture reproducibility, not model gain.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from .cases import holdout, materialize
from .run import judge, summarize
from ..scope import Scope


def verify(reports):
    reports = Path(reports)
    manifest = json.loads((reports / 'holdout-manifest.json').read_text())
    rows = json.loads((reports / 'holdout-cases.json').read_text())
    traces = [json.loads(line) for line in (reports / 'holdout-traces.jsonl').read_text().splitlines()]
    expected = json.loads((reports / 'holdout-strict-summary.json').read_text())
    cases = {c['id']: c for c in holdout()}
    keys = {(cid, condition) for cid in cases for condition in ('baseline', 'enhanced')}
    key = lambda r: (r['case'], r['condition'])
    assert len(rows) == len(traces) == len(keys) == 40
    assert {key(r) for r in rows} == {key(r) for r in traces} == keys
    indexed = {key(r): r for r in rows}
    # The content-identical tree is present in both local and published histories.
    tree = '9ebea07253e78b1761c57b644735041ffc597dcd'
    repo = Path(__file__).resolve().parents[2]
    for name, sha in manifest['frozen_files'].items():
        data = subprocess.check_output(['git', 'show', tree + ':cyber_engine/' + name], cwd=repo)
        assert hashlib.sha256(data).hexdigest() == sha, name
    for index, r in enumerate(traces, 1):
        row = indexed[key(r)]
        data = json.dumps(r, indent=2, ensure_ascii=False).encode()
        assert hashlib.sha256(data).hexdigest() == row['artifact_sha256'], key(r)
        assert r['source_sha256'] == cases[r['case']]['source_sha256']
        assert r['model'] == manifest['model']
        input_tokens = sum(sum(int(s['usage'].get(k) or 0) for k in
                           ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'))
                           for s in r['trace'])
        output_tokens = sum(int(s['usage'].get('output_tokens') or 0) for s in r['trace'])
        assert r['usage'] == dict(input_tokens=input_tokens, output_tokens=output_tokens)
        with tempfile.TemporaryDirectory(prefix='astra-offline-replay-') as d:
            materialize(cases[r['case']], d)
            scope = Scope(dict(authorization='offline replay of controlled published fixtures',
                               roots=[d], adapters=['replay'], trusted_lab=True))
            actual = judge(cases[r['case']], r['answer'], scope) if r['answer'] else dict(
                correct=False, false_positive=False, root_cause_confirmed=False, reproducible=False)
        assert actual == r['evaluation'] == row['evaluation'], key(r)
        if index % 10 == 0:
            print(json.dumps(dict(replayed=index, total=len(traces))), flush=True)
    assert summarize(traces) == expected
    return dict(status='PASS', records_verified=40, frozen_files_verified=len(manifest['frozen_files']),
                frozen_tree=tree, artifact_hashes_verified=40, judgments_reproduced=40,
                qwen_called=False, interpretation='Offline verification of recorded outcomes; no new model evaluation')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--reports', default=str(Path(__file__).resolve().parents[1] / 'reports'))
    p.add_argument('--output', required=True)
    args = p.parse_args()
    result = verify(args.reports)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
