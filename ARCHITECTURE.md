# 🏗️ ARCHITECTURE.md: Technical Deep-Dive

**Detailed Technical Documentation for DDoS Detection & Mitigation System**

---

## 📐 System Architecture Overview

### High-Level Component Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          PROTECTED NETWORK                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐                                                     │
│  │   Victim    │◄────────────────────────────────────────┐           │
│  │   Server    │  Services (HTTP, UDP, TCP)             │           │
│  │  (port      │                                        │           │
│  │  5000/5001) │                                    ┌───────────────┐│
│  └─────────────┘                                    │               ││
│         ▲                                          │ INCOMING      ││
│         │                                          │ TRAFFIC       ││
│         │                                          │               ││
│         │     ┌────────────────────────────────┐   └───────────────┘│
│         │     │   Real-Time Monitor            │        │            │
│         │     │  (realtime_monitor.py)         │        │            │
│         │     │                                │        │            │
│         │     │ 1. Scapy Packet Capture        │◄──────┘            │
│         │     │ 2. Flow Aggregation (3s)       │                    │
│         │     │ 3. Feature Extraction (17)     │                    │
│         │     │ 4. Binary ML Detection         │                    │
│         │     │ 5. Multiclass Prediction       │                    │
│         │     │ 6. Confidence Scoring          │                    │
│         │     │ 7. Logging (structured JSON)   │                    │
│         │     └──────────────┬────────────────┘                    │
│         │                    │                                     │
│         │                    │ Detection Event                     │
│         │                    ▼                                     │
│         │     ┌────────────────────────────────┐                    │
│         │     │ Adaptive Response Engine       │                    │
│         │     │ (adaptive_response.py)         │                    │
│         │     │                                │                    │
│         │     │ Confidence Threshold Logic:    │                    │
│         │     │ <0.60  → MONITOR               │                    │
│         │     │ 0.60-0.85 → RATE_LIMIT         │                    │
│         │     │ >0.85  → BLOCK/HONEYPOT        │                    │
│         │     └──────────────┬────────────────┘                    │
│         │                    │                                     │
│    ┌────┴─────────────┬──────┴──────┬────────────┐                 │
│    │                  │             │            │                 │
│    ▼                  ▼             ▼            ▼                 │
│ MONITOR          RATE_LIMIT       BLOCK      HONEYPOT             │
│  (Log)          (Throttle)   (Firewall)    (Redirect)             │
│                                       │            │               │
│                            Windows netsh│        ┌──┴────────────┐  │
│                            command │    └────────►│ Honeypot     │  │
│                                    │            │ Service      │  │
│                                    ▼            │ (port 8080)  │  │
│                            ┌──────────────┐     │              │  │
│                            │ Firewall     │     │ Fake:        │  │
│                            │ Rule Added   │     │ - HTTP       │  │
│                            │ (IP Blocked) │     │ - SSH        │  │
│                            └──────────────┘     │ - MySQL      │  │
│                                                 └──────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
         ▲
         │
         │ Attack Packets
         │
┌────────┴────────────────────────────────────────────────────────────┐
│               ATTACKER (External Network)                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐               │
│  │ HTTP Flood   │  │ UDP Flood   │  │  SYN Flood   │               │
│  │ (High Rate)  │  │ (Amplified) │  │ (Connection) │               │
│  └──────────────┘  └─────────────┘  └──────────────┘               │
│         │                │                  │                       │
│         └────────────────┼──────────────────┘                       │
│                          │                                           │
│                    Botnets (Simulated)                              │
│                    attack_simulator.py                              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│                    VISUALIZATION & MONITORING                      │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────┐       ┌──────────────────┐                  │
│  │  Dashboard      │       │  Structured Logs │                  │
│  │  (Flask)        │       │  JSON/CSV        │                  │
│  │  http://localhost:5000 │                  │                  │
│  │                 │       │ logs/            │                  │
│  │  Real-time      │       │ security_actions │                  │
│  │  Event Log      │       │ honeypot.log     │                  │
│  │  Attack Heatmap │       │ metrics.json     │                  │
│  │  IP Tracker     │       │                  │                  │
│  └─────────────────┘       └──────────────────┘                  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow & Processing Pipeline

