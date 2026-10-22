"""Trusted subprocess boundary; no candidate code enters the pytest process."""
import ctypes
import json
import math
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import time

ENTRY = '/app/heat.py'
LIMIT = 2_000_000
BUDGET = 240.0


def stop_candidates():
    deadline = time.monotonic() + 5
    while True:
        live = False
        for item in Path('/proc').iterdir():
            if item.name.isdecimal():
                try:
                    status = dict(line.split(':', 1) for line in item.joinpath('status').read_text().splitlines() if ':' in line)
                    if 1000 in [int(value) for value in status['Uid'].split()]:
                        # Zombies cannot fork or mutate files and are reaped below.
                        if status['State'].lstrip().startswith('Z'):
                            continue
                        live = True
                        os.kill(int(item.name), signal.SIGKILL)
                except (ProcessLookupError, FileNotFoundError, PermissionError):
                    pass
        if not live:
            return
        if time.monotonic() > deadline:
            raise RuntimeError('Candidate descendants could not be stopped')
        time.sleep(0.01)


def reap():
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            if not pid:
                return
        except ChildProcessError:
            return


def read_bytes(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > LIMIT:
            raise ValueError('Output must be a bounded regular JSON file')
        result = stream.read(LIMIT + 1)
        if len(result) > LIMIT:
            raise ValueError('Oversized result')
        return result


def read_json(path):
    result = json.loads(read_bytes(path).decode('utf-8-sig'), parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    def finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('Nonfinite JSON')
        if isinstance(value, dict):
            for item in value.values():
                finite(item)
        elif isinstance(value, list):
            for item in value:
                finite(item)
    finite(result)
    return result


def invoke(data, seconds):
    row = {'returncode': None, 'errors': [], 'seconds': 0, 'output': None}
    with tempfile.TemporaryDirectory(prefix='heat-') as directory:
        work = Path(directory)
        os.chown(work,1000,1000)
        os.chmod(work,0o700)
        source = work/'input.json'
        before = json.dumps(data,ensure_ascii=False,allow_nan=False).encode('utf-8')
        source.write_bytes(before)
        os.chmod(source,0o444)
        output_dir = work/'reports'
        output_dir.mkdir()
        os.chown(output_dir,1000,1000)
        os.chmod(output_dir,0o700)
        output = output_dir/'output.json'
        marker = b'previous complete result\n'
        output.write_bytes(marker)
        os.chown(output,1000,1000)
        os.chmod(output,0o600)
        started=time.monotonic()
        process=subprocess.Popen([sys.executable,'-B',ENTRY,str(source),str(output)],
            cwd='/app',stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            user=1000,group=1000,extra_groups=[],start_new_session=True,
            env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/home/solver','LANG':'C.UTF-8',
                 'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1',
                 'PYTHONDONTWRITEBYTECODE':'1'})
        try:
            row['returncode']=process.wait(timeout=max(0.001,seconds))
        except subprocess.TimeoutExpired:
            row['errors'].append('240 second batch budget exhausted')
        finally:
            # Stop descendants before reading results: output cannot keep changing.
            stop_candidates()
            process.wait()
            reap()
            row['seconds']=time.monotonic()-started
        try:
            if row['returncode']==0:
                row['output']=read_json(output)
        except (OSError,ValueError,TypeError,OverflowError,RecursionError) as exc:
            row['errors'].append('Invalid output: '+type(exc).__name__)
        finally:
            os.chmod(output_dir,0o700)
    return row


def run_cases(records, verify):
    if os.geteuid()!=0:
        raise RuntimeError('Trusted verifier requires root, candidate uses UID 1000')
    names=[record['id'] for record in records]
    if not names or len(names)!=len(set(names)) or len(names)>29:
        raise RuntimeError('Invalid scientific case set')
    if ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0)!=0:
        raise OSError(ctypes.get_errno(),'Cannot become child subreaper')
    stop_candidates()
    used=0.0
    rows={}
    for record in records:
        if used>=BUDGET:
            row={'returncode':None,'errors':['240 second batch budget exhausted'],'seconds':0,'output':None}
        else:
            row=invoke(record['input'],BUDGET-used)
            used+=row['seconds']
            if row['returncode']==0 and row['output'] is not None:
                row['errors'].extend(verify(record['input'],row['output'],record['expected']))
        rows[record['id']]=row
    report={'scientific_cases':len(records),'candidate_seconds':used,'cases':rows}
    Path('/logs/verifier/candidate-details.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return rows
