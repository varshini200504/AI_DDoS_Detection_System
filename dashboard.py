from collections import Counter
import json
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template_string


BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "logs" / "security_actions.log"
METRICS_FILE = BASE_DIR / "logs" / "runtime_metrics.json"
PORT = int(os.getenv("DASHBOARD_PORT", "5002"))
MAX_EVENTS = 30

app = Flask(__name__)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Live DDoS Detection Console</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #07111f;
      --panel: rgba(8, 19, 34, 0.86);
      --panel-2: rgba(12, 26, 43, 0.95);
      --line: rgba(129, 185, 255, 0.16);
      --text: #e8f1ff;
      --muted: #8ea4c2;
      --accent: #53d6ff;
      --accent-2: #7cf29a;
      --warning: #ffb84d;
      --danger: #ff6b7d;
      --shadow: 0 24px 80px rgba(0, 0, 0, 0.42);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      background:
        radial-gradient(circle at 20% 20%, rgba(83, 214, 255, 0.16), transparent 28%),
        radial-gradient(circle at 80% 0%, rgba(124, 242, 154, 0.14), transparent 24%),
        linear-gradient(180deg, #05101d, #081421 48%, #040b13);
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
    }

    .wrap {
      max-width: 1600px;
      margin: 0 auto;
      padding: 22px;
    }

    .topbar {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      padding: 18px 22px;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: linear-gradient(135deg, rgba(11, 26, 44, 0.95), rgba(10, 18, 31, 0.88));
      box-shadow: var(--shadow);
      backdrop-filter: blur(20px);
    }

    .brand h1 {
      margin: 0 0 6px;
      font-size: clamp(24px, 3vw, 38px);
      letter-spacing: 0.02em;
    }

    .brand p,
    .subtle {
      margin: 0;
      color: var(--muted);
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.04);
      color: var(--text);
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      font-size: 12px;
    }

    .pill .dot {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: var(--accent-2);
      box-shadow: 0 0 18px rgba(124, 242, 154, 0.9);
    }

    .grid {
      display: grid;
      grid-template-columns: minmax(0, 1.8fr) minmax(340px, 0.95fr);
      gap: 18px;
      margin-top: 18px;
    }

    .stack {
      display: grid;
      gap: 18px;
    }

    .cards {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }

    .card,
    .panel {
      border: 1px solid var(--line);
      border-radius: 22px;
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(20px);
    }

    .card {
      padding: 18px;
      min-height: 116px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .card small {
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 11px;
    }

    .card strong {
      font-size: clamp(24px, 4vw, 38px);
    }

    .card .delta {
      color: var(--accent-2);
      font-size: 13px;
    }

    .panel {
      padding: 18px;
    }

    .panel h2 {
      margin: 0 0 14px;
      font-size: 18px;
    }

    .charts {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }

    .chart-box {
      min-height: 260px;
      border-radius: 18px;
      padding: 14px;
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01));
      border: 1px solid rgba(255, 255, 255, 0.05);
    }

    .chart-box canvas {
      width: 100% !important;
      height: 220px !important;
    }

    .log-list {
      display: grid;
      gap: 10px;
      max-height: 280px;
      overflow: auto;
      padding-right: 4px;
    }

    .log-row {
      display: grid;
      grid-template-columns: 130px minmax(0, 1fr) auto;
      gap: 12px;
      padding: 12px 14px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.035);
      border: 1px solid rgba(255, 255, 255, 0.06);
      align-items: center;
    }

    .log-row .time { color: var(--muted); font-size: 12px; }
    .log-row .attack { color: var(--danger); font-weight: 700; }
    .log-row .ok { color: var(--accent-2); font-weight: 700; }
    .log-row .action { color: var(--warning); font-weight: 700; }

    .sidebar {
      display: grid;
      gap: 18px;
      align-content: start;
    }

    .actions {
      display: grid;
      gap: 12px;
    }

    .action-btn {
      width: 100%;
      border: 0;
      padding: 16px 18px;
      border-radius: 18px;
      color: #04121f;
      font-weight: 800;
      font-size: 15px;
      cursor: pointer;
      transition: transform 0.18s ease, filter 0.18s ease;
    }

    .action-btn:hover { transform: translateY(-1px); filter: brightness(1.04); }
    .action-btn.http { background: linear-gradient(135deg, #66e1ff, #58f0b7); }
    .action-btn.udp { background: linear-gradient(135deg, #ffd66b, #ffb45f); }
    .action-btn.syn { background: linear-gradient(135deg, #ff7b93, #ff9a61); }

    .status-panel {
      display: grid;
      gap: 12px;
    }

    .status-item {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 14px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.06);
      font-size: 14px;
    }

    .bottom {
      margin-top: 18px;
      display: grid;
      gap: 18px;
    }

    .table-wrap {
      overflow: auto;
      border-radius: 18px;
      border: 1px solid rgba(255, 255, 255, 0.06);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 860px;
      background: rgba(0, 0, 0, 0.18);
    }

    th, td {
      padding: 12px 14px;
      text-align: left;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      font-size: 14px;
    }

    th {
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 11px;
      background: rgba(255, 255, 255, 0.02);
      position: sticky;
      top: 0;
      z-index: 1;
    }

    .footer-note {
      color: var(--muted);
      font-size: 12px;
    }

    @media (max-width: 1200px) {
      .grid { grid-template-columns: 1fr; }
      .cards { grid-template-columns: 1fr 1fr; }
      .charts { grid-template-columns: 1fr; }
    }

    @media (max-width: 720px) {
      .wrap { padding: 14px; }
      .topbar { flex-direction: column; align-items: flex-start; }
      .cards { grid-template-columns: 1fr; }
      .log-row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div class="brand">
        <h1>Live DDoS Detection Console</h1>
        <p>Realtime packet capture, adaptive response, and attack simulation in one view.</p>
      </div>
      <div class="pill" id="network-pill"><span class="dot"></span><span id="network-status">NORMAL</span></div>
    </div>

    <div class="grid">
      <div class="stack">
        <div class="cards">
          <div class="card"><small>Captured Packets</small><strong id="captured-packets">0</strong><span class="delta" id="packets-delta">0 in current window</span></div>
          <div class="card"><small>Packet Rate</small><strong id="packet-rate">0</strong><span class="delta">packets / sec</span></div>
          <div class="card"><small>Active Flows</small><strong id="active-flows">0</strong><span class="delta" id="attack-count">0 detections</span></div>
        </div>

        <div class="panel">
          <h2>Live Telemetry</h2>
          <div class="charts">
            <div class="chart-box"><canvas id="rateChart"></canvas></div>
            <div class="chart-box"><canvas id="activityChart"></canvas></div>
          </div>
        </div>

        <div class="panel">
          <h2>Activity Feed</h2>
          <div class="log-list" id="event-stream"></div>
        </div>
      </div>

      <div class="sidebar">
        <div class="panel">
          <h2>Simulation Window</h2>
          <div class="actions">
            <button class="action-btn http" data-attack="http">Launch HTTP Flood</button>
            <button class="action-btn udp" data-attack="udp">Launch UDP Flood</button>
            <button class="action-btn syn" data-attack="syn">Launch SYN Flood</button>
          </div>
          <p class="footer-note" style="margin-top:12px;">Buttons trigger the bundled simulator while the monitor and dashboard keep updating.</p>
        </div>

        <div class="panel status-panel">
          <h2>Device Status</h2>
          <div class="status-item"><span>Protected Host</span><strong>{{ monitored_ip }}</strong></div>
          <div class="status-item"><span>Protected Ports</span><strong>{{ protected_ports }}</strong></div>
          <div class="status-item"><span>Latest Attack</span><strong id="latest-attack">None</strong></div>
          <div class="status-item"><span>Latest Action</span><strong id="latest-action">MONITOR</strong></div>
          <div class="status-item"><span>Confidence</span><strong id="latest-confidence">0.00</strong></div>
        </div>
      </div>
    </div>

    <div class="bottom">
      <div class="panel">
        <h2>Detection Log</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Source IP</th>
                <th>Attack Type</th>
                <th>Action</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody id="log-table"></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <script>
    const rateCtx = document.getElementById('rateChart');
    const activityCtx = document.getElementById('activityChart');
    const labels = [];
    const packetSeries = [];
    const cpuSeries = [];

    const rateChart = new Chart(rateCtx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Packet Rate',
            data: packetSeries,
            borderColor: '#53d6ff',
            backgroundColor: 'rgba(83, 214, 255, 0.12)',
            tension: 0.32,
            fill: true,
          },
          {
            label: 'CPU %',
            data: cpuSeries,
            borderColor: '#7cf29a',
            backgroundColor: 'rgba(124, 242, 154, 0.10)',
            tension: 0.32,
            fill: true,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#dfeaff' } } },
        scales: {
          x: { ticks: { color: '#8ea4c2' }, grid: { color: 'rgba(255,255,255,0.06)' } },
          y: { ticks: { color: '#8ea4c2' }, grid: { color: 'rgba(255,255,255,0.06)' } }
        }
      }
    });

    const activityChart = new Chart(activityCtx, {
      type: 'doughnut',
      data: {
        labels: ['Normal', 'Alert', 'Blocked'],
        datasets: [{
          data: [1, 1, 1],
          backgroundColor: ['#7cf29a', '#ffb84d', '#ff6b7d'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#dfeaff' } } }
      }
    });

    function formatNumber(value) {
      if (value === null || value === undefined) return '0';
      if (Number.isInteger(value)) return String(value);
      return Number(value).toFixed(2);
    }

    function statusFromSnapshot(snapshot) {
      const lastDetection = snapshot.last_detection_epoch || 0;
      if (!lastDetection) return 'NORMAL';
      const age = Date.now() / 1000 - lastDetection;
      return age < 12 ? 'ATTACK ACTIVE' : 'NORMAL';
    }

    function renderLogs(events) {
      const rows = events.map((event) => `
        <tr>
          <td>${event.timestamp || ''}</td>
          <td>${event.ip || ''}</td>
          <td class="${event.attack !== 'Normal' ? 'attack' : 'ok'}">${event.attack || ''}</td>
          <td class="action">${event.action || ''}</td>
          <td>${event.confidence || ''}</td>
        </tr>
      `).join('');
      document.getElementById('log-table').innerHTML = rows || '<tr><td colspan="5">No detection events yet.</td></tr>';
    }

    function renderStream(events) {
      const rows = events.slice(0, 8).map((event) => `
        <div class="log-row">
          <div class="time">${event.timestamp || ''}</div>
          <div>
            <div><strong>${event.ip || ''}</strong> ${event.attack ? '• ' + event.attack : ''}</div>
            <div class="subtle">${event.action || 'MONITOR'} · Confidence ${event.confidence || '0.00'}</div>
          </div>
          <div class="${event.action === 'BLOCK' ? 'attack' : 'action'}">${event.action || ''}</div>
        </div>
      `).join('');
      document.getElementById('event-stream').innerHTML = rows || '<div class="subtle">Waiting for live traffic...</div>';
    }

    async function triggerAttack(type) {
      const response = await fetch(`/api/attack/${type}`, { method: 'POST' });
      const data = await response.json();
      if (!response.ok) {
        alert(data.error || 'Failed to start attack.');
      }
    }

    async function refreshDashboard() {
      const response = await fetch('/api/state');
      const state = await response.json();
      const metrics = state.metrics || {};
      const summary = state.summary || {};

      document.getElementById('captured-packets').textContent = formatNumber(metrics.captured_packets_total || 0);
      document.getElementById('packet-rate').textContent = formatNumber(metrics.window_packet_rate || 0);
      document.getElementById('active-flows').textContent = formatNumber(metrics.active_flows || 0);
      document.getElementById('packets-delta').textContent = `${formatNumber(metrics.window_packets || 0)} packets in window`;
      document.getElementById('attack-count').textContent = `${formatNumber(summary.attack_events || 0)} detections logged`;
      document.getElementById('latest-attack').textContent = metrics.last_attack || 'None';
      document.getElementById('latest-action').textContent = metrics.last_action || 'MONITOR';
      document.getElementById('latest-confidence').textContent = formatNumber(metrics.last_confidence || 0);
      document.getElementById('network-status').textContent = statusFromSnapshot(metrics);
      document.getElementById('network-pill').style.borderColor = metrics.last_action === 'BLOCK' ? 'rgba(255,107,125,0.48)' : 'rgba(124,242,154,0.34)';

      const label = new Date().toLocaleTimeString();
      labels.push(label);
      packetSeries.push(Number(metrics.window_packet_rate || 0));
      cpuSeries.push(Number(metrics.cpu_usage || 0));
      if (labels.length > 18) {
        labels.shift();
        packetSeries.shift();
        cpuSeries.shift();
      }
      rateChart.update();

      const normal = Number(summary.normal_events || 0);
      const alert = Number(summary.rate_limit_events || 0) + Number(summary.honeypot_events || 0);
      const blocked = Number(summary.block_events || 0);
      activityChart.data.datasets[0].data = [Math.max(normal, 1), Math.max(alert, 1), Math.max(blocked, 1)];
      activityChart.update();

      renderStream(state.events || []);
      renderLogs(state.events || []);
    }

    document.querySelectorAll('[data-attack]').forEach((button) => {
      button.addEventListener('click', () => triggerAttack(button.dataset.attack));
    });

    refreshDashboard();
    setInterval(refreshDashboard, 2000);
  </script>
</body>
</html>
"""


def load_json(path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def parse_logs():
    events = []
    if not LOG_FILE.exists():
        return events

    try:
        with LOG_FILE.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()[-150:]
    except Exception:
        return events

    for line in lines:
        try:
            log_obj = json.loads(line.strip())
        except Exception:
            continue

        message = log_obj.get("message", "")
        if "Attack=" not in message:
          continue
        parts = [part.strip() for part in message.split(" | ") if part.strip()]
        if not parts:
            continue

        event = {
            "timestamp": log_obj.get("timestamp", ""),
            "ip": parts[0],
            "attack": "Normal",
            "action": "MONITOR",
            "confidence": "0.00",
        }

        for part in parts[1:]:
            if part.startswith("Attack="):
                event["attack"] = part.replace("Attack=", "").strip()
            elif part.startswith("Action="):
                event["action"] = part.replace("Action=", "").strip()
            elif part.startswith("Confidence="):
                event["confidence"] = part.replace("Confidence=", "").strip()

        events.append(event)

    return list(reversed(events))[:MAX_EVENTS]


def build_summary(events):
    attack_events = sum(1 for event in events if event.get("attack") not in {"Normal", "", None})
    action_counts = Counter(event.get("action", "MONITOR") for event in events)
    attack_counts = Counter(event.get("attack", "Normal") for event in events)

    return {
        "total_events": len(events),
        "attack_events": attack_events,
        "normal_events": action_counts.get("MONITOR", 0),
        "rate_limit_events": action_counts.get("RATE_LIMIT", 0),
        "honeypot_events": action_counts.get("HONEYPOT", 0),
        "block_events": action_counts.get("BLOCK", 0),
        "attack_counts": attack_counts,
    }


def read_state():
    metrics = load_json(METRICS_FILE, {})
    events = parse_logs()
    summary = build_summary(events)
    metrics.setdefault("captured_packets_total", 0)
    metrics.setdefault("window_packets", 0)
    metrics.setdefault("window_packet_rate", 0)
    metrics.setdefault("active_flows", 0)
    metrics.setdefault("cpu_usage", 0)
    metrics.setdefault("last_attack", "None")
    metrics.setdefault("last_action", "MONITOR")
    metrics.setdefault("last_confidence", 0)
    metrics.setdefault("last_detection_epoch", 0)
    return {
        "metrics": metrics,
        "events": events,
        "summary": summary,
    }


def start_attack_process(attack_type):
    choices = {"http": "1", "udp": "2", "syn": "3"}
    if attack_type not in choices:
        raise ValueError("Invalid attack type")

    log_path = BASE_DIR / "logs" / f"attack_{attack_type}.log"
    with log_path.open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [sys.executable, "attack_simulator.py"],
            cwd=str(BASE_DIR),
            stdin=subprocess.PIPE,
            stdout=log_file,
            stderr=log_file,
            text=True,
        )
        process.communicate(choices[attack_type] + "\n")


@app.route("/")
def dashboard():
    return render_template_string(
        HTML_TEMPLATE,
        monitored_ip="192.168.1.4",
        protected_ports="5000, 5001, 8081, 80",
    )


@app.route("/api/state")
def api_state():
    return jsonify(read_state())


@app.route("/api/attack/<attack_type>", methods=["POST"])
def api_attack(attack_type):
    try:
        threading.Thread(target=start_attack_process, args=(attack_type,), daemon=True).start()
        return jsonify({"ok": True, "attack": attack_type})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


if __name__ == "__main__":
    os.makedirs(BASE_DIR / "logs", exist_ok=True)
    print("Starting dashboard...")
    print(f"Open browser: http://127.0.0.1:{PORT}")
    try:
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    except Exception:
        pass
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
