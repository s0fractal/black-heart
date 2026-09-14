"""Pinned CLI tool policy. Provider connection is separate from tool network access."""
import json
import os
import socket
import sys
import tempfile
from pathlib import Path
from common import environment, run

VERSION = 'codex-cli 0.154.0'
MODEL = 'gpt-6-astra'
DISABLED = ['memories', 'external_agent_memory_import', 'plugins', 'hooks', 'apps',
            'multi_agent', 'shell_snapshot', 'browser_use', 'browser_use_external',
            'computer_use']

def settings():
    values = [
        'default_permissions="transfer"',
        'permissions.transfer.filesystem={":minimal"="read", ":workspace_roots"="write", "/opt/homebrew"="read", "/Library/Developer/CommandLineTools"="read"}',
        'permissions.transfer.network.enabled=false',
        'project_doc_max_bytes=0', 'model_reasoning_summary="none"',
        'hide_agent_reasoning=true', 'web_search="disabled"',
        'shell_environment_policy.inherit="none"',
        'shell_environment_policy.experimental_use_profile=false',
        'shell_environment_policy.set={PATH="/opt/homebrew/bin:/Library/Developer/CommandLineTools/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null", LANG="C", LC_ALL="C"}',
        'model_reasoning_effort="medium"',
    ]
    args = [a for value in values for a in ('-c', value)]
    args += ['--enable', 'skip_host_skill_discovery']
    for feature in DISABLED:
        args += ['--disable', feature]
    return args

def sandbox(root):
    return ['codex', *settings(), 'sandbox', '-P', 'transfer', '-C', str(root), '--']

def invocation(root):
    return ['codex', '-a', 'never', *settings(), 'exec', '--ephemeral',
            '--ignore-user-config', '--ignore-rules', '--strict-config',
            '--json', '--color', 'never', '--model', MODEL, '--cd', str(root), '-']

def stale_tmp_snapshots(current):
    """Do not delete unknown files. Refuse to launch with stale experiment inputs."""
    current = Path(current).resolve()
    return sorted(str(p) for pattern in ('receiver-*', 'transfer1-run-*')
                  for p in Path('/private/tmp').glob(pattern) if p.resolve() != current)


def preflight(root, run_root=None):
    root = Path(root).resolve()
    version = run(['codex', '--version'], cwd=root)
    if version['stdout'].strip() != VERSION:
        raise ValueError('CLIENT_VERSION_CHANGED')
    stale = stale_tmp_snapshots(root)
    if stale:
        return {'version': version, 'pass': False, 'stale_tmp_inputs': stale}
    # The real results/archive parent, not the OS-default tempfile location.
    host_parent = Path(run_root) if run_root else Path.home()/'.codex'/'transfer1-preflight'
    host_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='probe-', dir=host_parent) as host_td, \
         tempfile.TemporaryDirectory(prefix='transfer-probe-', dir='/private/tmp') as tmp_td:
        host = Path(host_td).resolve()
        previous = host/'previous-snapshot'/'lesson'/'witness.py'
        previous.parent.mkdir(parents=True); previous.write_text('previous condition canary')
        grade = host/'grade.json'; grade.write_text('grader canary')
        tmp = Path(tmp_td)/'neighbor.txt'; tmp.write_text('public tmp diagnostic')
        (root/'outside-link').symlink_to(previous)
        try:
            with socket.socket() as server:
                server.bind(('127.0.0.1', 0)); server.listen(1)
                port = server.getsockname()[1]
                code = """import json, pathlib, socket, subprocess
p=pathlib.Path('probe-write'); p.write_text('ok'); assert p.read_text()=='ok'; p.unlink()
blocked=[]
for p in [pathlib.Path(%r), pathlib.Path(%r), pathlib.Path('outside-link')]:
 try: p.read_bytes(); blocked.append(False)
 except PermissionError: blocked.append(True)
s=socket.socket(); s.settimeout(1)
try: s.connect(('127.0.0.1', %d)); network=False
except PermissionError: network=True
finally: s.close()
subprocess.run(['git','--version'],check=True,stdout=subprocess.DEVNULL)
try: pathlib.Path(%r).read_bytes(); tmp_readable=True
except PermissionError: tmp_readable=False
print(json.dumps({'write':True,'protected_read_denied':blocked,'loopback_denied':network,'tmp_neighbor_readable':tmp_readable}))
""" % (str(previous), str(grade), port, str(tmp))
                result = run([*sandbox(root), sys.executable, '-I', '-c', code], cwd=root)
                try: observed = json.loads(result['stdout'])
                except ValueError: observed = {}
                result['pass'] = (result['exit_code'] == 0 and not result['timed_out'] and
                    observed.get('write') is True and observed.get('protected_read_denied') == [True]*3 and
                    observed.get('loopback_denied') is True)
                return {'version':version, 'probe':result, 'pass':result['pass'],
                        'stale_tmp_inputs':stale,
                        'placement':'Prior snapshots and grader receipts are protected under the host home; /private/tmp remains readable.'}
        finally:
            (root/'outside-link').unlink()
