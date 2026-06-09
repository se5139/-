from __future__ import annotations

import os
import platform
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, shell=True)


def stop_windows(port: int) -> int:
    # netstat output: TCP 127.0.0.1:8520 ... LISTENING 1234
    result = run(f'netstat -ano | findstr :{port}')
    pids = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 5 and (f':{port}' in parts[1] or f':{port}' in parts[2]):
            pid = parts[-1]
            if pid.isdigit():
                pids.add(pid)
    killed = 0
    for pid in pids:
        task = run(f'taskkill /F /PID {pid}')
        if task.returncode == 0:
            killed += 1
    return killed


def stop_unix(port: int) -> int:
    result = run(f'lsof -ti tcp:{port}')
    pids = [p.strip() for p in result.stdout.splitlines() if p.strip().isdigit()]
    killed = 0
    for pid in pids:
        try:
            os.kill(int(pid), 9)
            killed += 1
        except Exception:
            pass
    return killed


def main() -> None:
    ports = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else [8520]
    total = 0
    is_windows = platform.system().lower().startswith('win')
    for port in ports:
        killed = stop_windows(port) if is_windows else stop_unix(port)
        print(f'port {port}: stopped {killed} process(es)')
        total += killed
    if total == 0:
        print('No process needed to be stopped.')


if __name__ == '__main__':
    main()
