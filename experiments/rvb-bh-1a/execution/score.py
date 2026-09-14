"""Strict answer parsing and the accepted four-session decision rule."""
import json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
KINDS={'OPERATION','IDENTITY_AUTHORITY','SEMANTIC_BINDING','COVERAGE','AMBIGUOUS'}
STATES={'SUPPORTED','REFUTED','OPEN','AMBIGUOUS'}
IDS=('R1','R2','S1','S2','B1','B2','D1','D2')
CRITICAL={'R2','S2','B1','B2','D2'}

def unique(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise ValueError('DUPLICATE_JSON_KEY')
        out[k]=v
    return out

def answer(raw):
    x=json.loads(raw,object_pairs_hook=unique)
    if not isinstance(x,dict) or set(x)!={'annotations'}: raise ValueError('BAD_ENVELOPE')
    if not isinstance(x['annotations'],list) or len(x['annotations'])!=8: raise ValueError('BAD_COUNT')
    result={}
    for item in x['annotations']:
        if not isinstance(item,dict) or set(item)!={'id','kind','state','justification'}: raise ValueError('BAD_ITEM')
        if any(not isinstance(v,str) for v in item.values()): raise ValueError('BAD_TYPE')
        i=item['id']
        if i not in IDS or i in result: raise ValueError('BAD_ID')
        if item['kind'] not in KINDS or item['state'] not in STATES: raise ValueError('BAD_LABEL')
        if not item['justification'].strip() or len(item['justification'])>1000: raise ValueError('BAD_JUSTIFICATION')
        result[i]=item
    return result

def score(raws,validity,key=None):
    if len(raws)!=4 or len(validity)!=4: raise ValueError('FOUR_SLOT_VECTOR_REQUIRED')
    if any(type(v) is not bool for v in validity): raise ValueError('BAD_VALIDITY')
    if not all(validity): return {'status':'INVALID'}
    parsed=[];errors={}
    for i,raw in enumerate(raws):
        try: parsed.append(answer(raw))
        except (ValueError,TypeError) as e: parsed.append(None);errors[str(i+1)]=str(e)
    if errors:return {'status':'INCONCLUSIVE','format_errors':errors}
    key=key or json.loads((BASE/'review-key.json').read_text())['items']
    if set(key)!=set(IDS) or any(x['kind'] not in KINDS or x['state'] not in STATES for x in key.values()): raise ValueError('BAD_KEY')
    pairs={}
    for name,a,b in [('A1_A2',0,3),('B1_B2',1,2),('A1_B1',0,1),('A2_B2',3,2)]:
        pairs[name]={'matches':sum(all(parsed[a][i][k]==parsed[b][i][k] for k in ('kind','state')) for i in IDS),
                     'disagreements':[i for i in IDS if any(parsed[a][i][k]!=parsed[b][i][k] for k in ('kind','state'))]}
    accuracies=[];critical=[]
    for n,p in enumerate(parsed,1):
        accuracies.append({k:sum(p[i][k]==key[i][k] for i in IDS) for k in ('kind','state')})
        critical += [{'slot':n,'id':i} for i in sorted(CRITICAL) if p[i]['state']=='SUPPORTED']
    ok=not critical and all(v['matches']>=7 for v in pairs.values()) and all(min(a.values())>=7 for a in accuracies)
    return {'status':'CANDIDATE_FOR_NEXT_PILOT' if ok else 'REVISE_INSTRUMENT',
            'pairs':pairs,'key_agreement':accuracies,'critical':critical,
            'annotations':parsed}
