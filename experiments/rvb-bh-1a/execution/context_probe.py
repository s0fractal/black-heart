"""Capture native request bodies at a loopback stub. OS denies remote networking.
No request forwarding, no model inference, no credential/header retention.
"""
import argparse
import hashlib
import http.server
import json
import os
import signal
import subprocess
import tempfile
import threading
from pathlib import Path
import runtime

PROFILE='(version 1)(allow default)(deny network*)(allow network-outbound (remote ip "localhost:*"))(allow network-inbound (local ip "localhost:*"))'


def capture(annotator, prompt, parent, home=None, unhardened=False):
    requests=[]
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            body=self.rfile.read(int(self.headers.get('Content-Length','0')))
            try:data=json.loads(body)
            except ValueError:data={'unparsed_body_sha256':hashlib.sha256(body).hexdigest()}
            requests.append({'path':self.path,'body_sha256':hashlib.sha256(body).hexdigest(),
                             'body':{k:data[k] for k in ('model','system','messages','tools') if k in data},
                             'omitted_noncontext_fields':sorted(set(data)-{'model','system','messages','tools'})})
            # Deliberate terminal API refusal; enough to observe the constructed context.
            self.send_response(400);self.send_header('Content-Type','application/json');self.end_headers()
            self.wfile.write(b'{"type":"error","error":{"type":"invalid_request_error","message":"OFFLINE_CONTEXT_PROBE_NO_INFERENCE"}}')
        def do_GET(self):
            self.send_response(404);self.end_headers()
    parent=Path(parent);parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='native-context-',dir=parent) as td:
        workspace=Path(td)
        marker='RVB_CONTEXT_CANARY_7e29cf1'
        (workspace/'CLAUDE.md').write_text(marker)
        (workspace/'AGENTS.md').write_text(marker)
        if home is not None:
            home=Path(home);(home/'.claude').mkdir(parents=True,exist_ok=True)
            (home/'.claude'/'CLAUDE.md').write_text(marker)
            slug=str(workspace).replace('/','-')
            mem=home/'.claude'/'projects'/slug/'memory';mem.mkdir(parents=True,exist_ok=True)
            (mem/'MEMORY.md').write_text(marker)
            (workspace/'.claude').mkdir()
            (workspace/'.claude'/'settings.json').write_text('{"autoMemoryEnabled":true}')
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        env=runtime.environment()
        if home is not None:env['HOME']=str(home)
        url=f'http://127.0.0.1:{server.server_port}'
        argv=runtime.command(annotator,workspace)
        if unhardened:
            if home is None:raise ValueError('UNHARDENED_REQUIRES_SYNTHETIC_HOME')
            argv.remove('--safe-mode')
            pos=argv.index('--settings');del argv[pos:pos+2]
            for name in ('CLAUDE_CODE_DISABLE_AUTO_MEMORY','CLAUDE_CODE_DISABLE_CLAUDE_MDS'):
                env.pop(name,None)
        env.update(ANTHROPIC_BASE_URL=url,ANTHROPIC_API_KEY='offline-not-a-credential',
                   ANTHROPIC_AUTH_TOKEN='',CLAUDE_CODE_MAX_RETRIES='0')
        argv=['/usr/bin/sandbox-exec','-p',PROFILE,*argv]
        process=subprocess.Popen(argv,cwd=workspace,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed_out=False
        try:out,err=process.communicate(prompt.encode(),timeout=40)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(process.pid,signal.SIGKILL);out,err=process.communicate()
        server.shutdown();server.server_close();worker.join()
        return {'annotator':annotator,'requests':requests,'exit_code':process.returncode,'timed_out':timed_out,
                'stdout':out.decode(errors='replace'),'stderr':err.decode(errors='replace'),
                'canary':marker,'workspace':str(workspace),'synthetic_home':str(home) if home else None,'unhardened_control':unhardened,'transport':'loopback stub; sandbox-exec denies remote network',
                'auth_difference':'Dummy API-key transport for capture; native Max login is not forwarded.',
                'projection':'Only model/system/messages/tools retained from request bodies; headers never retained; noncontext fields omitted by name and body digest.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('annotator',choices=['A','B']);p.add_argument('output',type=Path);a=p.parse_args()
    if a.output.exists():raise SystemExit('OUTPUT_EXISTS')
    result=capture(a.annotator,'OFFLINE CONTEXT PROBE. Return only probe-ok.',Path.home()/'rvb-bh-1a-work')
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'requests':len(result['requests']),'exit_code':result['exit_code'],'timed_out':result['timed_out']}))
