"""Offline regressions: prompts, context refusal, traces and audit sequencing."""
import copy
import datetime
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
import context_check
import events
import run_slot

HERE=Path(__file__).resolve().parent
BASE=HERE.parent

class Execution(unittest.TestCase):
    def test_no_card_identifiers_outside_cards(self):
        cards={c['id']:c for c in json.loads((BASE/'cards.json').read_text())}
        for slot in json.loads((BASE/'schedule.json').read_text())['slots']:
            prefix,body=(HERE/'stimuli'/f"{slot['slot']}.txt").read_text().split('\nCARDS:\n')
            self.assertIsNone(re.search(r'\b(?:R[12]|S[12]|B[12]|D[12])\b',prefix))
            self.assertEqual(json.loads(body),[cards[i] for i in slot['order']])
            self.assertIn('establishes/certifies',prefix)

    def test_context_mutations(self):
        for slot in json.loads((BASE/'schedule.json').read_text())['slots']:
            capture=json.loads((HERE/'context'/f"{slot['slot']}.json").read_text())
            prompt=(HERE/'stimuli'/f"{slot['slot']}.txt").read_text()
            self.assertTrue(context_check.check(capture,prompt)['ok'])
            mutations=[lambda b:b['tools'].append({'name':'Bash'}),
                       lambda b:b['messages'].append({'role':'user','content':'memory'}),
                       lambda b:b['messages'][0].update(content='changed'),
                       lambda b:b['system'][2].update(text='memory'),
                       lambda b:b['messages'][1]['content'][0].update(text='extra context'),
                       lambda b:b.update(model='different')]
            for mutate in mutations:
                bad=copy.deepcopy(capture);mutate(bad['requests'][0]['body'])
                with self.assertRaises(ValueError):context_check.check(bad,prompt)

    def test_canary_control(self):
        prompt='OFFLINE CONTEXT PROBE. Return only probe-ok.'
        good=json.loads((HERE/'context'/'canary-hardened.json').read_text())
        bad=json.loads((HERE/'context'/'canary-positive-control.json').read_text())
        self.assertTrue(context_check.check(good,prompt)['ok'])
        self.assertTrue(any(bad['canary'] in json.dumps(q) for q in bad['requests']))
        with self.assertRaises(ValueError):context_check.check(bad,prompt)

    def test_public_retention_and_hidden_removal(self):
        trace=events.Trace()
        raw=b'{ "type": "result", "result": "ok", "is_error": false }\n'
        self.assertEqual(trace.line(raw),raw)
        hidden={'type':'assistant','message':{'content':[None,{'type':'thinking','thinking':'private'},{'type':'text','text':'public'}],'stop_reason':None}}
        out=json.loads(trace.line(json.dumps(hidden).encode()))
        self.assertEqual(out['message']['content'],[None,{'type':'text','text':'public'}])
        self.assertIsNone(out['message']['stop_reason'])
        self.assertEqual(trace.omitted,1)
        self.assertEqual(trace.rewritten,1)
        trace.line(raw);self.assertTrue(trace.failed)

    def test_tool_error_and_malformed_events(self):
        for event in ({'type':'assistant','message':{'content':[{'type':'tool_use'}]}},
                      {'type':'system','subtype':'init','tools':['Bash']}):
            trace=events.Trace();trace.line(json.dumps(event).encode());self.assertTrue(trace.tool)
        trace=events.Trace();trace.line(b'{bad');self.assertEqual(trace.malformed,1)
        trace.line(b'{"type":"result","is_error":true}');self.assertTrue(trace.failed)
        trace.line(b'{"type":"unexpected"}');self.assertEqual(trace.unknown,['unexpected'])

    def test_simulated_client_partial_lines_and_timeout(self):
        parent=Path.home()/'rvb-bh-1a-work';parent.mkdir(exist_ok=True)
        for source,timeout,expected in [
            ("import sys;sys.stdin.read();sys.stdout.write('{\"type\":\"result\",');sys.stdout.flush();sys.stdout.write('\"result\":\"ok\"}\\n');print('stderr',file=sys.stderr)",3,False),
            ("import sys,time;sys.stdin.read();sys.stdout.write('{partial');sys.stdout.flush();time.sleep(10)",0.2,True),
            ("import sys;sys.stdin.read();sys.exit(3)",3,False)]:
            with tempfile.TemporaryDirectory(dir=parent) as td:
                folder=Path(td)
                trace,code,expired=events.run([sys.executable,'-c',source],b'prompt',folder,dict(os.environ),folder,timeout)
                self.assertEqual(expired,expected)
                if expected:
                    self.assertEqual((folder/'public-events.jsonl').read_bytes(),b'{partial')
                    self.assertEqual(trace.malformed,1)
                elif code==0:
                    self.assertEqual(trace.result,'ok');self.assertEqual((folder/'stderr.txt').read_text(),'stderr\n')
                else:self.assertEqual(code,3);self.assertFalse(trace.complete)

    def test_audit_is_required_and_bound(self):
        parent=Path.home()/'rvb-bh-1a-work';parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as td:
            root=Path(td);slot={'slot':1};folder=root/'1';folder.mkdir()
            result={'slot':slot,'finished_at':'2026-01-01T00:00:00+00:00','infrastructure_valid':True,'format_valid':False}
            run_slot.write(folder/'result.json',result)
            (folder/'public-events.jsonl').write_text('retained')
            with self.assertRaises(FileNotFoundError):run_slot.prior(root,[slot])
            audit={'valid':True,'reviewer':'offline test','evidence':'inspected fixtures',
                   'audited_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'hashes':{n:run_slot.sha(folder/n) if (folder/n).exists() else None for n in ('result.json','public-events.jsonl','response.txt','context.json')}}
            run_slot.write(folder/'audit.json',audit)
            self.assertEqual(run_slot.prior(root,[slot]),(None,[None],[True]))
            (folder/'public-events.jsonl').write_text('changed')
            with self.assertRaisesRegex(ValueError,'AUDIT_HASH'):run_slot.prior(root,[slot])

if __name__=='__main__':unittest.main()
