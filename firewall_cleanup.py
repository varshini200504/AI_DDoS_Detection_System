import os
import json
from datetime import datetime, timedelta

LOG_DIR = "logs"
FIREWALL_RULES_FILE = os.path.join(LOG_DIR, "firewall_rules.json")

def cleanup_rules(older_than_minutes=60):
    if not os.path.exists(FIREWALL_RULES_FILE):
        print("No firewall rules file found.")
        return

    try:
        with open(FIREWALL_RULES_FILE, 'r') as f:
            rules = json.load(f)
    except Exception as e:
        print(f"Error reading rules file: {e}")
        return

    cutoff = datetime.utcnow() - timedelta(minutes=older_than_minutes)
    remaining = []

    for r in rules:
        try:
            ts = datetime.fromisoformat(r.get('timestamp'))
        except Exception:
            continue

        if ts < cutoff:
            rule_name = r.get('rule_name')
            # Attempt to delete firewall rule (Windows)
            os.system(f'netsh advfirewall firewall delete rule name="{rule_name}"')
            print(f"Deleted rule: {rule_name}")
        else:
            remaining.append(r)

    with open(FIREWALL_RULES_FILE, 'w') as f:
        json.dump(remaining, f, indent=2)

if __name__ == '__main__':
    cleanup_rules(older_than_minutes=60)