### Detection Pipeline (Per Flow)

```
PACKET CAPTURE (Continuous)
    ↓
    ├─ Scapy sniff() on Ethernet interface
    ├─ Filter: MONITORED_IP as destination
    ├─ Filter: MONITORED_PORTS only
    ├─ Filter: Exclude SAFE_IPS
    ├─ Aggregate by source IP (flow_key)
    └─ Store in flow_stats dictionary
    
FEATURE EXTRACTION (Every 3 seconds)
    ↓
    ├─ Duration = flow['last_time'] - flow['start_time']
    ├─ Total packets = fwd + bwd
    ├─ Packets/sec = total_packets / duration
    ├─ Bytes/sec = total_bytes / duration
    ├─ Packet_mean = np.mean(packet_lengths)
    ├─ Packet_std = np.std(packet_lengths)
    ├─ TCP flags: SYN, ACK, RST, PSH counts
    ├─ Down/Up ratio = bwd_packets / fwd_packets
    ├─ Destination port
    └─ Protocol (TCP=6, UDP=17)
    
FEATURE VALIDATION
    ↓
    ├─ Check minimum threshold (10 packets)
    ├─ Replace inf/-inf with 0
    ├─ Fill NaN with 0
    └─ Normalize with StandardScaler
    
BINARY CLASSIFICATION (Stage 1)
    ↓
    ├─ Input: 17 features (scaled)
    ├─ Model: Random Forest
    ├─ Output: Prediction (0=Normal, 1=Attack)
    ├─ Output: Probability [0-1]
    └─ Decision: If prob < threshold → NORMAL (exit)
    
MULTICLASS CLASSIFICATION (Stage 2)
    ↓
    ├─ Input: Same 17 features
    ├─ Model: Random Forest multiclass
    ├─ Output: Attack type [1-12]
    ├─ Map: Label → Attack name
    └─ Example: 9 → "Syn"
    
CONFIDENCE-BASED RESPONSE
    ↓
    ├─ If confidence < 0.60 → MONITOR (log only)
    ├─ If 0.60 ≤ confidence < 0.85 → RATE_LIMIT
    └─ If confidence ≥ 0.85 → BLOCK/HONEYPOT
    
ADAPTIVE ACTION EXECUTION
    ↓
    ├─ MONITOR: Write to security_actions.log
    ├─ RATE_LIMIT: Simulate throttling
    ├─ BLOCK: Execute netsh firewall command
    └─ HONEYPOT: Redirect to port 8080
    
EVENT LOGGING
    ↓
    ├─ Structured JSON format
    ├─ Timestamp, IP, Attack, Action, Confidence
    └─ Written to: logs/security_actions.log
    
DASHBOARD UPDATE
    ↓
    └─ Flask app reads log file
        └─ Renders HTML table
            └─ Refreshes every 2 seconds
```

---

## 🧠 Machine Learning Pipeline

### Two-Stage Classification System

