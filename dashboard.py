from flask import Flask, render_template_string, jsonify
import os
import threading
import time

# ==========================
# CONFIG
# ==========================
LOG_FILE = os.path.join("logs", "security_actions.log")
REFRESH_INTERVAL = 2  # seconds
PORT = 5002

app = Flask(__name__)

# ==========================
# HTML TEMPLATE
# ==========================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>DDoS Detection Dashboard</title>
    <meta http-equiv="refresh" content="2">
    <style>
        body {
            font-family: Arial;
            background-color: #111;
            color: #eee;
            margin: 20px;
        }

        h1 {
            color: #00ff99;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        th, td {
            padding: 10px;
            border: 1px solid #444;
            text-align: center;
        }

        th {
            background-color: #222;
        }

        tr:nth-child(even) {
            background-color: #1b1b1b;
        }

        .attack {
            color: red;
            font-weight: bold;
        }

        .normal {
            color: lightgreen;
        }

        .honeypot {
            color: orange;
        }

        .block {
            color: crimson;
        }

        .rate {
            color: yellow;
        }
    </style>
</head>
<body>

    <h1>🚨 Real-Time DDoS Detection Dashboard 🚨</h1>

    <p>Total Logged Events: {{ total_events }}</p>

    <table>
        <tr>
            <th>Timestamp</th>
            <th>Source IP</th>
            <th>Attack Type</th>
            <th>Action Taken</th>
            <th>Confidence</th>
        </tr>

        {% for event in events %}
        <tr>
            <td>{{ event.timestamp }}</td>

            <td>{{ event.ip }}</td>

            <td class="{% if event.attack != 'Normal' %}attack{% else %}normal{% endif %}">
                {{ event.attack }}
            </td>

            <td class="
                {% if event.action == 'BLOCK' %}block
                {% elif event.action == 'HONEYPOT' %}honeypot
                {% elif event.action == 'RATE_LIMIT' %}rate
                {% endif %}
            ">
                {{ event.action }}
            </td>

            <td>{{ event.confidence }}</td>
        </tr>
        {% endfor %}
    </table>

</body>
</html>
"""

# ==========================
# LOG PARSER
# ==========================
def parse_logs():
    import json
    events = []

    if not os.path.exists(LOG_FILE):
        return events

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in reversed(lines[-100:]):  # Last 100 events
        try:
            # Parse JSON log entry
            log_obj = json.loads(line.strip())
            timestamp = log_obj.get("timestamp", "Unknown")
            message = log_obj.get("message", "")

            # Extract IP and attack details from message
            # Format: "192.168.1.4 | Attack=UDP | Action=RATE_LIMIT | Confidence=0.83"
            parts = message.split(" | ")

            ip = parts[0].strip() if parts else "Unknown"

            attack = "Unknown"
            action = "Unknown"
            confidence = "N/A"

            for part in parts[1:]:
                if "Attack=" in part:
                    attack = part.replace("Attack=", "").strip()

                elif "Action=" in part:
                    action = part.replace("Action=", "").strip()

                elif "Confidence=" in part:
                    confidence = part.replace("Confidence=", "").strip()

            events.append({
                "timestamp": timestamp,
                "ip": ip,
                "attack": attack,
                "action": action,
                "confidence": confidence
            })

        except:
            continue

    return events

# ==========================
# ROUTES
# ==========================
@app.route("/")
def dashboard():
    events = parse_logs()

    return render_template_string(
        HTML_TEMPLATE,
        events=events,
        total_events=len(events)
    )

@app.route("/api/logs")
def api_logs():
    return jsonify(parse_logs())

# ==========================
# MAIN
# ==========================
if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)

    print("Starting dashboard...")
    print(f"Open browser: http://127.0.0.1:{PORT}")

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )