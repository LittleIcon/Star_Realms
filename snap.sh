#!/bin/bash
# Simple snapshot tool for your StarRealms project
# Usage:
#   ./snap.sh save effects.py
#   ./snap.sh list
#   ./snap.sh restore effects.py <SNAPSHOT_NAME>

SNAPDIR=".snapshots"
mkdir -p "$SNAPDIR"

case "$1" in
  save)
    FILE=$2
    if [ -z "$FILE" ]; then
      echo "Usage: $0 save <file>"
      exit 1
    fi
    STAMP=$(date +%Y%m%d-%H%M%S)
    cp "starrealms/$FILE" "$SNAPDIR/${FILE//\//_}.$STAMP"
    echo "✅ Snapshot saved: $SNAPDIR/${FILE//\//_}.$STAMP"
    ;;
  list)
    ls -1t "$SNAPDIR"
    ;;
  restore)
    FILE=$2
    SNAP=$3
    if [ -z "$FILE" ] || [ -z "$SNAP" ]; then
      echo "Usage: $0 restore <file> <snapshot_name>"
      exit 1
    fi
    cp "$SNAPDIR/$SNAP" "starrealms/$FILE"
    echo "♻️ Restored $FILE from $SNAP"
    ;;
  *)
    echo "Usage: $0 {save <file>|list|restore <file> <snapshot_name>}"
    ;;
esac