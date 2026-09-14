"""Offline bundle readback: exact files, one-commit history, no cross-arm inputs."""
import argparse
import json
import tempfile
from pathlib import Path
from common import git, sha, write_json


def verify(package):
    frozen=json.loads((package/'freeze.json').read_text())
    results={}
    for arm, data in frozen['arms'].items():
        bundle=(package/data['bundle']).resolve()
        assert sha(bundle)==data['sha256']
        with tempfile.TemporaryDirectory(prefix='receiver-',dir='/private/tmp') as td:
            root=Path(td)
            git(root,'-c','init.templateDir=','init','-q','--object-format=sha1')
            git(root,'bundle','verify',str(bundle))
            git(root,'bundle','unbundle',str(bundle))
            git(root,'checkout','--detach',data['head'])
            assert git(root,'rev-list','--count','HEAD')=='1'
            tracked=git(root,'ls-files').splitlines()
            assert tracked==sorted(data['files'])
            assert all(sha(root/name)==digest for name,digest in data['files'].items())
            assert not (root/'.git/FETCH_HEAD').exists()
            assert not git(root,'remote')
            assert not git(root,'status','--porcelain')
            results[arm]={'pass':True,'head':data['head'],'files':tracked,'history_commits':1}
    assert frozen['arms']['T']['files']['lesson/lesson.txt']==frozen['arms']['P']['files']['lesson/lesson.txt']
    return {'pass':True,'freeze_sha256':sha(package/'freeze.json'),'arms':results}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('package',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();write_json(args.output,verify(args.package))
    print('Prepared bundle readback passed; no receiver called.')