```
┌────────────────────────────────────────────────────────────────┐
│                  TRAINING PHASE (train5.py)                   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Dataset: CICIDS2017 / CICDDoS2019                           │
│    ↓                                                           │
│  Data Preprocessing (combine.py)                             │
│  - Load CSV chunks                                            │
│  - Extract 17 lightweight features                            │
│  - Handle missing values (fillna, inf→0)                     │
│  - Balance classes                                            │
│  - Shuffle and split                                          │
│    ↓                                                           │
│  Feature Scaling                                              │
│  - StandardScaler (normalize to mean=0, std=1)               │
│  - Save scaler for runtime use                               │
│    ↓                                                           │
│  Model Training                                               │
│  ┌─────────────────────┬─────────────────────┐               │
│  │   BINARY MODEL      │  MULTICLASS MODEL   │               │
│  ├─────────────────────┼─────────────────────┤               │
│  │ Task: Detect attack │ Task: Classify type │               │
│  │ Output: 0/1         │ Output: 1-12        │               │
│  │ Algorithms:         │ Algorithms:         │               │
│  │ - Random Forest     │ - Random Forest     │               │
│  │ - Decision Tree     │ - XGBoost           │               │
│  │ - XGBoost           │                     │               │
│  │                     │                     │               │
│  │ Best: Random Forest │ Best: Random Forest │               │
│  │ Accuracy: 98-99%    │ Accuracy: 95-97%    │               │
│  │ Speed: ~2ms/pred    │ Speed: ~3ms/pred    │               │
│  └─────────────────────┴─────────────────────┘               │
│    ↓                                                           │
│  Model Serialization                                          │
│  - Save: binary_ddos_model.pkl                               │
│  - Save: best_ddos_model.pkl                                 │
│  - Save: binary_feature_scaler.pkl                           │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                  INFERENCE PHASE (realtime_monitor.py)        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Load Models (at startup)                                     │
│  - binary_model = joblib.load(...)                            │
│  - multiclass_model = joblib.load(...)                        │
│  - scaler = joblib.load(...)                                  │
│    ↓                                                           │
│  For each flow (every 3 seconds):                             │
│                                                                │
│  1. Extract 17 features from packet data                      │
│  2. Create DataFrame with proper column names                 │
│  3. Scale features: X_scaled = scaler.transform(X)            │
│                                                                │
│  4. STAGE 1: Binary Detection                                 │
│     binary_pred = binary_model.predict(X_scaled)              │
│     binary_prob = binary_model.predict_proba(X_scaled)        │
│                                                                │
│     If binary_pred == 0 (Normal):                             │
│       → Mark as normal, skip stage 2                          │
│       → Log if probability < threshold                        │
│                                                                │
│  5. STAGE 2: Attack Classification (if attack detected)       │
│     attack_pred = multiclass_model.predict(X_scaled)          │
│     attack_name = attack_label_map[attack_pred]               │
│                                                                │
│  6. Extract explanation features:                             │
│     - High SYN count? → Suspicious for SYN flood              │
│     - High packets/sec? → Rate-based attack                   │
│     - Down/up ratio anomalous? → Reflective attack            │
│                                                                │
│  7. Pass to response engine                                   │
│     adaptive_response(ip, attack_type, confidence)            │
│                                                                │
└────────────────────────────────────────────────────────────────┘

Feature Importance (from trained models):
┌─────────────────────────────────────────┐
│ Top 5 Features for Detection:            │
├─────────────────────────────────────────┤
│ 1. Flow Packets/s (highest variance)     │
│ 2. Total Fwd Packets (volume)            │
│ 3. SYN Flag Count (attack signature)     │
│ 4. Flow Bytes/s (intensity)              │
│ 5. Packet Length Std (pattern)           │
└─────────────────────────────────────────┘
```

---

## 🔌 Feature Engineering Details

### Feature Extraction Algorithm

