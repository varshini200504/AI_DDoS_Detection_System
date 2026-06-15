# 🛡️ Lightweight Real-Time AI-Powered DDoS Detection & Adaptive Mitigation Platform

**A Practical, Patent-Worthy, Edge-Deployable Cybersecurity Framework**

---

## 📋 Project Overview

This is a **lightweight, real-time, host-based DDoS detection and adaptive mitigation platform** designed for deployment on **edge devices, IoT systems, and low-resource hosts**. It combines:

- **Two-stage ML pipeline**: Binary detection → Multiclass attack classification
- **Adaptive response engine**: Monitor → Rate Limit → Block → Honeypot redirection
- **Real-time packet monitoring**: Scapy-based network traffic analysis
- **Explainable AI**: Feature-based reasoning for detection decisions
- **Integrated honeypot**: Deception-based threat redirection
- **Live dashboard**: Web-based event visualization
- **Lightweight architecture**: Only 17 realistic features extracted from live traffic

### 🎯 Core Innovation

Instead of claiming to "invent" DDoS detection, we position novelty as:
> **"A lightweight edge-defense cybersecurity framework combining minimal-feature ML inference, adaptive mitigation policies, and honeypot deception for practical real-time deployment on resource-constrained systems."**

**Patent-worthy contributions:**
1. Two-stage binary + multiclass detection pipeline
2. Reduced feature set (~17 features vs. 80+) for real-time extraction
3. Adaptive confidence-based response engine
4. Integrated honeypot redirection
5. Host-based edge deployment architecture

---

## 🏗️ System Architecture

### Component Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATASET PIPELINE                             │
├─────────────────────────────────────────────────────────────────┤
│  CICIDS2017 / CICDDoS2019 CSV → Chunk Loading → Feature          │
│  Extraction (17 lightweight features) → Balancing → Output CSV  │
│                    (combine.py)                                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    MODEL TRAINING                               │
├─────────────────────────────────────────────────────────────────┤
│  Binary Model (Normal vs Attack)                                 │
│  - Decision Tree / Random Forest / XGBoost                       │
│  - Save: binary_ddos_model.pkl + scaler                         │
│                    (train5.py)                                   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                REAL-TIME DETECTION & RESPONSE                   │
├─────────────────────────────────────────────────────────────────┤
│  Live Packet Capture (Scapy) → Feature Extraction               │
│  → Binary Classification → Multiclass Attack Type               │
│  → Adaptive Response Engine → Action (Block/Rate Limit/etc)    │
│  → Logging → Dashboard Visualization                            │
│         (realtime_monitor.py + adaptive_response.py)           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                DEFENSE COMPONENTS                               │
├─────────────────────────────────────────────────────────────────┤
│  • Firewall Integration (Windows netsh)                          │
│  • Rate Limiting (simulated)                                     │
│  • Honeypot Redirection (fake vulnerable service)               │
│  • Event Logging                                                 │
│         (adaptive_response.py + honeypot.py)                    │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
d:\DDoS_attack_mitigation\
├── README.md                                    # This file
├── EXECUTION_PLAN.md                            # Detailed next steps
├── ARCHITECTURE.md                              # Technical deep-dive
│
├── [DATASET PIPELINE]
├── combine.py                                   # Dataset preprocessing
├── final_multiclass_dataset_large.csv          # Balanced training data
├── final_dataset.csv                            # Binary training data
│
├── [MODEL TRAINING]
├── train5.py                                    # ML model training (XGBoost/RF/DT)
├── binary_ddos_model.pkl                        # Trained binary classifier
├── best_ddos_model.pkl                          # Multiclass classifier
├── binary_feature_scaler.pkl                    # Feature normalization
├── binary_model_comparison_results.csv          # Performance metrics
├── binary_model_accuracy_comparison.png         # Accuracy plot
│
├── [REAL-TIME DETECTION]
├── realtime_monitor.py                          # Packet capture + ML inference
├── adaptive_response.py                         # Response engine + honeypot
├── honeypot.py                                  # Honeypot service (empty - needs completion)
├── logs/
│   └── security_actions.log                     # Detailed attack logs
│
├── [TESTING & DEMONSTRATION]
├── victim.py                                    # Multi-protocol victim server
├── attack_simulator.py                          # Attack generation (HTTP/UDP/SYN)
├── dashboard.py                                 # Flask web dashboard
│
└── [DATA FOLDERS - Not included in repo]
    ├── data-attack/                             # Attack CSV files (CICIDS2017/CICDDoS2019)
    │   ├── DrDoS_DNS.csv
    │   ├── DrDoS_NTP.csv
    │   ├── DrDoS_SNMP.csv
    │   ├── Syn.csv
    │   └── ... (11 attack types total)
    │
    └── data-normal/                             # Normal traffic CSV files
        └── benign_traffic.csv
