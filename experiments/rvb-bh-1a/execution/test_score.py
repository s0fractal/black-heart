import copy
import json
import unittest
import score

class Tests(unittest.TestCase):
    def setUp(self):
        self.key=json.loads((score.BASE/'review-key.json').read_text())['items']
        self.rows=[dict(id=i,kind=k['kind'],state=k['state'],justification='Fixture only.') for i,k in self.key.items()]
    def raw(self,rows=None):return json.dumps({'annotations':self.rows if rows is None else rows})
    def result(self,rows):return score.score([self.raw(rows)]*4,[True]*4)
    def test_reference_and_order(self):
        self.assertEqual(self.result(self.rows)['status'],'CANDIDATE_FOR_NEXT_PILOT')
        self.assertEqual(self.result(self.rows[::-1])['status'],'CANDIDATE_FOR_NEXT_PILOT')
    def test_uniform_wrong(self):
        for state in ('SUPPORTED','OPEN','AMBIGUOUS'):
            rows=copy.deepcopy(self.rows)
            for r in rows:r['state']=state
            self.assertEqual(self.result(rows)['status'],'REVISE_INSTRUMENT')
    def test_missing_duplicate_and_json_keys(self):
        for rows in (self.rows[:-1],self.rows[:-1]+[self.rows[0]]):
            self.assertEqual(self.result(rows)['status'],'INCONCLUSIVE')
        with self.assertRaises(ValueError):score.answer('{"annotations":[],"annotations":[]}')
    def test_thresholds(self):
        for count,expected in ((1,'CANDIDATE_FOR_NEXT_PILOT'),(2,'REVISE_INSTRUMENT')):
            rows=copy.deepcopy(self.rows)
            for r in rows[:count]:r['kind']='AMBIGUOUS'
            result=score.score([self.raw(rows)]+[self.raw()]*3,[True]*4)
            self.assertEqual(result['status'],expected)
            self.assertEqual(result['pairs']['A1_A2']['matches'],8-count)
    def test_critical_and_integrity(self):
        for identity in score.CRITICAL:
            rows=copy.deepcopy(self.rows)
            next(r for r in rows if r['id']==identity)['state']='SUPPORTED'
            self.assertEqual(self.result(rows)['status'],'REVISE_INSTRUMENT')
        self.assertEqual(score.score([None]*4,[False,True,True,True])['status'],'INVALID')
        self.assertEqual(score.score([None]*4,[True]*4)['status'],'INCONCLUSIVE')
    def test_wrong_key(self):
        bad=copy.deepcopy(self.key);bad['S2']['state']='REFUTED'
        # Changed key changes its diagnostic; runtime must bind the reviewed digest.
        result=score.score([self.raw()]*4,[True]*4,bad)
        self.assertEqual(result['key_agreement'][0]['state'],7)
        del bad['S1']
        with self.assertRaises(ValueError):score.score([self.raw()]*4,[True]*4,bad)

if __name__=='__main__':unittest.main()