```python
def extract_features(flow):
    """
    Transform raw packet data into 17 ML features
    
    Input: flow_stats[source_ip] dictionary containing:
    - Timestamps, packet counts, byte counts
    - Flag counts, packet lengths
    
    Output: [17 numerical features]
    """
    
    # TEMPORAL FEATURES
    duration = flow['last_time'] - flow['start_time']  # seconds
    
    # RATE FEATURES
    total_packets = flow['fwd_packets'] + flow['bwd_packets']
    total_bytes = flow['fwd_bytes'] + flow['bwd_bytes']
    flow_packets_per_sec = total_packets / max(duration, 0.001)
    flow_bytes_per_sec = total_bytes / max(duration, 0.001)
    
    # VOLUME FEATURES
    total_fwd_packets = flow['fwd_packets']
    total_bwd_packets = flow['bwd_packets']
    total_fwd_bytes = flow['fwd_bytes']
    total_bwd_bytes = flow['bwd_bytes']
    
    # STATISTICAL FEATURES
    packet_lengths = flow['packet_lengths']
    packet_mean = np.mean(packet_lengths) if packet_lengths else 0
    packet_std = np.std(packet_lengths) if packet_lengths else 0
    avg_packet_size = total_bytes / max(total_packets, 1)
    
    # FLAG FEATURES (TCP)
    syn_count = flow['syn_count']
    ack_count = flow['ack_count']
    rst_count = flow['rst_count']
    psh_count = flow['psh_count']
    
    # RATIO FEATURES
    down_up_ratio = total_bwd_packets / max(total_fwd_packets, 1)
    
    # NETWORK FEATURES
    dest_port = flow['dest_port']
    protocol = flow['protocol']  # 6=TCP, 17=UDP
    
    return [
        duration,
        flow_packets_per_sec,
        flow_bytes_per_sec,
        total_fwd_packets,
        total_bwd_packets,
        total_fwd_bytes,
        total_bwd_bytes,
        packet_mean,
        packet_std,
        avg_packet_size,
        syn_count,
        ack_count,
        rst_count,
        psh_count,
        down_up_ratio,
        dest_port,
        protocol
    ]
```

### Why These 17 Features?

| Feature Category | Why These Features? | DDoS Relevance |
|---|---|---|
| **Temporal** | Duration captures attack window | Attacks sustained over time |
| **Rate** | Packets/sec & Bytes/sec show intensity | DDoS = high volume |
| **Volume** | Total counts distinguish attacks | Floods have high counts |
| **Statistical** | Packet length stats show patterns | Attack traffic is uniform |
| **Flags** | SYN counts directly detect SYN floods | TCP flags are attack signatures |
| **Ratios** | Down/up ratio shows asymmetry | Reflections are asymmetric |
| **Network** | Port & protocol identify service targets | Attacks target specific ports |

---

## 🛡️ Adaptive Response Engine Logic

### Confidence-Based Decision Tree

```
Confidence Score (probability from binary model)
    │
    ├─ [0.00 - 0.60]  → LOW THREAT
    │   ├─ Action: MONITOR (log only)
    │   ├─ Reasoning: Below threshold, likely false positive
    │   └─ Side effects: None
    │
    ├─ [0.60 - 0.85]  → MEDIUM THREAT
    │   ├─ Action: RATE_LIMIT
    │   ├─ Reasoning: Suspicious but uncertain
    │   ├─ Implementation: Socket-level throttling
    │   └─ Recovery: Automatic after 5 minutes
    │
    └─ [0.85 - 1.00]  → HIGH THREAT
        ├─ Fetch attack_type from multiclass model
        │
        ├─ IF attack_type IN [Syn, UDP, UDPLag, Portmap]:
        │   ├─ Action: BLOCK
        │   ├─ Implementation: Windows Firewall rule
        │   │   netsh advfirewall firewall add rule \
        │   │   name="DDoS_Block_{ip}" \
        │   │   dir=in action=block remoteip={ip}
        │   └─ Duration: Permanent (manual cleanup)
        │
        └─ ELIF attack_type IN [DrDoS_DNS, DrDoS_NTP, DrDoS_SNMP, DrDoS_SSDP]:
            ├─ Action: HONEYPOT
            ├─ Implementation: Redirect to fake service (port 8080)
            ├─ Deception: Emulate vulnerable service
            ├─ Collection: Log attacker attempt
            └─ Goal: Waste attacker's time, learn patterns
```

### Firewall Integration

