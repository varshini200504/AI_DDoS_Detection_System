"""Orchestrator to run victim, honeypot, monitor, and dashboard concurrently via subprocesses.
This is intended for local demo/test use. Run as admin for monitor/firewall actions.
"""
import subprocess
import signal
import sys
import os
from time import sleep

PROCESSES = []

def start_process(cmd, logfile):
    logf = open(logfile, 'a')
    p = subprocess.Popen(cmd, shell=True, stdout=logf, stderr=logf)
    PROCESSES.append((p, logf))
    return p

def main():
    cwd = os.path.dirname(__file__)

    print("Starting orchestration: victim, honeypot, monitor, dashboard")

    start_process('python victim.py', 'logs/victim.log')
    sleep(1)
    start_process('python honeypot.py', 'logs/honeypot_service.log')
    sleep(1)
    start_process('python realtime_monitor.py', 'logs/monitor.log')
    sleep(1)
    start_process('python dashboard.py', 'logs/dashboard.log')

    def shutdown(signum, frame):
        print('Shutting down processes...')
        for p, f in PROCESSES:
            try:
                p.terminate()
            except Exception:
                pass
            try:
                f.close()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)

if __name__ == '__main__':
    os.makedirs('logs', exist_ok=True)
    main()