```

---

## 🔧 Technical Specifications

### Lightweight Feature Set (17 Features)

Extracted from live packet capture using Scapy:

| # | Feature | Type | Purpose |
|---|---------|------|---------|
| 1 | Flow Duration | Temporal | Duration of captured flow |
| 2 | Flow Packets/s | Rate | Packets per second |
| 3 | Flow Bytes/s | Rate | Bytes per second |
| 4 | Total Fwd Packets | Count | Forward direction packets |
| 5 | Total Backward Packets | Count | Backward direction packets |
| 6 | Total Length of Fwd Packets | Size | Forward payload bytes |
| 7 | Total Length of Bwd Packets | Size | Backward payload bytes |
| 8 | Packet Length Mean | Statistical | Average packet size |
| 9 | Packet Length Std | Statistical | Packet size variance |
| 10 | Average Packet Size | Derived | Total bytes / total packets |
| 11 | SYN Flag Count | TCP Flag | SYN count in flow |
| 12 | ACK Flag Count | TCP Flag | ACK count in flow |
| 13 | RST Flag Count | TCP Flag | RST count in flow |
| 14 | PSH Flag Count | TCP Flag | PSH count in flow |
| 15 | Down/Up Ratio | Ratio | Backward/Forward packet ratio |
| 16 | Destination Port | Network | Target port number |
| 17 | Protocol | Network | TCP (6) or UDP (17) |

### Attack Types (12 Classes)

```
0 = Normal Traffic
1 = DrDoS_DNS (Distributed DNS Reflection)
2 = DrDoS_NTP (NTP Amplification)
3 = DrDoS_SNMP (SNMP Reflection)
4 = DrDoS_SSDP (SSDP Reflection)
5 = LDAP (LDAP Amplification)
6 = MSSQL (MS-SQL Server Attack)
7 = NetBIOS (NetBIOS Amplification)
8 = Portmap (Portmap Reflection)
9 = Syn (SYN Flood)
10 = TFTP (TFTP Reflection)
11 = UDP (UDP Flood)
12 = UDPLag (UDP with packet loss)
```

### Adaptive Response Engine

```
Confidence Level         → Action
─────────────────────────────────
< 0.60 (Low confidence)  → MONITOR (log only)
0.60 - 0.85              → RATE_LIMIT (throttle connection)
> 0.85 (High confidence) → Protocol-specific:
                            - SYN/UDP/Portmap → BLOCK (firewall)
                            - DDoS Reflection → HONEYPOT (redirect)
                            - Other → BLOCK
```

### ML Model Architecture

**Binary Classifier (Normal vs Attack):**
- Algorithm: Random Forest (best tradeoff of speed/accuracy)
- Alternative: XGBoost, Decision Tree
- Feature scaling: StandardScaler
- Input: 17 features
- Output: 0 (Normal), 1 (Attack) + Confidence [0-1]

**Multiclass Classifier (Attack Type):**
- Algorithm: Random Forest
- Input: Same 17 features
- Output: Attack label [1-12]

---

## 📦 Dependencies

### Core Libraries

```
scapy>=2.4.5               # Packet capture & network analysis
flask>=2.0.0               # Web dashboard
scikit-learn>=1.0.0        # ML models (Random Forest, Decision Tree)
xgboost>=1.5.0             # XGBoost classifier (optional but recommended)
joblib>=1.0.0              # Model serialization
pandas>=1.3.0              # Data manipulation
numpy>=1.20.0              # Numerical computing
psutil>=5.8.0              # System monitoring (CPU usage)
requests>=2.26.0           # HTTP requests (attack simulator)
matplotlib>=3.4.0          # Plotting & visualization
```

### System Requirements

**Windows-specific:**
- Npcap: Required for packet capture on Windows
  - Download: https://npcap.com/
  - Install with Admin privileges

**Admin Privileges Required For:**
- Packet capture (Scapy sniffing)
- Windows Firewall rule creation (netsh)

**Minimum Hardware:**
- RAM: 4GB (tested on 32GB)
- CPU: Dual-core (affects real-time performance)
- Network Interface: Standard Ethernet or Wi-Fi

---

## 🚀 Quick Start Guide

### 1. Environment Setup (Windows)

#### Step 1: Install Python 3.8+
```bash
# Verify Python installation
python --version
```

#### Step 2: Install Npcap (Windows Packet Capture)
```
1. Download from: https://npcap.com/
2. Run installer with Admin privileges
3. Choose "Install Npcap in WinPcap API-compatible Mode"
4. Complete installation
```

#### Step 3: Create Virtual Environment
```bash
# Create venv
python -m venv venv

