"""Optional deterministic local witness for the lesson. No network or source patch."""
import json, os, subprocess, tempfile
from pathlib import Path

def main():
    with tempfile.TemporaryDirectory(dir='.') as td:
        root=Path(td).resolve()
        env=dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                 GIT_AUTHOR_DATE='2000-01-01T00:00:00+00:00', GIT_COMMITTER_DATE='2000-01-01T00:00:00+00:00')
        def git(*args):
            return subprocess.check_output(['git','-C',str(root),*args],env=env,stderr=subprocess.PIPE)
        git('-c','init.templateDir=','init','-q')
        (root/'source.txt').write_bytes(b'local source witness\n')
        git('add','source.txt')
        git('-c','user.name=TRANSFER fixture','-c','user.email=transfer@example.invalid',
            '-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null','commit','-qm','source')
        commit=git('rev-parse','HEAD').decode().strip()
        tree=git('rev-parse','HEAD^{tree}').decode().strip()
        result={'commit_type':git('cat-file','-t',commit).decode().strip(),
                'tree_type':git('cat-file','-t',tree).decode().strip(),
                'same_path_bytes':git('show',commit+':source.txt')==git('show',tree+':source.txt')}
        print(json.dumps(result,sort_keys=True))
if __name__=='__main__': main()
