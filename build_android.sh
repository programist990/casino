#!/usr/bin/env bash
# Builds the debug apk inside WSL2 (Ubuntu 24.04). Run it like this:
#   bash /mnt/d/main/casino_origin/build_android.sh
# Options:
#   clean   - wipe the build cache first (use after strange errors)
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/casino_build"
VENV="$HOME/buildozer-venv"

# 0. checks
for cmd in python3 java rsync unzip zip git; do
    command -v "$cmd" >/dev/null 2>&1 || {
        echo "!!! '$cmd' is not installed. Do step 2 of ANDROID_BUILD.md first."
        exit 1
    }
done
PYV="$(python3 -c 'import sys; print("%d%02d" % sys.version_info[:2])')"
if [ "$PYV" -gt 312 ]; then
    echo "!!! python3 is newer than 3.12; python-for-android 'master' needs 3.12 or older."
    echo "    Use Ubuntu 24.04 (python 3.12), see ANDROID_BUILD.md."
    exit 1
fi
JAVAV="$(java -version 2>&1 | head -1 | sed -E 's/.*"([0-9]+).*/\1/')"
if [ "$JAVAV" != "17" ]; then
    echo "!!! java $JAVAV is selected, buildozer needs 17: sudo update-alternatives --config java"
    exit 1
fi

# 1. one-time setup of buildozer in its own virtual environment
if [ ! -x "$VENV/bin/buildozer" ]; then
    echo ">>> creating $VENV and installing buildozer (one time only)"
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --upgrade pip
    "$VENV/bin/pip" install --upgrade buildozer setuptools "cython==0.29.34"
fi

# 2. copy the project onto the Linux disk (building on /mnt/d is slow and breaks)
if [ "${1:-}" = "clean" ]; then
    echo ">>> cleaning the build cache"
    rm -rf "$DEST/.buildozer" "$DEST/bin"
fi
echo ">>> copying the project to $DEST"
mkdir -p "$DEST"
rsync -a --delete \
    --exclude 'myenv' --exclude 'venv' --exclude '.venv' \
    --exclude '__pycache__' --exclude '.git' \
    --exclude '.buildozer' --exclude 'bin' --exclude 'apk' \
    "$SRC"/ "$DEST"/

# 3. build
cd "$DEST"
echo ">>> building (the first build takes a long time)"
"$VENV/bin/buildozer" -v android debug 2>&1 | tee "$SRC/build.log"

# 4. bring the apk back to the Windows folder
mkdir -p "$SRC/apk"
cp -v "$DEST"/bin/*.apk "$SRC/apk/"
echo ">>> done: the apk is in $SRC/apk"
