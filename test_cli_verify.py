import contextlib,io,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from crypto import generate_keypair

ROOT=Path(__file__).parent
class VerifyCLI(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=Path(self.tmp.name)
  self.sk,self.pk=generate_keypair()
 def invoke(self,p,ok=True):
  r=subprocess.run([sys.executable,str(ROOT/'cli.py'),'verify',str(p)],capture_output=True,text=True,timeout=15)
  self.assertEqual(r.returncode,0 if ok else 1,r.stdout+r.stderr)
  self.assertNotIn('Traceback',r.stderr)
  return r.stdout
 def corrupt(self,p,prefix,mutate):
  lines=p.read_bytes().splitlines(keepends=True)
  for i,line in enumerate(lines):
   if line.startswith(prefix):
    obj=json.loads(line[len(prefix):]);mutate(obj);lines[i]=prefix+json.dumps(obj,ensure_ascii=False).encode()+b'\n';break
  else:self.fail('manifest missing')
  p.write_bytes(b''.join(lines))
 def test_polyglot_claim(self):
  from polyglot import PolyglotDocument
  doc=PolyglotDocument('claim');doc.add_claim('id','identity','🤍 a','a');p=self.d/'claim.pdf';doc.compile(str(p));self.invoke(p)
  bad=PolyglotDocument('bad');bad.add_claim('id','wrong','🤍 a','b');bad.compile(str(p));self.invoke(p,False)
 def test_contract(self):
  from monad import SelfVerifyingContractPolyglot
  doc=SelfVerifyingContractPolyglot('contract');doc.add_clause('c','title','text','identity','🤍 a','a');p=self.d/'c.pdf';doc.compile(str(p));self.invoke(p)
  self.corrupt(p,'%🖤 CONTRACT_MANIFEST: '.encode(),lambda x:x.update(joint_anchor='0'*64));self.invoke(p,False)
 def test_continuum(self):
  from continuum import ResumableComputationPolyglot
  doc=ResumableComputationPolyglot();doc.initialize('🤍 a',10,self.sk,self.pk);p=self.d/'continuum.pdf';doc.compile(str(p));self.invoke(p)
  self.corrupt(p,'%🖤 CONTINUUM_THUNK: '.encode(),lambda x:x[0].update(current_expr='wrong'));self.invoke(p,False)
 def test_zk(self):
  from zk_glyph import ZKProofPolyglot,schnorr_prove
  doc=ZKProofPolyglot('proof');doc.add_schnorr_proof(schnorr_prove(self.sk,context='original'));p=self.d/'zk.pdf';doc.compile(str(p));self.invoke(p)
  self.corrupt(p,'%🖤 ZK_PROOF_MANIFEST: '.encode(),lambda x:x['schnorr_proofs'][0].update(context='changed'));self.invoke(p,False)
 def test_ledger(self):
  from living_ledger import LivingLedger
  doc=LivingLedger();doc.create_genesis('test','test',self.sk);p=self.d/'ledger.pdf';doc.compile(str(p));self.invoke(p)
  self.corrupt(p,'%🖤 LEDGER_MANIFEST: '.encode(),lambda x:x.update(chain_tip='f'*64));self.invoke(p,False)
 def test_colony(self):
  from colony import Colony,ColonyPolyglotCompiler
  doc=Colony.create_genesis_colony('test',initial_organisms=1,initial_substrate_atp=1000);doc.step_epoch(solar_influx_atp=50)
  p=self.d/'colony.pdf';p.write_bytes(ColonyPolyglotCompiler(doc).compile_pdf());out=self.invoke(p);self.assertIn('declared epoch links only',out)
  self.corrupt(p,b'# %COLONY_MANIFEST:',lambda x:x['epochs'][0].update(prev_epoch_hash='f'*64));self.invoke(p,False)
 def test_metamorphosis(self):
  from organism import create_genesis_organism,Chromosome
  from metamorphosis import contemplate_and_evolve,MetamorphicPolyglotCompiler
  org=create_genesis_organism();org.chromosomes.append(Chromosome(gene_id='opt',gene_name='router',expression='🌿 (🖤 (🌿 🤍)) (🖤 🤍)',expected_normal_form='(🌿 🤍) 🤍',max_atp=100));org.organism_hash=org.compute_hash()
  succ,log,receipt=contemplate_and_evolve(org);p=self.d/'meta.pdf';p.write_bytes(MetamorphicPolyglotCompiler(org,succ,receipt,log).compile_pdf());self.invoke(p)
  self.corrupt(p,b'# %METAMORPHOSIS',lambda x:x['parent'].update(organism_hash='f'*64));self.invoke(p,False)
 def test_runner_text_is_not_executed_or_detected_as_manifest(self):
  p=self.d/'trap.pdf';p.write_text("raise Exception('must not execute')\nprefix = '%🖤 CONTINUUM_THUNK: ' \n")
  self.invoke(p,False)
 def test_malformed_manifest_refuses_without_traceback(self):
  p=self.d/'bad.pdf';p.write_bytes('%🖤 CONTINUUM_THUNK: {oops}\n'.encode());self.invoke(p,False)

class TermParser(unittest.TestCase):
 def test_constructor_and_glyph_positive_controls(self):
  from cegis_kernel import parse_term
  from glyph import App,K,Var
  self.assertEqual(parse_term("App(K, Var('x'))"),App(K,Var('x')))
  self.assertEqual(parse_term("App(left=K, right=Var(name='x'))"),App(K,Var('x')))
  self.assertEqual(parse_term('🖤 x'),App(K,Var('x')))
 def test_python_injection_is_refused_without_effect(self):
  from cegis_kernel import parse_term
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'marker'
   payload="App(__import__('pathlib').Path("+repr(str(p))+").write_text('executed'), K)"
   with self.assertRaises(ValueError):parse_term(payload)
   self.assertFalse(p.exists())
   for expr in ["App(K, K, K)","Var(42)","Comb(symbol='x', **{})","App(K, (lambda: K)())"]:
    with self.subTest(expr=expr),self.assertRaises(ValueError):parse_term(expr)

if __name__=='__main__':unittest.main()
