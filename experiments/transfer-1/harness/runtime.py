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

def preflight(root):
    root = Path(root).resolve()
    version = run(['codex', '--version'], cwd=root)
    if version['stdout'].strip() != VERSION:
        raise ValueError('CLIENT_VERSION_CHANGED')
    # Use known-existing canaries, not missing paths mistaken for denied reads.
    with tempfile.TemporaryDirectory(prefix='transfer-canary-') as td:
        outside = Path(td).resolve() / 'forbidden.txt'
        outside.write_text('not receiver material')
        (root / 'outside-link').symlink_to(outside)
        try:
            with socket.socket() as server:
                server.bind(('127.0.0.1', 0)); server.listen(1)
                port = server.getsockname()[1]
                code = '''import json, pathlib, socket, subprocess
p=pathlib.Path('probe-write'); p.write_text('ok'); assert p.read_text()=='ok'; p.unlink()
blocked=[]
for p in [pathlib.Path(%r), pathlib.Path('outside-link')]:
 try: p.read_bytes(); blocked.append(False)
 except PermissionError: blocked.append(True)
s=socket.socket(); s.settimeout(1)
try: s.connect(('127.0.0.1', %d)); network=False
except PermissionError: network=True
finally: s.close()
subprocess.run(['git','--version'],check=True,stdout=subprocess.DEVNULL)
print(json.dumps({'write':True,'outside_read_denied':blocked,'network_denied':network}))
''' % (str(outside), port)
                result = run([*sandbox(root), sys.executable, '-I', '-c', code], cwd=root)
                expected = {'write': True, 'outside_read_denied': [True, True], 'network_denied': True}
                result['pass'] = (result['exit_code'] == 0 and not result['timed_out'] and
                                  json.loads(result['stdout'] or 'null') == expected)
                return {'version': version, 'probe': result, 'pass': result['pass']}
        finally:
            (root / 'outside-link').unlink()
