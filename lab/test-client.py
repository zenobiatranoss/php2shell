import socket
import sys
import time

HOST = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
B = "----b"
SID = "a" * 32


def build():
    body = (
        f"--{B}\r\nContent-Disposition: form-data; name=\"PHPSESSID\"\r\n\r\n{SID}\r\n"
        f"--{B}\r\nContent-Disposition: form-data; name=\"PHP_SESSION_UPLOAD_PROGRESS\"\r\n\r\nx\r\n"
        f"--{B}\r\nContent-Disposition: form-data; name=\"f\"; filename=\"a\"\r\n\r\nZ\r\n"
        f"--{B}--\r\n"
    ).encode()
    return body


def main():
    body = build()
    assert len(body) == 258, len(body)
    head = (
        f"POST /index.php HTTP/1.1\r\nHost: {HOST}\r\n"
        f"Content-Type: multipart/form-data; boundary={B}\r\n"
        f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    ).encode()
    cut = body.index(b'filename="a"\r\n\r\n') + len(b'filename="a"\r\n\r\n')
    s = socket.create_connection((HOST, PORT), timeout=10)
    s.sendall(head + body[:cut])
    time.sleep(1.4)        
    s.sendall(body[cut:])
    s.settimeout(10)
    out = b""
    try:
        while True:
            d = s.recv(4096)
            if not d:
                break
            out += d
    except socket.timeout:
        pass
    s.close()
    print(out.split(b"\r\n", 1)[0].decode("latin1") if out else "NO-RESPONSE")


if __name__ == "__main__":
    main()
