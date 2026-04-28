import socket
import threading
import logging
from datetime import datetime


class Honeypot:
    def __init__(self, port=8080, service_type='generic', log_file='logs/honeypot.log'):
        self.port = port
        self.service_type = service_type
        self.log_file = log_file
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )

    def serve_http_banner(self, client):
        banner = b"HTTP/1.1 200 OK\r\nServer: Apache/2.2.1\r\n\r\nWelcome\r\n"
        try:
            client.send(banner)
        except:
            pass

    def serve_ssh_banner(self, client):
        banner = b"SSH-2.0-OpenSSH_5.1\r\n"
        try:
            client.send(banner)
        except:
            pass

    def serve_mysql_banner(self, client):
        banner = b"\x00\x00\x00\x0a5.1.45-log\x00\x08\x00\x00\x00\x7b\x42\x33\x09\x00"
        try:
            client.send(banner)
        except:
            pass

    def handle_client(self, client, addr):
        attacker_ip = addr[0]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"HONEYPOT_CAPTURED | IP={attacker_ip} | Service={self.service_type} | Time={timestamp}")
        print(f"[HONEYPOT] Captured: {attacker_ip} attempting {self.service_type}")

        try:
            if self.service_type == 'http':
                self.serve_http_banner(client)
            elif self.service_type == 'ssh':
                self.serve_ssh_banner(client)
            elif self.service_type == 'mysql':
                self.serve_mysql_banner(client)
            else:
                client.send(b"Fake vulnerable service\r\n")
        except:
            pass
        finally:
            try:
                client.close()
            except:
                pass

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.port))
        server.listen(100)

        print(f"[HONEYPOT] Running {self.service_type} on port {self.port}")

        while True:
            try:
                client, addr = server.accept()
                thread = threading.Thread(target=self.handle_client, args=(client, addr), daemon=True)
                thread.start()
            except Exception as e:
                logging.error(f"Honeypot error: {e}")
                continue


if __name__ == "__main__":
    honeypots = [
        Honeypot(port=8080, service_type='http'),
        Honeypot(port=2222, service_type='ssh'),
        Honeypot(port=3306, service_type='mysql'),
    ]

    for hp in honeypots:
        thread = threading.Thread(target=hp.start, daemon=True)
        thread.start()

    print("[HONEYPOT] All services started")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Stopping honeypots")