```python
# Windows Firewall Rule Creation (adaptive_response.py)

def block_ip(ip):
    """Create permanent firewall rule to block IP"""
    cmd = f'netsh advfirewall firewall add rule ' \
          f'name="DDoS_Block_{ip}" ' \
          f'dir=in action=block remoteip={ip}'
    
    os.system(cmd)
    logging.info(f"Firewall rule created for {ip}")

# Requires Admin Privileges!
# Rule persists across reboots
# Manual removal: netsh advfirewall firewall delete rule name="DDoS_Block_{ip}"
```

---

## 🍯 Honeypot Service Architecture

### Multi-Service Honeypot (honeypot.py)

```python
class Honeypot:
    """
    Emulates multiple vulnerable services to deceive attackers
    and collect attack intelligence
    """
    
    SERVICES = {
        'http': {
            'port': 8080,
            'banner': b'HTTP/1.1 200 OK\r\nServer: Apache/2.2.1\r\n\r\n',
            'vulnerability': 'Generic HTTP service'
        },
        'ssh': {
            'port': 2222,
            'banner': b'SSH-2.0-OpenSSH_5.1\r\n',
            'vulnerability': 'OpenSSH v5.1 (vulnerable)'
        },
        'mysql': {
            'port': 3306,
            'banner': b'\x00\x00\x00\x0a5.1.45-log\x00...',
            'vulnerability': 'MySQL 5.1 (auth bypass)'
        },
        'ftp': {
            'port': 21,
            'banner': b'220 ProFTPD 1.2.0 Server\r\n',
            'vulnerability': 'ProFTPD (RCE)'
        }
    }
    
    def handle_connection(self, client_socket, source_ip, service):
        """
        Handle attacker connection:
        1. Send fake service banner
        2. Log attacker attempt
        3. Close connection
        """
        logging.info(f"Honeypot triggered: {source_ip} → {service}")
        
        try:
            client_socket.send(self.SERVICES[service]['banner'])
            # Attacker may continue sending exploit code
            # We log and close
        except:
            pass
        finally:
            client_socket.close()
```

### Honeypot Intelligence Collection

```
Attack Event
    ↓
Honeypot Connection
    ├─ Source IP logged
    ├─ Service targeted noted
    ├─ Timestamp recorded
    └─ Payload (if sent) captured
    
Analysis
    ├─ Which services are most targeted?
    ├─ Which IPs are most aggressive?
    ├─ What payloads are being sent?
    └─ Geographic origin tracking
    
Integration
    └─ Feedback to ML model:
       - Confirm attack classification
       - Enhance attack profiles
       - Reduce false positives
```

---

## 📊 Data Flow: Packet to Action

