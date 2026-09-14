"""Freeze independent input bundles and a single run directory before review."""
import argparse
import json
import tempfile
import uuid
from pathlib import Path
from common import ROOT, PLAN_HEAD, git, sha, verify_inputs, write_json
from decision import SCHEDULE
from runtime import VERSION, MODEL, settings


def prepare(output):
    output=output.resolve()
    if any(output.is_relative_to(Path(p).resolve()) for p in ('/private/tmp','/private/var/tmp',tempfile.gettempdir())):
        raise ValueError('PACKAGE_OUTPUT_MUST_BE_OUTSIDE_TEMP_STORAGE')
    inputs = verify_inputs()
    output.mkdir(parents=True, exist_ok=False)
    arms = {}
    for arm in 'NTP':
        build_root=Path.home()/'transfer1-work'/'build';build_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='snapshot-', dir=build_root) as td:
            snapshot = Path(td)
            mapping = {p.name: p for p in (ROOT/'inputs/common').iterdir()}
            if arm in 'TP':
                mapping['lesson/lesson.txt'] = ROOT/'inputs/lesson/lesson.txt'
            if arm == 'P':
                for name in ('witness.py', 'manifest.json'):
                    mapping['lesson/'+name] = ROOT/'inputs/packet'/name
            for name, source in mapping.items():
                target=snapshot/name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
            git(snapshot, '-c', 'init.templateDir=', 'init', '-q', '--object-format=sha1')
            git(snapshot, 'add', '.')
            git(snapshot, 'commit', '-qm', 'receiver input')
            bundle=output.resolve()/(arm+'.bundle')
            git(snapshot, 'bundle', 'create', str(bundle), 'HEAD')
            arms[arm]={'bundle':bundle.name, 'sha256':sha(bundle),
                       'head':git(snapshot,'rev-parse','HEAD'),
                       'files':{name:sha(source) for name,source in sorted(mapping.items())}}
    frozen={'plan_head':PLAN_HEAD,'preparation_head':git(ROOT,'rev-parse','HEAD'),
            'run_root':str(Path.home()/'transfer1-runs'/uuid.uuid4().hex),
            'model':MODEL, 'client_version':VERSION, 'settings':settings(),
            'timeout_seconds':300,'schedule':list(SCHEDULE),'inputs':inputs,'arms':arms,
            'harness':{p.name:sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
            'status':'PREPARED_NOT_LAUNCHED; exact package commit requires review'}
    write_json(output/'freeze.json',frozen)
    return frozen

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path)
    print(json.dumps(prepare(parser.parse_args().output),indent=2))
