"""Offline B1/B2 regression probes; never call a model."""
import json
import shutil
import sys
import tempfile
from pathlib import Path
from common import run
from decision import decide
from grader import grade
from runtime import preflight, sandbox


def crash_checks(directory, prefix=()):
    reports = {}
    for label, source in (
        ('exit_during_call', 'import os\ndef read_source(*args): os._exit(3)\n'),
        ('exit_during_import', 'import os\nos._exit(3)\n'),
    ):
        path=directory/(label+'.py'); path.write_text(source)
        result=grade(path,prefix)
        assert result['valid'] and not result['pass']
        assert all(c['worker_started'] and c['worker']['exit_code']==3 and not c['pass'] for c in result['cases'])
        assert decide([{'arm':'N','pass':result['pass'],'valid':result['valid']}])['status']=='CONTINUE'
        reports[label]=result
    # Trusted prefix exits before Python even starts; this remains infrastructure failure.
    before=grade(directory/'exit_during_call.py',[sys.executable,'-I','-c','import sys; sys.exit(3)'])
    assert not before['valid'] and not before['pass']
    assert all(not c['worker_started'] for c in before['cases'])
    reports['exit_before_worker']=before
    return reports


def isolation_check():
    home=Path.home()/'.codex'/'transfer1-preflight';home.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='host-',dir=home) as host_td, \
         tempfile.TemporaryDirectory(prefix='transfer-next-',dir='/private/tmp') as next_td:
        host=Path(host_td); current=Path(next_td)
        previous=Path(tempfile.mkdtemp(prefix='receiver-',dir='/private/tmp'))
        try:
            (previous/'lesson').mkdir();(previous/'lesson/witness.py').write_text('previous arm canary')
            blocked=preflight(current,host)
            assert not blocked['pass'] and str(previous) in blocked['stale_tmp_inputs']
            archive=host/'previous-snapshot'
            shutil.move(str(previous),str(archive))
            (host/'grade.json').write_text('host grading canary')
            check=preflight(current,host)
            assert check['pass']
            code='''import pathlib,json
result=[]
for name in %r:
 try: pathlib.Path(name).read_bytes(); result.append(False)
 except PermissionError: result.append(True)
print(json.dumps(result))
''' % [str(archive/'lesson/witness.py'),str(host/'grade.json')]
            observed=run([*sandbox(current),sys.executable,'-I','-c',code],cwd=current)
            assert observed['exit_code']==0 and json.loads(observed['stdout'])==[True,True]
            assert not previous.exists()
            return {'pass':True,'stale_snapshot_refused':blocked,
                    'after_archive_preflight':check,'actual_previous_and_grade_denied':observed,
                    'previous_tmp_path_removed':True}
        finally:
            if previous.exists(): shutil.rmtree(previous)
