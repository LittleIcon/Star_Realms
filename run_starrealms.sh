#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# --- Locate project (this script's directory) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Start Termux:X11 if not running ---
if ! pgrep -f "termux-x11 :0" >/dev/null 2>&1; then
  echo "Starting Termux:X11 server…"
  termux-x11 :0 >/dev/null 2>&1 &
  # give it a moment to spin up
  sleep 1
fi

# --- Env for pygame on Termux:X11 ---
export DISPLAY=:0
export XDG_RUNTIME_DIR="${TMPDIR}"
unset SDL_VIDEODRIVER
export PYGAME_HIDE_SUPPORT_PROMPT=1

# --- Optional: probe that pygame can open a window (fast & quiet) ---
python - <<'PY' || { echo "⚠️  Could not open X11 window. Is the Termux:X11 app visible?"; exit 1; }
import pygame, time
pygame.display.init()
pygame.display.set_mode((10,10))  # tiny test window
pygame.display.quit()
PY

# --- Launch the game ---
exec python pygame_main.py
