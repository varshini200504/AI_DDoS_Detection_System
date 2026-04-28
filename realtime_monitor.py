import time
import joblib
import psutil
import numpy as np
import pandas as pd
import threading
import logging
from collections import defaultdict
from scapy.all import sniff, IP, TCP, UDP

# ==========================
# CONFIG
# ==========================
WINDOW_SIZE = 3
INTERFACE = "Intel(R) Wi-Fi 6 AX200 160MHz"

BINARY_MODEL_PATH = "binary_ddos_model.pkl"
MULTICLASS_MODEL_PATH = "best_ddos_model.pkl"
SCALER_PATH = "binary_feature_scaler.pkl"

# YOUR DEFENDER MACHINE IP
MONITORED_IP = "192.168.1.4"

# Only monitor traffic targeting your services
MONITORED_PORTS = {5000, 8080, 80}

# Detection strictness
MIN_PACKETS_THRESHOLD = 10
BINARY_CONFIDENCE_THRESHOLD = 0.75

# Safe infrastructure
SAFE_IPS = {
    "127.0.0.1",
    "0.0.0.0",
    "255.255.255.255",
    "192.168.1.1"
}

# Logging
LOG_FILE = "logs/security_actions.log"

# ==========================
# FEATURE NAMES
# ==========================
FEATURE_NAMES = [
    "Flow Duration",
    "Flow Packets/s",
    "Flow Bytes/s",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Packet Length Mean",
    "Packet Length Std",
    "Average Packet Size",
    "SYN Flag Count",
    "ACK Flag Count",
    "RST Flag Count",
    "PSH Flag Count",
    "Down/Up Ratio",
    "Destination Port",
    "Protocol"
]

# ==========================
# LABEL MAP
# ==========================
attack_label_map = {
    0: "Normal",
    1: "DrDoS_DNS",
    2: "DrDoS_NTP",
    3: "DrDoS_SNMP",
    4: "DrDoS_SSDP",
    5: "LDAP",
    6: "MSSQL",
    7: "NetBIOS",
    8: "Portmap",
    9: "Syn",
    10: "TFTP",
    11: "UDP",
    12: "UDPLag"
}

# ==========================
# LOAD MODELS
# ==========================
print("Loading models...")

binary_model = joblib.load(BINARY_MODEL_PATH)
multiclass_model = joblib.load(MULTICLASS_MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

print("Models loaded successfully!")

# ==========================
# LOGGING SETUP
# ==========================
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - IP=%(message)s"
)

# ==========================
# FLOW STORAGE
# ==========================
flow_stats = defaultdict(lambda: {
    "start_time": None,
    "last_time": None,
    "fwd_packets": 0,
    "bwd_packets": 0,
    "fwd_bytes": 0,
    "bwd_bytes": 0,
    "packet_lengths": [],
    "syn_count": 0,
    "ack_count": 0,
    "rst_count": 0,
    "psh_count": 0,
    "dest_port": 0,
    "protocol": 0
})

# ==========================
# PACKET CAPTURE
# ==========================
def process_packet(packet):
    if IP not in packet:
        return

    src_ip = packet[IP].src
    dst_ip = packet[IP].dst

    # Ignore safe infrastructure
    if src_ip in SAFE_IPS:
        return

    # ONLY monitor packets aimed at protected machine
    if dst_ip != MONITORED_IP:
        return

    dest_port = None

    if TCP in packet:
        dest_port = packet[TCP].dport

    elif UDP in packet:
        dest_port = packet[UDP].dport

    # Ignore unrelated traffic
    if dest_port not in MONITORED_PORTS:
        return

    # Aggregate by attacker source IP
    flow_key = src_ip

    pkt_len = len(packet)
    now = time.time()

    flow = flow_stats[flow_key]

    if flow["start_time"] is None:
        flow["start_time"] = now

    flow["last_time"] = now
    flow["fwd_packets"] += 1
    flow["fwd_bytes"] += pkt_len
    flow["packet_lengths"].append(pkt_len)
    flow["dest_port"] = dest_port

    # TCP
    if TCP in packet:
        flow["protocol"] = 6
        tcp_flags = packet[TCP].flags

        if tcp_flags & 0x02:
            flow["syn_count"] += 1
        if tcp_flags & 0x10:
            flow["ack_count"] += 1
        if tcp_flags & 0x04:
            flow["rst_count"] += 1
        if tcp_flags & 0x08:
            flow["psh_count"] += 1

    # UDP
    elif UDP in packet:
        flow["protocol"] = 17

    print(f"Captured: {src_ip} -> {dst_ip}:{dest_port}")

