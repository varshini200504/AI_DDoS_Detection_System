import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
MODELS_DIR = BASE_DIR


def first_existing_path(*relative_names):
    for name in relative_names:
        candidate = MODELS_DIR / name
        if candidate.exists():
            return str(candidate)
    return str(MODELS_DIR / relative_names[0])

# Ensure log dir exists
os.makedirs(LOGS_DIR, exist_ok=True)

# Detection window and thresholds
WINDOW_SIZE = 3
MIN_PACKETS_THRESHOLD = 10
BINARY_CONFIDENCE_THRESHOLD = 0.75

# Model files (prefer standard names, fall back to lightweight aliases)
BINARY_MODEL_PATH = first_existing_path(
    "binary_ddos_model.pkl",
    "binary_ddos_model_light.pkl"
)
MULTICLASS_MODEL_PATH = first_existing_path(
    "best_ddos_model.pkl",
    "best_ddos_model_light.pkl"
)
SCALER_PATH = first_existing_path(
    "binary_feature_scaler.pkl",
    "binary_feature_scaler_light.pkl"
)

# Network defaults (edit for your environment)
MONITORED_IP = "192.168.1.4"
MONITORED_PORTS = {5000, 5001, 8081, 80}

# Safe IPs to ignore
SAFE_IPS = {
    "127.0.0.1",
    "0.0.0.0",
    "255.255.255.255",
    "192.168.1.1"
}

# Logging
LOG_FILE = str(LOGS_DIR / "security_actions.log")

# Default interface fallback (None -> auto-detect)
DEFAULT_INTERFACE = None
