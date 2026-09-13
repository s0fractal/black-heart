"""Restore retained outputs against frozen bundles and check them offline."""
import hashlib,json,subprocess,tempfile,zipfile
from pathlib import Path
from check_result import check
HERE=Path(__file__).resolve().parent

def main():
    for name,digest in json.loads((HERE/'prelaunch-sha256.json').read_text()).items():
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==digest,name
    results={}
    with tempfile.TemporaryDirectory() as td:
        for route in ('save','replay'):
            snapshot=Path(td)/route
            subprocess.run(['git','-c','init.templateDir=','clone','-q',str(HERE/(route+'-input.bundle')),str(snapshot)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            retained=HERE/'results'/route
            with zipfile.ZipFile(retained/'generated-files.zip') as archive:
                for name in archive.namelist():
                    parts=Path(name).parts
                    assert parts and not Path(name).is_absolute() and '..' not in parts
                    assert parts[0] in ('store','output') and '.git' not in parts
                    target=snapshot/name
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(archive.read(name))
            for name,digest in json.loads((retained/'artifact-sha256.json').read_text()).items():
                assert hashlib.sha256((retained/name).read_bytes()).hexdigest()==digest,name
            results[route]=check(route,snapshot,retained)
    return {'ok':True,'model_invoked':False,'evaluator_replayed':False,'results':results}
if __name__=='__main__': print(json.dumps(main(),ensure_ascii=False,indent=2))