```
EXAMPLE: SYN Flood Attack Scenario
═════════════════════════════════════════════════════════════════

TIME: 14:32:15
Source IP: 192.168.1.100
Target: 192.168.1.4:5000 (victim HTTP server)

STEP 1: PACKET CAPTURE (Continuous)
─────────────────────────────────────
Scapy captures 5,000 TCP packets in 3 seconds:
- All have SYN flag set (TCP flags = 0x02)
- Varying source ports
- High rate: 1,667 pps
- Small payloads: 60 bytes each
- Total: 300 KB in 3 seconds

STEP 2: FLOW AGGREGATION
─────────────────────────
Aggregated by source IP (192.168.1.100):
- Duration: 3.0 seconds
- Fwd Packets: 5,000
- Bwd Packets: 0
- Fwd Bytes: 300,000
- Bwd Bytes: 0
- SYN Count: 5,000
- ACK Count: 0
- Packet Lengths: [60, 60, 60, ...]

STEP 3: FEATURE EXTRACTION
───────────────────────────
Extracted 17 features:
1. Flow Duration = 3.0 s
2. Flow Packets/s = 1,667 pps
3. Flow Bytes/s = 100,000 bytes/s
4. Total Fwd Packets = 5,000
5. Total Bwd Packets = 0
6. Total Fwd Bytes = 300,000
7. Total Bwd Bytes = 0
8. Packet Length Mean = 60
9. Packet Length Std = 0
10. Average Packet Size = 60
11. SYN Flag Count = 5,000  ← SUSPICIOUS!
12. ACK Flag Count = 0
13. RST Flag Count = 0
14. PSH Flag Count = 0
15. Down/Up Ratio = 0
16. Destination Port = 5000
17. Protocol = 6 (TCP)

STEP 4: FEATURE SCALING
────────────────────────
StandardScaler normalization:
- Z-score: (value - mean) / std
- Example: Packets/s = (1667 - 500) / 300 = 3.89 (very high!)

STEP 5: BINARY CLASSIFICATION
──────────────────────────────
Model: Random Forest Binary Classifier
Input: 17 scaled features
Decision Tree in Forest:
  IF flow_packets_per_sec > 1500 THEN Attack (SYN flood)
  ELSE check other features

Result:
  Prediction: 1 (ATTACK)
  Probability: 0.98 ← Very confident!

STEP 6: MULTICLASS CLASSIFICATION
──────────────────────────────────
Model: Random Forest Multiclass
Input: Same 17 features
Decision Tree:
  IF syn_count > 1000 THEN Syn flood
  ELSE check other attack types

Result:
  Attack Type: 9 (Syn)
  Probability: 0.95

STEP 7: CONFIDENCE SCORING & THRESHOLD
───────────────────────────────────────
Confidence = 0.98 (binary model confidence)
Threshold Check:
  0.98 > 0.85 → HIGH THREAT ✓

STEP 8: RESPONSE ENGINE DECISION
─────────────────────────────────
Attack Type: Syn
Confidence: 0.98
Is Syn in [Syn, UDP, UDPLag, Portmap]? YES
→ Action: BLOCK

STEP 9: ACTION EXECUTION
────────────────────────
Execute Windows Firewall command:
  netsh advfirewall firewall add rule \
    name="DDoS_Block_192.168.1.100" \
    dir=in action=block remoteip=192.168.1.100

Result: Firewall blocks all traffic from 192.168.1.100

STEP 10: LOGGING
────────────────
Log Entry:
  Timestamp: 2025-01-15 14:32:15
  IP: 192.168.1.100
  Attack: Syn
  Action: BLOCK
  Confidence: 0.98

STEP 11: DASHBOARD UPDATE
─────────────────────────
Dashboard refresh (every 2 seconds):
  Displays new event in real-time table
  Shows: IP, Attack Type, Action, Confidence

RESULT:
────────────────────────────────────────
Total process time: ~50-100 milliseconds
Attacker packets blocked: Subsequent traffic rejected by firewall
System status: Protected ✓
```

---

## 🔍 Flow Tracking & State Management

### Flow Dictionary Structure

```python
flow_stats = {
    "192.168.1.100": {
        "start_time": 1642281135.123,
        "last_time": 1642281138.456,
        "fwd_packets": 5000,
        "bwd_packets": 0,
        "fwd_bytes": 300000,
        "bwd_bytes": 0,
        "packet_lengths": [60, 60, 62, 60, ...],
        "syn_count": 5000,
        "ack_count": 0,
        "rst_count": 0,
        "psh_count": 0,
        "dest_port": 5000,
        "protocol": 6  # TCP
    },
    "192.168.1.101": {
        # Another flow...
    }
}
```

### Flow Lifecycle

```
PHASE 1: INITIALIZATION
─────────────────────
First packet from source IP arrives
→ Create entry in flow_stats
→ Set start_time = packet_arrival_time
→ Initialize counters to 0

PHASE 2: AGGREGATION (3 seconds)
────────────────────────────────
Packets arrive continuously
→ Update counters (fwd_packets, bytes, etc.)
→ Append packet_length to list
→ Increment flag counts
→ Update last_time

PHASE 3: ANALYSIS
─────────────────
Every 3 seconds:
→ Extract features
→ Run ML models
→ Determine action

PHASE 4: CLEANUP
────────────────
After action decision:
→ Delete entry from flow_stats
→ Reset counters
→ Ready for next 3-second window
```

