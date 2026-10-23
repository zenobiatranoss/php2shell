set -euo pipefail
DEST=${1:-/tmp/php-asan}
VER=${2:-8.4.4}
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/build" && cd "$ROOT/build"

[ -f "php-$VER.tar.gz" ] || curl -sSLO "https://www.php.net/distributions/php-$VER.tar.gz"
[ -d "php-$VER" ] || tar xzf "php-$VER.tar.gz"
cd "php-$VER"

./configure --disable-all --enable-cli --enable-session --disable-cgi \
  --without-pear --disable-phpdbg \
  CFLAGS="-fsanitize=address -fno-omit-frame-pointer -g -O1" \
  LDFLAGS="-fsanitize=address"
make -j"$(nproc 2>/dev/null || sysctl -n hw.ncpu)"
cp sapi/cli/php "$DEST"
echo "[+] built: $DEST"
