"""Fail-closed content scan executed with the receiver's actual read permissions."""
import hashlib
import json
import tempfile
from pathlib import Path
from common import ROOT, run
from controls import sources

# Sent over stdin, not written into readable temporary storage.
SCANNER = r'''import hashlib,json,os,stat,sys
request=json.load(sys.stdin)
markers=[bytes.fromhex(x) for x in request['markers_hex']]
digests=set(request['digests'])
seen=set();matches=[];errors=[];files=0;denied=0
stack=list(request['roots'])
while stack:
 p=stack.pop()
 try:
  info=os.stat(p)
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
print(json.dumps({'matches':matches,'errors':errors,'files_read':files,'denied':denied,'complete':True}))
'''


def scan(root):
    from runtime import sandbox
    import sys
    roots=sorted({str(Path(p).resolve()) for p in
                  ('/private/tmp','/tmp','/private/var/tmp','/var/tmp',tempfile.gettempdir())
                  if Path(p).exists()})
    markers=[b'transfer-1',b'transfer1',(ROOT/'inputs/lesson/lesson.txt').read_bytes().strip().lower()]
    digests=sorted({hashlib.sha256(s.encode()).hexdigest() for s in sources().values()})
    request={'roots':roots,'markers_hex':[m.hex() for m in markers],'digests':digests}
    result=run([*sandbox(root),sys.executable,'-I','-c',SCANNER],cwd=root,
               stdin=json.dumps(request).encode(),timeout=60)
    try: observed=json.loads(result['stdout'])
    except ValueError: observed={}
    return {'pass':result['exit_code']==0 and not result['timed_out'] and
            observed.get('complete') is True and observed.get('matches')==[] and observed.get('errors')==[],
            'roots':roots,'scan':observed,'process':result}
