"""Trusted bounded lifecycle around the existing completion gate.

The gate alone can write weighted reward. This supervisor only invalidates reward on
failure and stops candidate/worker descendants, including children in their own
sessions. SIGKILL of the supervisor itself cannot run Python cleanup; the outer
shell and disposable-container lifecycle remain necessary boundaries.
"""
import argparse
import ctypes
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


LOGS = Path('/logs/verifier')
HERE = Path(__file__).resolve().parent
SIGNALS = []


def interrupted(number, _frame):
    SIGNALS.append(number)
    # Close the small window after the final lifecycle check as well. The gate
    # may still be running, so the ordinary final path invalidates again later.
    fd = None
    try:
        fd = os.open(LOGS / 'reward.txt', os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
        os.write(fd, b'0\n')
    except OSError:
        pass
    finally:
        if fd is not None:
            os.close(fd)


def processes():
    """Read real/effective/saved/fs UIDs, not dumpability-dependent /proc owner."""
    result = {}
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            status = {}
            for line in (path / 'status').read_text().splitlines():
                key, _, value = line.partition(':')
                status[key] = value.strip()
            tail = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            result[int(path.name)] = {
                'ppid': int(status['PPid']),
                'uids': tuple(map(int, status['Uid'].split())),
                'state': tail[0], 'start': tail[19],
            }
        except (FileNotFoundError, ProcessLookupError):
            continue
    return result


def selected(snapshot):
    descendants = {os.getpid()}
    while True:
        more = {pid for pid, item in snapshot.items() if item['ppid'] in descendants}
        if more <= descendants:
            break
        descendants |= more
    descendants.discard(os.getpid())
    candidates = {pid for pid, item in snapshot.items() if 1000 in item['uids']}
    return descendants | candidates


def kill_same_process(pid, identity):
    try:
        tail = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
        if tail[19] == identity['start']:
            os.kill(pid, signal.SIGKILL)
    except (FileNotFoundError, ProcessLookupError):
        pass


def reap():
    count = 0
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if pid == 0:
            break
        count += 1
    return count


def cleanup(seconds=5.0, gate=None):
    deadline = time.monotonic() + seconds
    stopped, adopted = set(), 0
    while True:
        snapshot = processes()
        targets = selected(snapshot)
        for pid in targets:
            if snapshot[pid]['state'] != 'Z':
                kill_same_process(pid, snapshot[pid])
                stopped.add(pid)
        # Let Popen collect its own child first; waitpid(-1) must not consume
        # that status and accidentally make a nonzero exit look successful.
        if gate is not None and gate.returncode is None:
            gate.poll()
        if gate is None or gate.returncode is not None:
            adopted += reap()
        snapshot = processes()
        targets = selected(snapshot)
        live = sorted(pid for pid in targets if snapshot[pid]['state'] != 'Z')
        adopted_zombies = sorted(pid for pid in targets
                                 if snapshot[pid]['state'] == 'Z'
                                 and snapshot[pid]['ppid'] == os.getpid())
        if not live and not adopted_zombies and (gate is None or gate.returncode is not None):
            return {'ok': True, 'stopped_pids': sorted(stopped), 'reaped_children': adopted,
                    'remaining_live_pids': [], 'remaining_adopted_zombies': []}
        if time.monotonic() >= deadline:
            return {'ok': False, 'stopped_pids': sorted(stopped), 'reaped_children': adopted,
                    'remaining_live_pids': live, 'remaining_adopted_zombies': adopted_zombies}
        time.sleep(0.02)


def write_file(path, text):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def supervise(timeout, gate_timeout):
    started = time.monotonic()
    gate = None
    row = {'schema_version': 1, 'pid': os.getpid(), 'gate_exit_code': None,
           'timed_out': False, 'signals': [], 'errors': [], 'cleanup': None,
           'scope': 'trusted lifecycle; only completion.py can award weighted credit'}
    try:
        if os.geteuid() != 0:
            raise RuntimeError('Supervisor requires root; candidate is UID 1000')
        if not all(math.isfinite(value) and value > 0 for value in (timeout, gate_timeout)):
            raise ValueError('Positive finite timeouts are required')
        if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), 'Cannot become child subreaper')
        # This is also fail-closed when invoked directly for an author audit.
        write_file(LOGS / 'reward.txt', '0\n')
        command = [sys.executable, '-I', '-B', str(HERE / 'completion.py'), 'run',
                   '--suite', str(HERE), '--expected', str(HERE / 'expected-tests.json'),
                   '--out-dir', str(LOGS), '--timeout', str(gate_timeout)]
        environment = {key: value for key, value in os.environ.items() if key in {
            'PATH', 'LANG', 'LC_ALL', 'TZ', 'TEMP', 'TMP'}}
        gate = subprocess.Popen(command, cwd='/', env=environment,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        deadline = started + timeout
        while gate.poll() is None:
            if SIGNALS or time.monotonic() >= deadline:
                row['timed_out'] = not SIGNALS
                try:
                    os.killpg(gate.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                # The completion gate handles TERM and stops its pytest group.
                # If it cannot, cleanup below kills all adopted descendants.
                try:
                    gate.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    row['errors'].append('gate_did_not_stop_after_term')
                break
            time.sleep(0.02)
    except Exception as exc:
        row['errors'].append(type(exc).__name__ + ': ' + str(exc))
    finally:
        try:
            row['cleanup'] = cleanup(gate=gate)
        except Exception as exc:
            row['errors'].append('cleanup_error: ' + type(exc).__name__ + ': ' + str(exc))
            row['cleanup'] = {'ok': False}
        if gate is not None:
            row['gate_exit_code'] = gate.poll()
        row['signals'] = list(SIGNALS)
        row['seconds'] = time.monotonic() - started
        row['successful_lifecycle'] = (row['gate_exit_code'] == 0 and not row['timed_out']
                                       and not row['signals'] and not row['errors']
                                       and row['cleanup']['ok'])
        if not row['successful_lifecycle']:
            write_file(LOGS / 'reward.txt', '0\n')
        write_file(LOGS / 'supervision.json', json.dumps(row, indent=2) + '\n')
        # A signal arriving during evidence publication must not preserve credit.
        if SIGNALS:
            write_file(LOGS / 'reward.txt', '0\n')
            row['successful_lifecycle'] = False
            row['signals'] = list(SIGNALS)
            write_file(LOGS / 'supervision.json', json.dumps(row, indent=2) + '\n')
    return 0 if row['successful_lifecycle'] and not SIGNALS else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=float, default=290.0)
    parser.add_argument('--gate-timeout', type=float, default=275.0)
    args = parser.parse_args()
    for name in ('SIGTERM', 'SIGINT', 'SIGHUP'):
        signal.signal(getattr(signal, name), interrupted)
    return supervise(args.timeout, args.gate_timeout)


if __name__ == '__main__':
    raise SystemExit(main())
