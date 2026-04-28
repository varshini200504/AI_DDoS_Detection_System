import socket
import threading
from flask import Flask

# ==========================
# CONFIG
# ==========================
HTTP_PORT = 5000
UDP_PORT = 5001
TCP_PORT = 8081

# ==========================
# FLASK HTTP SERVER
# ==========================
app = Flask(__name__)

@app.route("/")
def home():
    return "Victim server active", 200

def run_http_server():
    print(f"[HTTP] Victim server running on port {HTTP_PORT}")
    app.run(
        host="0.0.0.0",
        port=HTTP_PORT,
        debug=False,
        use_reloader=False
    )

# ==========================
# UDP SERVER
# ==========================
def run_udp_server():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(("0.0.0.0", UDP_PORT))

    print(f"[UDP] Victim server running on port {UDP_PORT}")

    while True:
        try:
            data, addr = udp_sock.recvfrom(4096)

        except:
            continue

# ==========================
# TCP SERVER
# ==========================
def handle_tcp_client(client_socket):
    try:
        client_socket.send(
            b"Victim TCP service active\r\n"
        )

    except:
        pass

    client_socket.close()

def run_tcp_server():
    tcp_sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    tcp_sock.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    tcp_sock.bind(("0.0.0.0", TCP_PORT))
    tcp_sock.listen(100)

    print(f"[TCP] Victim server running on port {TCP_PORT}")

    while True:
        try:
            client, addr = tcp_sock.accept()

            client_thread = threading.Thread(
                target=handle_tcp_client,
                args=(client,),
                daemon=True
            )

            client_thread.start()

        except:
            continue

# ==========================
# MAIN
# ==========================
if __name__ == "__main__":
    print("==== VICTIM SERVER STARTING ====")

    # HTTP
    http_thread = threading.Thread(
        target=run_http_server,
        daemon=True
    )

    # UDP
    udp_thread = threading.Thread(
        target=run_udp_server,
        daemon=True
    )

    # TCP
    tcp_thread = threading.Thread(
        target=run_tcp_server,
        daemon=True
    )

    http_thread.start()
    udp_thread.start()
    tcp_thread.start()

    print("")
    print(f"HTTP Port : {HTTP_PORT}")
    print(f"UDP Port  : {UDP_PORT}")
    print(f"TCP Port  : {TCP_PORT}")
    print("")
    print("Victim services active.")
    print("Press Ctrl+C to stop.")

    # Keep alive
    while True:
        pass