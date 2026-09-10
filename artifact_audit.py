"""Host-side data auditors for CLI routes; never execute embedded PDF runners."""
import json
from pathlib import Path


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def manifest(path, prefix, latest=False):
    rows = [line[len(prefix):] for line in Path(path).read_bytes().splitlines() if line.startswith(prefix)]
    need(rows and (latest or len(rows) == 1), 'MANIFEST_MISSING_OR_AMBIGUOUS')
    return json.loads(rows[-1] if latest else rows[0])


def continuum(path):
    from continuum import ThunkCheckpoint, verify_checkpoint_computation
    rows = manifest(path, '%🖤 CONTINUUM_THUNK: '.encode(), latest=True)
    need(isinstance(rows, list) and 0 < len(rows) <= 10000, 'CHECKPOINT_COUNT')
    prev = None
    for row in rows:
        cp = ThunkCheckpoint.from_dict(row)
        need(cp.verify(), 'CHECKPOINT_SIGNATURE_OR_HASH')
        ok, reason = verify_checkpoint_computation(cp)
        need(ok, reason)
        if prev is None:
            need(cp.height == 0 and cp.prev_hash == '0'*64, 'CHECKPOINT_GENESIS')
            signer = cp.public_key_hex
        else:
            need(cp.height == prev.height+1 and cp.prev_hash == prev.checkpoint_hash, 'CHECKPOINT_CHAIN')
            need(cp.initial_expr == prev.initial_expr and cp.atp_accumulated == prev.atp_accumulated+cp.atp_spent_step, 'CHECKPOINT_REPLAY_CHAIN')
        need(cp.public_key_hex == signer, 'CHECKPOINT_SIGNER_CONTINUITY')
        prev = cp
    print('scope: checkpoint links, declared signatures and bounded computation replay; signer identity not externally pinned')
    return True


def zk(path):
    from zk_glyph import SchnorrProof, schnorr_verify, ChaumPedersenProof, chaum_pedersen_verify
    obj = manifest(path, '%🖤 ZK_PROOF_MANIFEST: '.encode())
    schnorr, cp = obj.get('schnorr_proofs', []), obj.get('chaum_pedersen_proofs', [])
    need(schnorr or cp, 'NO_PROOFS')
    need(all(schnorr_verify(SchnorrProof.from_dict(p)) for p in schnorr), 'SCHNORR_PROOF')
    need(all(chaum_pedersen_verify(ChaumPedersenProof.from_dict(p)) for p in cp), 'CHAUM_PEDERSEN_PROOF')
    print('scope: supplied Schnorr and Chaum-Pedersen proof equations under local verifier')
    return True


def ledger(path):
    from living_ledger import LedgerBlock
    from crypto import verify_bytes
    from glyph import parse, evaluate
    obj = manifest(path, '%🖤 LEDGER_MANIFEST: '.encode())
    blocks = obj['blocks']; need(blocks and obj['block_count'] == len(blocks), 'BLOCK_COUNT')
    previous = '0'*64
    for i,row in enumerate(blocks):
        b = LedgerBlock.from_dict(row)
        need(b.height == i and b.prev_hash == previous, 'LEDGER_CHAIN')
        need(b.compute_hash() == b.block_hash, 'LEDGER_HASH')
        need(verify_bytes(bytes.fromhex(b.public_key_hex), b.canonical_bytes_for_signing(), bytes.fromhex(b.signature_hex)), 'LEDGER_SIGNATURE')
        if b.combinator_claim:
            claim = b.combinator_claim; budget = claim.get('atp',10000)
            need(type(budget) is int and 0 <= budget <= 10000, 'CLAIM_BUDGET')
            result = evaluate(parse(claim['expr']), max_atp=budget)
            expected = evaluate(parse(claim['expected']), max_atp=budget)
            need(result.is_settled() and expected.is_settled() and result.term == expected.term, 'LEDGER_CLAIM')
        previous = b.block_hash
    need(obj['chain_tip'] == previous, 'LEDGER_TIP')
    print('scope: ledger links, hashes, declared signatures and combinator claims; signer identity not externally pinned')
    return True


def colony(path):
    obj = manifest(path, b'# %COLONY_MANIFEST:')
    epochs = obj.get('epochs'); need(isinstance(epochs,list) and epochs, 'NO_EPOCHS')
    previous = '0'*64
    for i,ep in enumerate(epochs):
        need(ep.get('prev_epoch_hash') == previous, 'EPOCH_LINK')
        current = ep.get('epoch_hash')
        need(isinstance(current,str) and len(current)==64 and all(c in '0123456789abcdef' for c in current), 'EPOCH_HASH_SHAPE')
        previous = current
    print('scope: declared epoch links only; epoch hashes, signatures and colony behavior not recomputed')
    return True


def metamorphosis(path):
    from organism import Organism, Chromosome
    from metamorphosis import MetamorphicTransitionReceipt, ExperimentLog, audit_metamorphic_transition
    obj = manifest(path, b'# %METAMORPHOSIS')
    def organism(row):
        org = Organism(generation=row['generation'], parent_hash=row['parent_hash'],
                        public_key_hex=row['public_key_hex'], secret_key_hex='',
                        birth_timestamp_utc=row['birth_timestamp_utc'], organism_hash=row['organism_hash'],
                        chromosomes=[Chromosome.from_dict(c) for c in row['chromosomes']])
        need(org.compute_hash() == row['organism_hash'], 'ORGANISM_HASH')
        return org
    need(obj.get('experiments'), 'MISSING_EXPERIMENTS')
    ok,reason = audit_metamorphic_transition(organism(obj['parent']),organism(obj['successor']),
        MetamorphicTransitionReceipt.from_dict(obj['transition']),experiment_log=ExperimentLog.from_list(obj['experiments']))
    need(ok,reason)
    print('scope: metamorphic transition replay under local frozen evaluator; embedded source_dir ignored')
    return True
