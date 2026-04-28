import json
import time
import joblib
import psutil
import numpy as np
import pandas as pd
import threading
from pathlib import Path
from collections import defaultdict, deque
from scapy.all import sniff, IP, TCP, UDP, get_if_list

# Local helpers and config
from detect_interface import get_working_interface
from logger_setup import setup_logging
import config

# ==========================
# CONFIG (from config.py)
# ==========================
WINDOW_SIZE = config.WINDOW_SIZE
INTERFACE = get_working_interface() or config.DEFAULT_INTERFACE

BINARY_MODEL_PATH = config.BINARY_MODEL_PATH
MULTICLASS_MODEL_PATH = config.MULTICLASS_MODEL_PATH
SCALER_PATH = config.SCALER_PATH

MONITORED_IP = config.MONITORED_IP
MONITORED_PORTS = config.MONITORED_PORTS
MIN_PACKETS_THRESHOLD = config.MIN_PACKETS_THRESHOLD
BINARY_CONFIDENCE_THRESHOLD = config.BINARY_CONFIDENCE_THRESHOLD
SAFE_IPS = config.SAFE_IPS
LOG_FILE = config.LOG_FILE
METRICS_FILE = Path(LOG_FILE).with_name("runtime_metrics.json")

# Setup structured logger
logger = setup_logging(__name__, log_file=LOG_FILE)

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

# Models will be loaded at runtime to avoid heavy top-level import work
binary_model = None
multiclass_model = None
scaler = None
models_ready = False

def load_models():
    global binary_model, multiclass_model, scaler, models_ready
    logger.info("Loading models...")
    try:
        binary_path = Path(BINARY_MODEL_PATH)
        scaler_path = Path(SCALER_PATH)

        if not binary_path.exists():
            raise FileNotFoundError(f"Binary model not found: {binary_path}")
        if not scaler_path.exists():
            raise FileNotFoundError(f"Scaler not found: {scaler_path}")

        binary_model = joblib.load(binary_path)
        scaler = joblib.load(scaler_path)
        multiclass_path = Path(MULTICLASS_MODEL_PATH)
        if multiclass_path.exists():
            multiclass_model = joblib.load(multiclass_path)
        else:
            multiclass_model = None
            logger.warning(
                "Multiclass model not found at %s; attack typing will be degraded.",
                multiclass_path
            )
        models_ready = True
        logger.info("Models loaded successfully!")
        return True
    except Exception as e:
        models_ready = False
        logger.error(f"Error loading models: {e}")
        return False

# ==========================
# LOGGING SETUP
# ==========================
# Note: structured logging via logger

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
    # Limited-length buffer to avoid unbounded memory growth
    "packet_lengths": deque(maxlen=1000),
    "syn_count": 0,
    "ack_count": 0,
    "rst_count": 0,
    "psh_count": 0,
    "dest_port": 0,
    "protocol": 0
})

captured_packets_total = 0
no_flow_windows = 0
last_detection_epoch = 0

# ==========================
# PACKET CAPTURE
# ==========================
def process_packet(packet):
    global captured_packets_total

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

    # Aggregate by attacker source IP and destination port so flows
    # to different victim services are classified separately.
    flow_key = f"{src_ip}:{dest_port}"

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

    captured_packets_total += 1
    if captured_packets_total % 500 == 0:
        print(f"Captured packets total: {captured_packets_total}")

# ==========================
# FEATURE EXTRACTION
# ==========================
def extract_features(flow):
    duration = max(flow["last_time"] - flow["start_time"], 0.001)

    total_packets = flow["fwd_packets"] + flow["bwd_packets"]
    total_bytes = flow["fwd_bytes"] + flow["bwd_bytes"]

    flow_packets_per_sec = total_packets / duration
    flow_bytes_per_sec = total_bytes / duration

    packet_lengths = list(flow["packet_lengths"]) if flow["packet_lengths"] else []
    packet_mean = float(np.mean(packet_lengths)) if packet_lengths else 0.0
    packet_std = float(np.std(packet_lengths)) if packet_lengths else 0.0

    avg_packet_size = total_bytes / total_packets if total_packets > 0 else 0.0

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
        action = "RATE_LIMIT" if attack_type in ["Syn", "UDP", "UDPLag", "Portmap", "HTTP_Flood"] else "MONITOR"

    elif confidence < 0.85:
        action = "RATE_LIMIT"

    else:
        if attack_type in ["Syn", "UDP", "UDPLag", "Portmap", "HTTP_Flood"]:
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

    logger.info(log_entry)

    print(f"Action for {src_ip}: {action}")
    return action