# ==========================
# FEATURE EXTRACTION
# ==========================
def extract_features(flow):
    duration = max(flow["last_time"] - flow["start_time"], 0.001)

    total_packets = flow["fwd_packets"] + flow["bwd_packets"]
    total_bytes = flow["fwd_bytes"] + flow["bwd_bytes"]

    flow_packets_per_sec = total_packets / duration
    flow_bytes_per_sec = total_bytes / duration

    packet_mean = np.mean(flow["packet_lengths"]) if flow["packet_lengths"] else 0
    packet_std = np.std(flow["packet_lengths"]) if flow["packet_lengths"] else 0

    avg_packet_size = total_bytes / total_packets if total_packets > 0 else 0

    down_up_ratio = (
        flow["bwd_packets"] / flow["fwd_packets"]
        if flow["fwd_packets"] > 0 else 0
    )

    return [
        duration,
        flow_packets_per_sec,
        flow_bytes_per_sec,
        flow["fwd_packets"],
        flow["bwd_packets"],
        flow["fwd_bytes"],
        flow["bwd_bytes"],
        packet_mean,
        packet_std,
        avg_packet_size,
        flow["syn_count"],
        flow["ack_count"],
        flow["rst_count"],
        flow["psh_count"],
        down_up_ratio,
        flow["dest_port"],
        flow["protocol"]
    ]

# ==========================
# ADAPTIVE RESPONSE
# ==========================
def adaptive_response(src_ip, attack_type, confidence):
    if confidence < 0.60:
        action = "MONITOR"

    elif confidence < 0.85:
        action = "RATE_LIMIT"

    else:
        if attack_type in ["Syn", "UDP", "UDPLag", "Portmap"]:
            action = "BLOCK"

        elif attack_type in [
            "DrDoS_DNS",
            "DrDoS_NTP",
            "DrDoS_SNMP",
            "DrDoS_SSDP"
        ]:
            action = "HONEYPOT"

        else:
            action = "BLOCK"

    log_entry = (
        f"{src_ip} | Attack={attack_type} | "
        f"Action={action} | Confidence={confidence:.2f}"
    )

    logging.info(log_entry)

    print(f"Action for {src_ip}: {action}")

# ==========================
# ANALYSIS ENGINE
# ==========================
def analyze_flows():
    while True:
        time.sleep(WINDOW_SIZE)

        print("\n===== REAL-TIME ANALYSIS =====")

        for flow_key, flow in list(flow_stats.items()):
            src_ip = flow_key

            if flow["start_time"] is None:
                continue

            # Ignore tiny bursts
            if flow["fwd_packets"] < MIN_PACKETS_THRESHOLD:
                del flow_stats[flow_key]
                continue

            features = extract_features(flow)

            feature_df = pd.DataFrame(
                [features],
                columns=FEATURE_NAMES
            )

            scaled_features = scaler.transform(feature_df)

            # Binary detection
            binary_pred = binary_model.predict(scaled_features)[0]

            if hasattr(binary_model, "predict_proba"):
                binary_confidence = binary_model.predict_proba(
                    scaled_features
                )[0][1]
            else:
                binary_confidence = 1.0

            # Confidence filter
            if binary_confidence < BINARY_CONFIDENCE_THRESHOLD:
                print(f"{src_ip} -> NORMAL traffic")
                del flow_stats[flow_key]
                continue

            # Attack path
            if binary_pred == 1:
                attack_pred = multiclass_model.predict(
                    scaled_features
                )[0]

                attack_name = attack_label_map.get(
                    attack_pred,
                    f"Unknown Attack ({attack_pred})"
                )

                print(f"{src_ip} -> ATTACK DETECTED: {attack_name}")
                print(f"Confidence: {binary_confidence:.2f}")

                print(
                    f"Reason: SYN={flow['syn_count']}, "
                    f"ACK={flow['ack_count']}, "
                    f"Packets/sec={features[1]:.2f}"
                )

                adaptive_response(
                    src_ip,
                    attack_name,
                    binary_confidence
                )

            else:
                print(f"{src_ip} -> NORMAL traffic")

            # Reset flow
            del flow_stats[flow_key]

        cpu = psutil.cpu_percent()
        print(f"CPU Usage: {cpu}%")
        print("==============================")

# ==========================
# MAIN
# ==========================
if __name__ == "__main__":
    print("Starting real-time DDoS monitor...")
    print(f"Protecting IP: {MONITORED_IP}")
    print(f"Protected Ports: {MONITORED_PORTS}")

    analysis_thread = threading.Thread(
        target=analyze_flows,
        daemon=True
    )

    analysis_thread.start()

    sniff(
        prn=process_packet,
        store=False,
        iface=INTERFACE
    )