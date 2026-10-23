import glob
import os
import signal
import socket
import subprocess
import sys
import time

PHP = sys.argv[1] if len(sys.argv) > 1 else "/tmp/php-asan"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8100
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)))
INI = os.path.join(ROOT, "php.ini")
WEB = os.path.join(ROOT, "webroot")
SESS = "/tmp/php-up-lab-sess"
ASAN = "/tmp/php-up-asan"

os.makedirs(WEB, exist_ok=True)
os.makedirs(SESS, exist_ok=True)
os.makedirs(ASAN, exist_ok=True)
open(os.path.join(WEB, "index.php"), "w").write('<?php echo "OK\\n";')


def start(extra, tag):
    env = dict(os.environ, USE_ZEND_ALLOC="0",
               ASAN_OPTIONS="detect_leaks=0:log_path=" + ASAN)
    args = [PHP, "-c", INI, "-S", f"127.0.0.1:{PORT}", "-t", WEB] + extra
    p = subprocess.Popen(args, env=env, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", PORT), timeout=0.2).close()
            break
        except Exception:
            time.sleep(0.1)
    return p


def stop(p):
    try:
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
    except Exception:
        pass
    time.sleep(0.4)


def part(b, name, data, fn=None):
    d = f'Content-Disposition: form-data; name="{name}"'
    if fn:
        d += f'; filename="{fn}"'
    return (f"--{b}\r\n{d}\r\n\r\n").encode() + data


def build(fields=(), files=(), b="----z", sid="d" * 32, key="x"):
    body = part(b, "PHPSESSID", sid.encode()) + b"\r\n"
    body += part(b, "PHP_SESSION_UPLOAD_PROGRESS", key.encode()) + b"\r\n"
    for n, v in fields:
        body += part(b, n, v) + b"\r\n"
    for n, data, fn in files:
        body += part(b, n, data, fn) + b"\r\n"
    return body + (f"--{b}--\r\n").encode()


def send(body, split=None, close_early=False):
    b = "----z"
    head = (f"POST /index.php HTTP/1.1\r\nHost: 127.0.0.1\r\n"
            f"Content-Type: multipart/form-data; boundary={b}\r\n"
            f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode()
    s = socket.create_connection(("127.0.0.1", PORT), timeout=10)
    try:
        if split:
            s.sendall(head + body[:split])
            time.sleep(1.2)
            s.sendall(body[split:])
        else:
            s.sendall(head + body)
        if close_early:
            s.close()
            return "<closed>"
        s.settimeout(15)
        out = b""
        while True:
            try:
                d = s.recv(65536)
            except socket.timeout:
                break
            if not d:
                break
            out += d
        return out.split(b"\r\n", 1)[0].decode("latin1") if out else "NO-RESPONSE"
    finally:
        try:
            s.close()
        except Exception:
            pass


def alive():
    try:
        socket.create_connection(("127.0.0.1", PORT), timeout=2).close()
        return True
    except Exception:
        return False


CASES = [
    ("cleanup=1 single", ["-d", "session.upload_progress.cleanup=1"],
     build(files=[("f", b"Z", "a")])),
    ("php_serialize", ["-d", "session.serialize_handler=php_serialize"],
     build(files=[("f", b"Z", "a")])),
    ("php_binary", ["-d", "session.serialize_handler=php_binary"],
     build(files=[("f", b"Z", "a")])),
    ("3 files", [], build(files=[("f", b"Z" * 6000, "a"),
                                 ("g", b"Y" * 6000, "b"),
                                 ("h", b"X" * 6000, "c")])),
    ("5MB file", [], build(files=[("f", b"Q" * (5 * 1024 * 1024), "a")])),
    ("300 fields+2files", [], build(fields=[("t[]", b"P" * 288) for _ in range(300)],
                                    files=[("f", b"Z" * 6000, "a"),
                                           ("g", b"Y" * 6000, "b")])),
    ("weird filename", [], build(files=[("f", b"Z", 'a"b\\c')])),
    ("abort mid-file", [], build(files=[("f", b"Z" * 20000, "a")])),
    ("cancel_upload", [], build(files=[("f", b"Z" * 4000, "a")])),
]


def main():
    print(f"{'case':20s} {'http':22s} {'asan':6s} worker")
    for name, extra, body in CASES:
        for f in glob.glob(ASAN + "/*"):
            os.remove(f)
        p = start(extra, name)
        try:
            split = len(body) // 3 if name != "abort mid-file" else len(body) // 2
            st = send(body, split=split, close_early=(name == "abort mid-file"))
            time.sleep(0.6)
            a = "YES" if glob.glob(ASAN + "/*") else "no"
            print(f"{name:20s} {st[:22]:22s} {a:6s} {'alive' if alive() else 'DEAD'}")
        finally:
            stop(p)


if __name__ == "__main__":
    main()