### Memory Implications

```
Memory per flow: ~2 KB
- 100 flows: ~200 KB
- 1000 flows: ~2 MB
- 10000 flows: ~20 MB

With 3-second windows and cleanup:
Maximum simultaneous flows ≈ unique source IPs in 3 seconds
Typical network: 50-500 flows
Memory usage: 100 KB - 1 MB (negligible)
```

---

## ⚙️ Configuration Parameters

### Critical Parameters (realtime_monitor.py)

```python
# NETWORK CONFIGURATION
MONITORED_IP = "192.168.1.4"          # Defender's IP (TO ADJUST)
MONITORED_PORTS = {5000, 8080, 80}    # Ports to protect
INTERFACE = "Ethernet"                 # Network interface (TO ADJUST)

# DETECTION PARAMETERS
WINDOW_SIZE = 3                        # Analysis window (seconds)
MIN_PACKETS_THRESHOLD = 10             # Minimum packets to classify
BINARY_CONFIDENCE_THRESHOLD = 0.75     # Confidence threshold

# SAFE INFRASTRUCTURE (Whitelist)
SAFE_IPS = {
    "127.0.0.1",
    "0.0.0.0",
    "255.255.255.255",
    "192.168.1.1"  # Router
}
```

### Response Parameters (adaptive_response.py)

```python
# CONFIDENCE THRESHOLDS
LOW_THRESHOLD = 0.60                   # Low threat
HIGH_THRESHOLD = 0.85                  # High threat

# RESPONSE ACTIONS
RESPONSE_MAPPING = {
    'low': 'MONITOR',
    'medium': 'RATE_LIMIT',
    'high': 'BLOCK'  or  'HONEYPOT'
}

# FIREWALL CONFIGURATION
WINDOWS_BLOCK_CMD = 'netsh advfirewall firewall add rule ...'
HONEYPOT_PORT = 8080
```

---

## 🧪 Testing & Validation

### Unit Testing Strategy

```
Test: Feature Extraction
├─ Input: Known packet flow
├─ Expected: 17 features with expected values
└─ Validate: No NaN, inf, or type errors

Test: Model Inference
├─ Input: Test dataset (holdout set)
├─ Expected: Predictions match ground truth
└─ Validate: Accuracy > 95%, F1 > 0.9

Test: Response Engine
├─ Input: High-confidence attack event
├─ Expected: Correct action (BLOCK/HONEYPOT)
└─ Validate: Firewall rule created (if BLOCK)

Test: Dashboard
├─ Input: Log file with events
├─ Expected: Events rendered in table
└─ Validate: All fields displayed correctly

Test: End-to-End
├─ Input: Attack simulator + victim server
├─ Expected: Attack detected → Action taken
└─ Validate: Flow from attack to mitigation
```

---

## 📈 Performance Characteristics

### Latency Breakdown

```
Step                              Time (ms)
────────────────────────────────────────
Packet Capture (Scapy)           Continuous (buffered)
Flow Aggregation                 ~1 ms per packet
Feature Extraction               ~5 ms per flow
StandardScaler Transform         ~2 ms per flow
Binary Model Prediction          ~2 ms
Multiclass Model (if attack)     ~3 ms
Response Decision Logic          ~1 ms
Action Execution:
  - MONITOR (log)                ~1 ms
  - BLOCK (netsh cmd)            50-100 ms (OS dependent)
  - HONEYPOT (redirect)          ~1 ms

Total Detection Latency:          ~15-20 ms
Total Action Latency:            50-120 ms
End-to-End (detection→block):    65-140 ms
```

### Throughput Capacity

```
Scapy Capture Rate (Windows):    ~50,000 pps (100 Mbps)
Feature Extraction:              ~100,000 flows/sec per core
ML Inference:                    ~500 predictions/sec (RF)
Bottleneck:                      Scapy capture on Windows

Realistic Deployment:
- Small network (100 Mbps):      OK
- Medium network (1 Gbps):       May exceed capacity
- Large network (10 Gbps):       Not recommended (needs optimization)
```