# Activate venv
# Windows CMD:
venv\Scripts\activate

# Windows PowerShell:
venv\Scripts\Activate.ps1
```

#### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Dataset Preparation

**Important:** Large dataset files (CICIDS2017/CICDDoS2019) are NOT included in repo.

#### Option A: Manual Dataset Acquisition
1. Download CICIDS2017 or CICDDoS2019 datasets
2. Extract CSV files to:
   ```
   data-attack/          # Attack samples
   data-normal/          # Normal samples
   ```
3. Run preprocessing:
   ```bash
   python combine.py
   ```
   Output: `final_multiclass_dataset_large.csv`

#### Option B: Use Pre-trained Models (If Available)
- If `binary_ddos_model.pkl` exists, skip training

### 3. Model Training

If pre-trained models not available:

```bash
# Train binary classification model
python train5.py
```

**Output:**
- `binary_ddos_model.pkl` - Binary classifier
- `best_ddos_model.pkl` - Multiclass classifier  
- `binary_feature_scaler.pkl` - Feature scaler
- `binary_model_accuracy_comparison.png` - Performance chart

### 4. Start Demonstration Environment

**Terminal 1: Start Victim Server**
```bash
python victim.py
```
Output:
```
[HTTP] Victim server running on port 5000
[UDP] Victim server running on port 5001
[TCP] Victim server running on port 8080
```

**Terminal 2: Start Real-Time Monitor**
```bash
# Run with Admin privileges
python realtime_monitor.py
```
Output:
```
Loading models...
Models loaded successfully!
Starting real-time DDoS monitor...
Protecting IP: 192.168.1.4
Protected Ports: {5000, 8080, 80}
```

**Terminal 3: Start Dashboard**
```bash
python dashboard.py
```
Open browser: `http://127.0.0.1:5000`

**Terminal 4: Launch Attack Simulator**
```bash
# Run with Admin privileges
python attack_simulator.py
```
Menu:
```
1. HTTP Flood
2. UDP Flood
3. SYN Flood
```

---

## 📊 Expected Output Example

### Dashboard Display

```
🚨 Real-Time DDoS Detection Dashboard 🚨
Total Logged Events: 45

Timestamp               | Source IP      | Attack Type   | Action Taken    | Confidence
─────────────────────────────────────────────────────────────────────────────────────
2025-01-15 14:32:15   | 192.168.1.100  | Syn          | BLOCK           | 0.92
2025-01-15 14:32:14   | 192.168.1.101  | UDP          | BLOCK           | 0.88
2025-01-15 14:32:13   | 192.168.1.102  | DrDoS_DNS    | HONEYPOT        | 0.91
2025-01-15 14:32:12   | 192.168.1.4    | Normal       | MONITOR         | 0.45
```

### Real-Time Monitor Output

```
===== REAL-TIME ANALYSIS =====
Captured: 192.168.1.100 -> 192.168.1.4:5000
192.168.1.100 -> ATTACK DETECTED: Syn
Confidence: 0.92
Reason: SYN=245, ACK=12, Packets/sec=4523.50
Action for 192.168.1.100: BLOCK

CPU Usage: 12.3%
==============================
```

---

## 🔍 Key Technical Details

### Feature Extraction Window

- **Time Window:** 3 seconds (configurable in `realtime_monitor.py`)
- **Aggregation:** By source IP
- **Minimum Threshold:** 10 packets before classification
- **Port Filtering:** Only monitors target ports (5000, 8080, 80)
- **IP Filtering:** Ignores safe infrastructure (127.0.0.1, 192.168.1.1, etc.)

### Model Inference Pipeline

```
Live Packets → 3-sec Window → Feature Extraction (17 features)
  → StandardScaler normalization
  → Binary Model Prediction (Normal/Attack)
  → If Attack: Multiclass Model Prediction (12 attack types)
  → Confidence-based Response Engine
  → Action Execution + Logging
```

### Performance Metrics (Typical)

Based on `train5.py` results:

| Metric | Random Forest | XGBoost | Decision Tree |
|--------|---------------|---------|---------------|
| Binary Accuracy | 98-99% | 98-99% | 95-97% |
| Training Time | 2-5 sec | 5-10 sec | <1 sec |
| Prediction Time | 0.5-2 ms | 1-3 ms | 0.1 ms |
| CPU Memory | ~500 MB | ~800 MB | ~200 MB |

