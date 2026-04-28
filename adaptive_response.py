import os
import time
import socket
import threading
import logging
from datetime import datetime

# ==========================
# CONFIG
# ==========================
LOG_DIR = "logs"
HONEYPOT_PORT = 8080
HONEYPOT_HOST = "0.0.0.0"

# Windows firewall block command
# Requires admin terminal
WINDOWS_BLOCK_CMD = 'netsh advfirewall firewall add rule name="DDoS_Block_{ip}" dir=in action=block remoteip={ip}'

# ==========================
# SETUP
# ==========================
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "security_actions.log"),
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

# ==========================
# LOGGING
# ==========================
def log_action(ip, attack_type, action, confidence):
    log_entry = (
        f"IP={ip} | Attack={attack_type} | "
        f"Action={action} | Confidence={confidence:.2f}"
    )

    print(log_entry)
    logging.info(log_entry)

# ==========================
# RATE LIMIT (Simulated)
# ==========================
def rate_limit_ip(ip):
    print(f"[RATE LIMIT] Applied to {ip}")

# ==========================
# BLOCK IP (REAL Windows Firewall)
# ==========================
def block_ip(ip):
    try:
        cmd = WINDOWS_BLOCK_CMD.format(ip=ip)
        os.system(cmd)

        print(f"[BLOCKED] {ip}")

    except Exception as e:
        print(f"Error blocking IP {ip}: {e}")

# ==========================
# HONEYPOT REDIRECT (logical)
# ==========================
def redirect_to_honeypot(ip):
    print(f"[HONEYPOT REDIRECT] {ip} redirected to honeypot:{HONEYPOT_PORT}")

# ==========================
# HONEYPOT SERVER
# ==========================
def honeypot_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HONEYPOT_HOST, HONEYPOT_PORT))
    server.listen(5)

    print(f"[HONEYPOT] Running on port {HONEYPOT_PORT}")

    while True:
        client, addr = server.accept()

        attacker_ip = addr[0]

        log_entry = f"HONEYPOT CAPTURED: {attacker_ip}"

        print(log_entry)
        logging.info(log_entry)

        try:
            fake_banner = b"Fake vulnerable service\r\n"
            client.send(fake_banner)

        except:
            pass

        client.close()

# ==========================
# START HONEYPOT THREAD
# ==========================
def start_honeypot():
    thread = threading.Thread(
        target=honeypot_server,
        daemon=True
    )
    thread.start()

# ==========================
# ADAPTIVE RESPONSE ENGINE
# ==========================
def adaptive_response(ip, attack_type, confidence):
    """
    confidence:
    0.0 → 1.0
    """

    # Low threat
    if confidence < 0.60:
        action = "MONITOR"

    # Medium threat
    elif confidence < 0.85:
        action = "RATE_LIMIT"
        rate_limit_ip(ip)

    # High threat
    else:
        # Protocol-specific stronger actions
        if attack_type in [
            "Syn",
            "UDP",
            "UDPLag",
            "Portmap"
        ]:
            action = "BLOCK"
            block_ip(ip)

        elif attack_type in [
            "DrDoS_DNS",
            "DrDoS_NTP",
            "DrDoS_SNMP",
            "DrDoS_SSDP"
        ]:
            action = "HONEYPOT"
            redirect_to_honeypot(ip)

        else:
            action = "BLOCK"
            block_ip(ip)

    # Log
    log_action(
        ip,
        attack_type,
        action,
        confidence
    )

    return action

start_honeypot()
while True:
    time.sleep(1)