def classify_demo_attack(flow, predicted_label):
    """Use protocol/port heuristics to keep the demo labels stable."""
    protocol = flow.get("protocol", 0)
    dest_port = flow.get("dest_port", 0)
    syn = flow.get("syn_count", 0)
    ack = flow.get("ack_count", 0)
    packets = flow.get("fwd_packets", 0)

    # Strongly TCP/HTTP-like flows on the victim HTTP port.
    if protocol == 6 and dest_port in {80, 5000} and ack >= syn:
        return "HTTP_Flood"

    # TCP SYN-heavy flows on the TCP service.
    if protocol == 6 and dest_port == 8081 and syn > max(ack, 0) and packets >= MIN_PACKETS_THRESHOLD:
        return "Syn"

    # UDP service traffic.
    if protocol == 17 and dest_port == 5001 and packets >= MIN_PACKETS_THRESHOLD:
        return "UDP"

    # Fall back to the ML label if no rule matches.
    return predicted_label

# ==========================
# ANALYSIS ENGINE
# ==========================
def analyze_flows():
    global no_flow_windows, last_detection_epoch

    while True:
        time.sleep(WINDOW_SIZE)

        if not models_ready:
            if flow_stats:
                flow_stats.clear()
            logger.warning(
                "Inference is disabled until binary and scaler artifacts are available."
            )
            continue

        print("\n===== REAL-TIME ANALYSIS =====")
        print(f"Total flows in buffer: {len(flow_stats)}")

        window_packets = 0
        window_flow_count = len(flow_stats)
        detections_in_window = 0
        last_attack_name = "None"
        last_action = "MONITOR"
        last_confidence = 0.0
        recent_flows = []

        if len(flow_stats) == 0:
            no_flow_windows += 1
            if no_flow_windows >= 3:
                print(
                    "No matched traffic yet. "
                    f"Filter is dst_ip={MONITORED_IP}, ports={sorted(MONITORED_PORTS)}"
                )
        else:
            no_flow_windows = 0

        for flow_key, flow in list(flow_stats.items()):
            # flow_key is 'attacker_ip:dest_port'
            src_ip = flow_key.split(":")[0]

            if flow["start_time"] is None:
                continue

            # Ignore tiny bursts
            window_packets += flow["fwd_packets"]

            if flow["fwd_packets"] < MIN_PACKETS_THRESHOLD:
                print(f"  {src_ip}: FILTERED (only {flow['fwd_packets']} packets, threshold={MIN_PACKETS_THRESHOLD})")
                del flow_stats[flow_key]
                continue

            features = extract_features(flow)

            # Keep feature names aligned with training to avoid scaler warnings
            feature_frame = pd.DataFrame([features], columns=FEATURE_NAMES)
            scaled_features = scaler.transform(feature_frame)

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
                # Allow strong protocol/port heuristics to override low ML confidence
                is_syn_heavy = (
                    flow.get("protocol") == 6
                    and flow.get("dest_port") == 8081
                    and flow.get("syn_count", 0) > flow.get("ack_count", 0)
                    and flow.get("fwd_packets", 0) >= MIN_PACKETS_THRESHOLD
                )
                is_udp_heavy = (
                    flow.get("protocol") == 17
                    and flow.get("dest_port") == 5001
                    and flow.get("fwd_packets", 0) >= MIN_PACKETS_THRESHOLD
                )
                is_http_like = (
                    flow.get("protocol") == 6
                    and flow.get("dest_port") in {80, 5000}
                    and flow.get("ack_count", 0) >= flow.get("syn_count", 0)
                    and flow.get("fwd_packets", 0) >= MIN_PACKETS_THRESHOLD
                )

                if not (is_syn_heavy or is_udp_heavy or is_http_like):
                    print(f"  {src_ip}: LOW CONFIDENCE ({binary_confidence:.2f} < {BINARY_CONFIDENCE_THRESHOLD})")
                    del flow_stats[flow_key]
                    continue
                else:
                    print(f"  {src_ip}: LOW CONFIDENCE but heuristic override ({binary_confidence:.2f} < {BINARY_CONFIDENCE_THRESHOLD})")

            # Attack path
            attack_name = "Normal"
            if binary_pred == 1:
                if multiclass_model is not None:
                    attack_pred = multiclass_model.predict(
                        scaled_features
                    )[0]

                    attack_name = attack_label_map.get(
                        attack_pred,
                        f"Unknown Attack ({attack_pred})"
                    )
                else:
                    attack_name = "Attack"

                attack_name = classify_demo_attack(flow, attack_name)

                print(f"  {src_ip}: *** ATTACK DETECTED: {attack_name} ***")
                print(f"     Confidence: {binary_confidence:.2f}")
                print(
                    f"     Reason: SYN={flow['syn_count']}, "
                    f"ACK={flow['ack_count']}, "
                    f"Packets/sec={features[1]:.2f}"
                )

                last_action = adaptive_response(
                    src_ip,
                    attack_name,
                    binary_confidence
                )

                detections_in_window += 1
                last_attack_name = attack_name
                last_confidence = float(binary_confidence)
                last_detection_epoch = time.time()

            else:
                print(f"  {src_ip}: Normal (confidence={binary_confidence:.2f})")
                last_confidence = float(binary_confidence)

            recent_flows.append({
                "ip": src_ip,
                "attack": attack_name,
                "confidence": round(float(binary_confidence), 2),
                "packets": int(flow["fwd_packets"]),
                "dest_port": int(flow.get("dest_port", 0)),
            })

            # Reset flow
            del flow_stats[flow_key]

        cpu = psutil.cpu_percent()
        snapshot = {
            "timestamp": time.time(),
            "captured_packets_total": captured_packets_total,
            "window_packets": window_packets,
            "window_packet_rate": round(window_packets / max(WINDOW_SIZE, 1), 2),
            "active_flows": len(flow_stats),
            "window_flow_count": window_flow_count,
            "detections_in_window": detections_in_window,
            "last_attack": last_attack_name,
            "last_action": last_action,
            "last_confidence": round(last_confidence, 2),
            "last_detection_epoch": last_detection_epoch,
            "cpu_usage": cpu,
            "recent_flows": recent_flows[-10:],
        }

        try:
            METRICS_FILE.write_text(json.dumps(snapshot), encoding="utf-8")
        except Exception:
            pass

        print(f"CPU Usage: {cpu}%")
        print("==============================")

# ==========================
# MAIN
# ==========================
if __name__ == "__main__":
    print("Starting real-time DDoS monitor...")
    print(f"Protecting IP: {MONITORED_IP}")
    print(f"Protected Ports: {MONITORED_PORTS}")
    print(f"Sniff interface: {INTERFACE}")

    analysis_thread = threading.Thread(
        target=analyze_flows,
        daemon=True
    )

    # Load models before starting analysis
    load_models()
    analysis_thread.start()

    sniff_targets = []
    if INTERFACE:
        sniff_targets.append(INTERFACE)

    for iface in get_if_list():
        if "loopback" in iface.lower() and iface not in sniff_targets:
            sniff_targets.append(iface)

    print(f"Sniff targets: {sniff_targets}")

    def run_sniffer(iface_name):
        sniff(
            prn=process_packet,
            store=False,
            iface=iface_name
        )

    for iface_name in sniff_targets:
        threading.Thread(
            target=run_sniffer,
            args=(iface_name,),
            daemon=True
        ).start()

    while True:
        time.sleep(1)