---

## ⚠️ Known Limitations & Challenges

### 1. Windows Packet Capture Issues

**Problem:**
- Npcap/WinPcap API inconsistencies
- Interface naming variations
- Loopback traffic complications
- Local routing challenges for self-attacks

**Workaround:**
- Run victim server on separate machine (production)
- Use external attack source for reliable testing
- Verify interface name: `ipconfig /all`

### 2. Local Attack Simulation Limitations

**Problem:**
- Self-attacks may not be captured by Scapy
- Windows routing may bypass local packet capture
- SYN floods less effective on loopback

**Workaround:**
- Use external threat machine
- Use network simulation tools
- Run victim on separate machine

### 3. Feature Mismatch in Real-Time

**Problem:**
- Initial training datasets had 80+ features
- Real-time extraction limited to 17 features
- Some feature variations in live traffic

**Workaround:**
- Train models with only 17 features (done in `combine.py`)
- Use the same 17 features everywhere
- Validate feature extraction matches training

### 4. High False Positive Rate on Internet

**Problem:**
- Google, Cloudflare, Microsoft infrastructure triggers false alerts
- Normal P2P traffic can look like attacks

**Workaround:**
- IP whitelist (SAFE_IPS)
- Port filtering
- Confidence thresholds
- Restrict monitoring to specific IPs/ports

---

## 📈 Project Deliverables & Timelines

### Research Paper

**Target Title:**
> "Lightweight Real-Time AI-Based DDoS Detection and Adaptive Honeypot Mitigation Framework for Edge Systems"

**Key Sections:**
1. Introduction (Problem + Novelty)
2. Related Work (DDoS detection landscape)
3. Proposed Architecture (17-feature pipeline, adaptive response)
4. Experimental Setup (Datasets, models, metrics)
5. Results (Accuracy, latency, resource usage)
6. Conclusion + Future Work

**Target Venues:**
- IEEE/ACM cybersecurity conferences
- Journal on cybersecurity
- Computer networks publications

### Patent Draft

**Patent Title:**
> "Adaptive Multi-Layer Lightweight Host-Based Cybersecurity Framework Integrating Machine Learning and Deception-Based Mitigation"

**Key Claims:**
1. Two-stage ML classification (binary + multiclass)
2. Lightweight reduced feature set
3. Adaptive confidence-based response
4. Integrated honeypot redirection
5. Edge-deployable architecture

### Demonstration

**Components to Demo:**
1. Real-time attack detection
2. Attack classification
3. Adaptive response triggering
4. Dashboard visualization
5. Honeypot redirection
6. System performance metrics

---

## 🐛 Troubleshooting

### Issue: "No module named scapy"
```bash
pip install scapy
```

### Issue: "Npcap not installed" (Windows)
```
Download and install from https://npcap.com/
Requires admin installation
```

### Issue: "Permission denied" on packet capture
```
Run Python terminal as Administrator
```

### Issue: "Cannot find interface"
```bash
# List all interfaces:
python -c "from scapy.all import get_if_list; print(get_if_list())"

# Update INTERFACE variable in realtime_monitor.py
```

### Issue: "Dashboard not updating"
```
Check that logs/security_actions.log exists
Verify adaptive_response.py is running
Check Flask is running on 127.0.0.1:5000
```

---

## 📚 References & Documentation

- **Scapy Documentation:** https://scapy.readthedocs.io/
- **Scikit-learn ML Models:** https://scikit-learn.org/
- **Flask Web Framework:** https://flask.palletsprojects.com/
- **XGBoost:** https://xgboost.readthedocs.io/
- **CICIDS2017 Dataset:** https://www.unb.ca/cic/datasets/ids-2017.html
- **CICDDoS2019 Dataset:** https://www.unb.ca/cic/datasets/ddos-2019.html
- **DDoS Detection Papers:** IEEE Xplore, ACM Digital Library

---

## 👥 Team & Attribution

**University-Funded Research Program (URF Round II)**

**Project Status:** Active Development

**Last Updated:** 2025-01-15

---

## 📝 License

[Specify your license - MIT, Apache 2.0, etc.]

---

## 📞 Contact & Support

For questions or issues:
- Check EXECUTION_PLAN.md for detailed next steps
- Review ARCHITECTURE.md for technical deep-dive
- Run `python <module> -h` for module-specific help.

---

**This README serves as the foundation for your academic publication, patent application, and institutional presentation.**
