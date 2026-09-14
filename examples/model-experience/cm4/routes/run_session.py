"""One bounded Codex CLI session. No OAuth rewriting; public events only."""
import datetime, hashlib, json, os, signal, subprocess, sys, threading, time
from pathlib import Path

def main(snapshot, output):
    snapshot=Path(snapshot).resolve(); output=Path(output).resolve()
    if not str(snapshot).startswith('/private/tmp/'):
        raise ValueError('snapshot must be outside Projects in /private/tmp')
    output.mkdir(parents=True,exist_ok=False)
    prompt=(snapshot/'task.txt').read_bytes()
    argv=['codex','-a','never','exec','--ephemeral','--ignore-user-config','--ignore-rules',
          '--sandbox','workspace-write','--json','--color','never','--cd',str(snapshot),
          '-c','project_doc_max_bytes=0','-c','model_reasoning_summary="none"',
          '-c','hide_agent_reasoning=true','-c','web_search="disabled"',
          '-c','shell_environment_policy.inherit="core"',
          '-c','shell_environment_policy.experimental_use_profile=false',
          '--enable','skip_host_skill_discovery']
    for feature in ['memories','external_agent_memory_import','plugins','hooks','apps','multi_agent','shell_snapshot','browser_use','computer_use']:
        argv+=['--disable',feature]
    argv+=['--output-last-message',str(output/'final.txt'),'-']
    env={k:v for k,v in os.environ.items() if k in ('HOME','PATH','USER','LOGNAME','SHELL','TMPDIR','LANG','LC_ALL','CODEX_HOME')}
    def git(*args): return subprocess.check_output(['git','-C',str(snapshot),*args],text=True)
    invocation={'argv':argv,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'head_before':git('rev-parse','HEAD').strip(),'status_before':git('status','--porcelain'),
        'prompt_sha256':hashlib.sha256(prompt).hexdigest(),'env_keys':sorted(env),
        'client_version':subprocess.check_output(['codex','--version'],text=True).strip(),
        'context_scope':'New CLI process and public tool trace, not a full outbound-context audit.'}
    (output/'invocation.json').write_text(json.dumps(invocation,indent=2)+'\n')
    omitted=0; timed_out=[]; started=time.monotonic()
    with (output/'stderr.txt').open('wb') as err, (output/'public-events.jsonl').open('wb') as public:
        process=subprocess.Popen(argv,cwd=snapshot,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,start_new_session=True)
        def terminate():
            timed_out.append(True)
            try: os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError: pass
        timer=threading.Timer(600,terminate); timer.start()
        try:
            process.stdin.write(prompt); process.stdin.close()
            for line in process.stdout:
                event=json.loads(line)
                item=event.get('item',{})
                if item.get('type') in ('reasoning','thinking','redacted_thinking'):
                    omitted+=1; continue
                public.write(line); public.flush()
            code=process.wait()
        finally: timer.cancel()
    report={'exit_code':code,'timed_out':bool(timed_out),'elapsed_seconds':time.monotonic()-started,
            'omitted_reasoning_events':omitted,'head_after':git('rev-parse','HEAD').strip(),
            'status_after':git('status','--porcelain'),
            'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'public_trace_scope':'Only public command/file/final events retained; no hidden reasoning requested or stored.'}
    (output/'session.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report)); return code
if __name__=='__main__': sys.exit(main(*sys.argv[1:]))
