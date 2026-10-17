#!/usr/bin/env bash
# Builds the apk inside WSL (Ubuntu). Run it like this:
#   bash /mnt/d/main/Казик/build_android.sh
# Change the path to the folder where this file lies.
set -e

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/kazik_build"
VENV="$HOME/buildozer-venv"

# 1. one-time setup of buildozer in its own virtual environment
if [ ! -d "$VENV" ]; then
    echo ">>> creating $VENV and installing buildozer (one time only)"
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --upgrade pip
    "$VENV/bin/pip" install --upgrade buildozer cython setuptools
fi

# 2. copy the project onto the Linux disk (building on /mnt/d is slow and breaks)
echo ">>> copying the project to $DEST"
mkdir -p "$DEST"
rsync -a --delete \
    --exclude 'myenv' --exclude 'venv' --exclude '.venv' \
    --exclude '__pycache__' --exclude '.git' \
    --exclude '.buildozer' --exclude 'bin' \
    "$SRC"/ "$DEST"/

# 3. build
cd "$DEST"
echo ">>> building (the first build takes a long time)"
"$VENV/bin/buildozer" -v android debug

# 4. bring the apk back to the Windows folder
mkdir -p "$SRC/apk"
cp -v "$DEST"/bin/*.apk "$SRC/apk/"
echo ">>> done: the apk is in $SRC/apk"
