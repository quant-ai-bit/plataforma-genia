import socket
import threading
from datetime import datetime

LOG_FILE = "backend/proxy_log.txt"

def log_proxy(msg):
    print(msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()}: {msg}\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")

class HTTPProxy:
    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port

    def handle_client(self, client_socket):
        try:
            request = client_socket.recv(4096)
            if not request:
                client_socket.close()
                return

            first_line = request.split(b'\n')[0].decode(errors='ignore')
            parts = first_line.split(' ')
            if len(parts) < 2:
                client_socket.close()
                return

            method, url = parts[0], parts[1]

            if method == 'CONNECT':
                log_proxy(f"[Proxy Request] CONNECT {url}")
                host_port = url.split(':')
                dest_host = host_port[0]
                dest_port = int(host_port[1]) if len(host_port) > 1 else 443

                try:
                    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    remote_socket.connect((dest_host, dest_port))
                    log_proxy(f"[Proxy Success] Connected to {dest_host}:{dest_port}")
                except Exception as e:
                    log_proxy(f"[Proxy Error] Failed to connect to {dest_host}:{dest_port} - {e}")
                    client_socket.close()
                    return
                
                client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")

                # Robust TCP Half-Close implementation to prevent WebSockets drops
                state = {'count': 2}
                
                def forward(src, dst, name):
                    try:
                        while True:
                            data = src.recv(16384)  # Increased buffer size for performance
                            if not data:
                                log_proxy(f"[Proxy Close] Connection closed by source on {dest_host}:{dest_port} ({name})")
                                break
                            dst.sendall(data)
                    except Exception as e:
                        log_proxy(f"[Proxy Error] Error forwarding data on {dest_host}:{dest_port} ({name}): {e}")
                    finally:
                        try:
                            dst.shutdown(socket.SHUT_WR)
                        except Exception:
                            pass
                        
                        state['count'] -= 1
                        if state['count'] == 0:
                            log_proxy(f"[Proxy Done] Tunnel closed for {dest_host}:{dest_port}")
                            try: client_socket.close()
                            except: pass
                            try: remote_socket.close()
                            except: pass

                threading.Thread(target=forward, args=(client_socket, remote_socket, "client->remote"), daemon=True).start()
                threading.Thread(target=forward, args=(remote_socket, client_socket, "remote->client"), daemon=True).start()
            else:
                client_socket.close()
        except Exception as e:
            log_proxy(f"[Proxy Connection Error] {e}")
            client_socket.close()

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(100)
        log_proxy(f"HTTP Proxy server running on {self.host}:{self.port} (Colombia)")
        try:
            while True:
                client_socket, addr = server.accept()
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
        except KeyboardInterrupt:
            log_proxy("Shutting down proxy.")
        finally:
            server.close()

if __name__ == '__main__':
    HTTPProxy().start()
