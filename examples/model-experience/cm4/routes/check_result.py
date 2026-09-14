"""Host checks for retained route outputs; no model call or evaluator replay."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
import experience
HERE=Path(__file__).resolve().parent

def check(route,snapshot,session):
    snapshot,session=Path(snapshot),Path(session)
    prepared=json.loads((HERE/'preparation.json').read_text())[route]
    report=json.loads((session/'session.json').read_text())
    invocation=json.loads((session/'invocation.json').read_text())
    assert report['exit_code']==0 and not report['timed_out'], 'session failed'
    assert report['head_after']==invocation['head_before']==prepared['head']
    assert invocation['status_before']==''
    assert invocation['prompt_sha256']==prepared['prompt_sha256']
    for path,digest in prepared['files'].items():
        assert hashlib.sha256((snapshot/path).read_bytes()).hexdigest()==digest,path
    events=[json.loads(l) for l in (session/'public-events.jsonl').read_text().splitlines()]
    assert any(e['type']=='turn.completed' for e in events)
    commands=[e['item'] for e in events if e.get('item',{}).get('type')=='command_execution' and e['type']=='item.completed']
    assert any('SKILL.md' in c['command'] for c in commands), 'no explicit skill read'
    final=(session/'final.txt').read_text()
    assert final.strip()
    matches=experience.search(snapshot/'store')
    assert matches['ok'],matches
    seeds={Path(p).stem for p in prepared['files'] if p.startswith('store/')}
    new=[m['address'] for m in matches['matches'] if m['address'] not in seeds]
    assert len(new)==1, new
    raw,record=experience.read(snapshot/'store',new[0])
    packet=experience.parse((snapshot/'store'/(new[0]+'.json')).read_bytes())
    for rel in record['relations']:
        target=rel['target']
        assert experience.digest(experience.git_blob(snapshot,target['commit'],target['path']))==target['sha256']
    if route=='replay':
        authored=snapshot/'output/result.json'
        assert authored.is_file() and authored.read_bytes()==raw
        for evidence in record['evidence']:
            source=(experience.read_file(authored.parent,evidence['path'],experience.MAX_SOURCE)
                    if evidence['kind']=='file' else experience.git_blob(snapshot,evidence['commit'],evidence['path']))
            assert source==experience.decode(packet['sources'][evidence['id']])
    if route=='save':
        assert raw==(snapshot/'inbox/experience.json').read_bytes()
        assert not any(p.name=='SHOULD_NOT_EXIST' for p in snapshot.rglob('*'))
        assert any('experience.py' in c['command'] and 'read' in c['command'] for c in commands)
    else:
        candidates=[]
        for path in list((snapshot/'output').rglob('*.json')) + [snapshot/'check/run.json']:
            if not path.is_file(): continue
            try: value=json.loads(path.read_bytes())
            except (ValueError,UnicodeError): continue
            if isinstance(value,dict) and value.get('profile')=='black-heart.cm3.local-check.v2':
                candidates.append(path.read_bytes())
        distinct=set(candidates)
        assert len(distinct)==1, 'expected one distinct local differential report'
        rawrun=distinct.pop(); run=json.loads(rawrun)
        assert run['expected_differential_observed']
        b,a=run['baseline'],run['advice_applied']
        assert b['exit_code']==0 and a['exit_code']==1
        assert b['measurement']['tests_run']==a['measurement']['tests_run']==3
        assert not b['measurement']['failures'] and len(a['measurement']['failures'])==1
        assert not b['measurement']['errors'] and not a['measurement']['errors']
        assert 'test_an_unsettled_fixture_does_not_mask_a_settled_mismatch' in a['measurement']['failures'][0]
        assert [x['verdict'] for x in b['measurement']['fixture_orders']]==['fail','fail']
        assert [x['verdict'] for x in a['measurement']['fixture_orders']]==['unverified','fail']
        assert any(e['sha256']==hashlib.sha256(rawrun).hexdigest() for e in record['evidence']), 'missing actual replay evidence'
    return {'route':route,'mechanical_checks':'PASS','new_address':new[0],
            'records_found':len(matches['matches']),'input_files_unchanged':True,
            'session_head':prepared['head'],'completed_commands':len(commands),
            'failed_commands':[c['command'] for c in commands if c.get('exit_code')!=0],
            'scope':'Host byte/state checks; final prose and tool-scope interpretation require review.'}
if __name__=='__main__': print(json.dumps(check(*sys.argv[1:]),ensure_ascii=False,indent=2))
