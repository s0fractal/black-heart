"""Fail-closed content scan executed with the receiver's actual read permissions.

Copied from experiments/transfer-1/harness/tmp_scan.py (SCANNER verbatim; the
scanner lower-cases file content, so markers are lower-case bytes). Adapted:
markers name this experiment, the defect and the repair's refusal string;
digests are the sha256 of every control-patched mycelium.py from
../controls/C*.json EXCEPT C0 (its digest is the pinned pre-repair file, which
IS the snapshot's own mycelium.py and must not count as a leak) plus the
repository checkout's current mycelium.py (the merged repair).
"""
import hashlib
import json
import tempfile
from pathlib import Path
from common import REPO, ROOT, run, read_json

MARKERS = [b'calib-myc-1', b'calibmyc1', b's-verif-7', b'rejected_metabolic_viability_unsettled']

# Sent over stdin, not written into readable temporary storage.
SCANNER = r'''import hashlib,json,os,stat,sys
request=json.load(sys.stdin)
markers=[bytes.fromhex(x) for x in request['markers_hex']]
digests=set(request['digests'])
seen=set();matches=[];errors=[];dangling=[];files=0;denied=0
stack=list(request['roots'])
while stack:
 p=stack.pop()
 try:
  info=os.stat(p)
 except FileNotFoundError:
  # Only here: a symlink whose target does not exist (Chromium-style
  # SingletonCookie links) has no readable content and cannot leak; it is
  # recorded, not an error. Anything that vanishes AFTER a successful stat
  # is a genuine disappearance during the scan (handled below).
  if os.path.islink(p) and not os.path.exists(p): dangling.append(p)
  else: errors.append({'path':p,'error':'DISAPPEARED_DURING_SCAN'})
  continue
 except PermissionError:
  denied+=1;continue
 except OSError as e:
  errors.append({'path':p,'error':type(e).__name__});continue
 try:
  key=(info.st_dev,info.st_ino)
  if key in seen: continue
  seen.add(key)
  if stat.S_ISDIR(info.st_mode):
   stack.extend(os.path.join(p,n) for n in os.listdir(p));continue
  if not stat.S_ISREG(info.st_mode): continue
  h=hashlib.sha256();tail=b'';found=False
  with open(p,'rb') as f:
   while True:
    chunk=f.read(1024*1024)
    if not chunk: break
    h.update(chunk);text=tail+chunk.lower()
    found=found or any(m in text for m in markers)
    tail=text[-max(len(m) for m in markers):]
   after=os.fstat(f.fileno())
  if (info.st_size,info.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
   errors.append({'path':p,'error':'CHANGED_DURING_SCAN'})
  files+=1
  if found or h.hexdigest() in digests: matches.append({'path':p,'sha256':h.hexdigest()})
 except PermissionError:
  denied+=1
 except FileNotFoundError:
  errors.append({'path':p,'error':'DISAPPEARED_DURING_SCAN'})
 except OSError as e:
  errors.append({'path':p,'error':type(e).__name__})
print(json.dumps({'matches':matches,'errors':errors,'dangling_symlinks':dangling,'files_read':files,'denied':denied,'complete':True}))
'''


def digests():
    excluded = read_json(ROOT / 'controls' / 'C0.json')['patched_mycelium_sha256']
    values = {read_json(p)['patched_mycelium_sha256'] for p in sorted((ROOT / 'controls').glob('C*.json'))}
    values.add(hashlib.sha256((REPO / 'mycelium.py').read_bytes()).hexdigest())
    values.discard(excluded)
    return sorted(values), excluded


def scan(root):
    from runtime import sandbox, environment
    import sys
    roots = sorted({str(Path(p).resolve()) for p in
                    ('/private/tmp', '/tmp', '/private/var/tmp', '/var/tmp', tempfile.gettempdir())
                    if Path(p).exists()})
    values, excluded = digests()
    request = {'roots': roots, 'markers_hex': [m.hex() for m in MARKERS], 'digests': values}
    result = run([*sandbox(root), sys.executable, '-I', '-c', SCANNER], cwd=root, env=environment(),
                 stdin=json.dumps(request).encode(), timeout=600)
    try:
        observed = json.loads(result['stdout'])
    except ValueError:
        observed = {}
    return {'pass': result['exit_code'] == 0 and not result['timed_out'] and
            observed.get('complete') is True and observed.get('matches') == [] and observed.get('errors') == [],
            'roots': roots, 'markers': [m.decode() for m in MARKERS], 'digests': values,
            'excluded_c0_digest': excluded, 'scan': observed, 'process': result}
