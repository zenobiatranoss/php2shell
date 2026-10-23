set -euo pipefail
SRC=${1:?path to the php-8.4.4 source tree}
PORT=${2:-8099}
HERE="$(cd "$(dirname "$0")" && pwd)"
SESS=/tmp/php-up-lab-sess
ASAN=/tmp/php-up-asan
mkdir -p "$SESS" "$ASAN"
rm -f "$ASAN"/*

cp "$SRC/ext/session/session.c" "$SRC/ext/session/session.c.orig"
python3 - "$SRC/ext/session/session.c" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
old = "\t\tZ_TRY_ADDREF(progress->data);\n"
assert s.count(old) == 1, "line not found (already patched?)"
open(p, "w").write(s.replace(old, "\t\t/* ABLATION: addref removed */\n"))
print("[+] addref removed")
PY

make -C "$SRC" -j"$(nproc 2>/dev/null || sysctl -n hw.ncpu)" >/dev/null
start() {
  USE_ZEND_ALLOC=0 ASAN_OPTIONS="detect_leaks=0:log_path=$ASAN" \
    "$SRC/sapi/cli/php" -c "$HERE/php.ini" -S "127.0.0.1:$PORT" -t "$HERE/webroot" \
    >/dev/null 2>&1 &
  SRV=$!
  sleep 1
}
stop_srv() { kill "$SRV" 2>/dev/null || true; wait "$SRV" 2>/dev/null || true; sleep 0.5; }

echo "[1] ablated build, firing trigger (expect ASAN heap-use-after-free)"
start
python3 "$HERE/test-client.py" "$PORT" || true
sleep 1
stop_srv
if ls "$ASAN"/* >/dev/null 2>&1; then
  echo "[+] ASAN report: $(ls "$ASAN"/* | head -1)"
  head -12 "$ASAN"/* | head -12
else
  echo "[-] no ASAN report (unexpected)"
fi

echo "[2] restoring and rebuilding"
mv "$SRC/ext/session/session.c.orig" "$SRC/ext/session/session.c"
make -C "$SRC" -j"$(nproc 2>/dev/null || sysctl -n hw.ncpu)" >/dev/null
rm -f "$ASAN"/*
start
python3 "$HERE/test-client.py" "$PORT" || true
sleep 1
stop_srv
if ls "$ASAN"/* >/dev/null 2>&1; then
  echo "[-] ASAN still firing after restore (unexpected)"
else
  echo "[+] clean after restore (no ASAN report)"
fi
