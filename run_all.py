"""Single-entry launcher for the demo stack.

Starts the victim service, realtime monitor, and dashboard in the background,
then opens the dashboard in the default browser.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
import webbrowser
import socket
from pathlib import Path


BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
DASHBOARD_URL = "http://127.0.0.1:5002"
PROCESSES: list[tuple[subprocess.Popen, object]] = []
STOP_EVENT = threading.Event()


def is_tcp_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _creation_flags():
    flags = 0
    if os.name == "nt":
        flags |= subprocess.CREATE_NEW_PROCESS_GROUP
        flags |= subprocess.CREATE_NO_WINDOW
    return flags


def start_process(script_name: str, log_name: str, extra_env: dict[str, str] | None = None):
    log_path = LOG_DIR / log_name
    log_handle = open(log_path, "a", encoding="utf-8")
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    process = subprocess.Popen(
        [sys.executable, script_name],
        cwd=str(BASE_DIR),
        stdout=log_handle,
        stderr=log_handle,
        creationflags=_creation_flags(),
        env=env,
    )
    PROCESSES.append((process, log_handle))
    return process


def start_stack():
    print("Starting victim, monitor, and dashboard...", flush=True)
    if is_tcp_port_open(5000):
        print("Victim already appears to be running on port 5000; reusing it.", flush=True)
    else:
        print("Launching victim service...", flush=True)
        start_process("victim.py", "victim.log")
        time.sleep(1.0)

    metrics_path = LOG_DIR / "runtime_metrics.json"
    metrics_age_ok = metrics_path.exists() and (time.time() - metrics_path.stat().st_mtime) < 15
    if metrics_age_ok:
        print("Monitor metrics are fresh; reusing the existing monitor.", flush=True)
    else:
        print("Launching realtime monitor...", flush=True)
        start_process("realtime_monitor.py", "monitor.log")
        time.sleep(1.5)

    dashboard_port = find_free_port()
    global DASHBOARD_URL
    DASHBOARD_URL = f"http://127.0.0.1:{dashboard_port}"
    with (LOG_DIR / "dashboard_url.txt").open("w", encoding="utf-8") as handle:
        handle.write(DASHBOARD_URL)

    print(f"Launching dashboard on port {dashboard_port}...", flush=True)
    start_process("dashboard.py", "dashboard.log", {"DASHBOARD_PORT": str(dashboard_port)})

    for _ in range(20):
        if is_tcp_port_open(dashboard_port):
            break
        time.sleep(0.5)

    try:
        webbrowser.open(DASHBOARD_URL)
    except Exception:
        pass
    print(f"Dashboard opened at {DASHBOARD_URL}", flush=True)
    print("Use the dashboard buttons to launch HTTP, UDP, or SYN attacks.", flush=True)


def shutdown(*_args):
    if STOP_EVENT.is_set():
        return
    STOP_EVENT.set()
    print("Shutting down demo processes...")
    for process, log_handle in PROCESSES:
        try:
            process.terminate()
        except Exception:
            pass
        try:
            log_handle.close()
        except Exception:
            pass


def main():
    LOG_DIR.mkdir(exist_ok=True)
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    start_stack()

    try:
        while not STOP_EVENT.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