### Memory Profile

```
Baseline (Python + libraries):   ~100 MB
Loaded Models:                   ~50 MB (RF trees in memory)
Active Flows (1000 flows):       ~2 MB
Buffers & Queues:               ~5 MB
Logs (memory mapped):           ~1 MB

Total at Rest:                  ~160 MB
Peak Memory (during training):  ~2 GB (with datasets)
```

---

## 🔐 Security Considerations

### Potential Vulnerabilities

1. **Admin Privilege Requirement**
   - Needed for packet capture
   - Needed for firewall rule creation
   - Mitigate: Run in controlled environment

2. **Firewall Rule Accumulation**
   - Problem: Blocking IPs is permanent
   - Risk: IP exhaustion, denial of legitimate IPs
   - Mitigate: Implement rule expiration, automatic cleanup

3. **Honeypot Detection**
   - Risk: Attacker identifies honeypot
   - Mitigate: Improve service emulation, varied responses

4. **Model Poisoning**
   - Risk: Adversary crafts traffic to evade detection
   - Mitigate: Regular model retraining, outlier detection

### Security Best Practices

```python
# 1. Input Validation
- Validate IP addresses (CIDR ranges)
- Validate port numbers (1-65535)
- Validate feature values (no extreme outliers)

# 2. Rate Limiting
- Limit firewall rules per minute (prevent DoS of rule creation)
- Implement backoff on repeated blocks

# 3. Logging & Audit
- Log all administrative actions
- Log model decisions with confidence
- Enable audit trail for regulatory compliance

# 4. Isolation
- Run in separate VLAN if possible
- Monitor the monitor (meta-security)
- Regular security audits of codebase
```

---

## 🚀 Deployment Scenarios

### Scenario 1: Development Environment (Local Machine)

```
Hardware: Laptop (8GB RAM, i7)
OS: Windows 10/11
Setup:
  - Python venv
  - Npcap local install
  - Models on SSD

Limitations:
  - Self-attacks may not be captured
  - Limited throughput
  - Used for testing only

Usage:
  - Model development
  - Feature validation
  - API testing
```

### Scenario 2: Production Server (Windows Server)

```
Hardware: Server (32GB RAM, Xeon)
OS: Windows Server 2019/2022
Setup:
  - Python in virtualenv
  - Npcap in silent install
  - Models on fast storage
  - Logs on separate disk

Requirements:
  - Static IP for monitored interface
  - Firewall rule permissions
  - Backup of firewall state
  - Regular model updates

Monitoring:
  - Dashboard 24/7
  - Alerting on high confidence events
  - Performance monitoring (CPU, memory)
```

### Scenario 3: Edge/IoT Device

```
Hardware: Raspberry Pi 4 (4GB)
OS: Ubuntu 20.04
Setup:
  - Python 3.9
  - Lightweight ML models
  - Reduced feature set (if needed)

Constraints:
  - Limited computational power
  - Slow packet capture
  - Model quantization required
  - Edge-native deployment

Adaptation:
  - Use TinyML or ONNX models
  - Reduce window size
  - Aggregate at cloud if needed
```

---

## 📚 References & Further Reading

### Research Papers
- "Machine Learning for DDoS Detection" - IEEE
- "Honeypot Systems" - ACM Security Reviews
- "Feature Engineering for Network Security" - Journal of Cybersecurity

### Technical Documentation
- Scapy: https://scapy.readthedocs.io/
- Scikit-learn: https://scikit-learn.org/stable/
- Npcap: https://npcap.com/guide/

### Related Projects
- Zeek IDS
- Suricata
- Snort
- YARA

---

**End of Architecture Documentation**

*For questions or clarifications, refer to README.md and EXECUTION_PLAN.md*
