#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PROJECT_DIR="/storage/emulated/0/StarRealms"
VENV="$HOME/.venvs/starrealms"
PY="$VENV/bin/python"
MAIN_PY="$PROJECT_DIR/main.py"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

ensure_venv(){ [ -x "$PY" ] || { echo "Missing venv at $VENV"; exit 1; }; }

is_x_running(){ pgrep -af "termux-x11" >/dev/null 2>&1; }
start_x(){
  if is_x_running; then echo "Termux:X11 already running."; return; fi
  export SDL_VIDEODRIVER="x11"
  export DISPLAY="${DISPLAY:-:0}"
  nohup termux-x11 "$DISPLAY" >/dev/null 2>&1 &
  sleep 1.5
}
stop_x_soft(){ pkill -TERM -f "termux-x11" || true; sleep 0.5; }
stop_x_hard(){ pkill -KILL -f "termux-x11" || true; }
force_stop_android_xapp(){ command -v am >/dev/null 2>&1 && am force-stop com.termux.x11 || true; }

cleanup(){
  # Called on normal exit, Ctrl-C, kill, or crash
  stop_x_soft
  stop_x_hard
  # This makes the Android app show “Not connected”
  force_stop_android_xapp
}
trap cleanup EXIT INT TERM

run_ui(){
  ensure_venv
  export SDL_VIDEODRIVER="x11"
  export DISPLAY="${DISPLAY:-:0}"
  start_x

  ts="$(date +'%Y%m%d_%H%M%S')"
  log="$LOG_DIR/ui_$ts.log"
  echo "Launching UI… (logs: $log)"
  # IMPORTANT: do NOT 'exec' here—so trap still runs afterwards
  "$PY" "$MAIN_PY" 2>&1 | tee -a "$log"
  exit_code=${PIPESTATUS[0]}

  # When the game exits (normal close or crash), trap will run and disconnect X11.
  exit "$exit_code"
}

run_cli(){
  ensure_venv
  export SDL_VIDEODRIVER="dummy"
  unset DISPLAY
  ts="$(date +'%Y%m%d_%H%M%S')"
  log="$LOG_DIR/cli_$ts.log"
  "$PY" "$MAIN_PY" --cli 2>&1 | tee -a "$log"
}

case "${1:-ui}" in
  ui) run_ui ;;
  cli) run_cli ;;
  stop) cleanup ;;            # manual “disconnect now”
  status) is_x_running && echo "X11: RUNNING" || echo "X11: STOPPED" ;;
  *) echo "Usage: $0 {ui|cli|stop|status}"; exit 2 ;;
esac
