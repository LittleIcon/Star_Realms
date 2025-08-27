# starrealms/ai_storage.py
"""
Persistence and data defaults for Star Realms AI.

Responsibilities:
- Decide where the learning data (weights, logs) live
- Load / save weights
- Provide default weights (data)
- Append simple training logs

Configuration:
- Env var STARREALMS_DATA_DIR can override the default data directory.
- Default data dir: ~/.starrealms
- Files:
    weights.json
    training_log.csv
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, Tuple, Optional
from datetime import datetime

# ---------- Data directory & paths ----------
def _default_data_dir() -> Path:
    env = os.environ.get("STARREALMS_DATA_DIR")
    if env:
        return Path(env).expanduser()
    # Fallback to a simple dot-dir in the home folder
    return Path.home() / ".starrealms"

def get_paths() -> Tuple[Path, Path]:
    data_dir = _default_data_dir()
    weights_path = data_dir / "weights.json"
    log_path = data_dir / "training_log.csv"
    return weights_path, log_path

def ensure_dirs() -> None:
    weights_path, log_path = get_paths()
    weights_path.parent.mkdir(parents=True, exist_ok=True)

# ---------- Default weights (learning "data") ----------
DEFAULT_WEIGHTS: Dict[str, float] = {
    "trade": 1.0,
    "combat": 1.0,
    "draw": 2.0,
    "authority": 0.4,
    "discard": 1.2,          # making opponent discard is nice
    "scrap_hand_or_discard": 1.0,
    "scrap_multiple": 1.6,   # deck-thinning is strong
    "destroy_base": 1.5,
    "destroy_target_trade_row": 0.5,
    "ally_any_faction": 0.6, # Mech World synergy
    "per_ship_combat": 0.8,
    "topdeck_next_purchase": 1.2,
    "copy_target_ship": 1.0,
    "base_defense": 0.15,    # extra score per defense point
    "outpost_bonus": 0.6,    # outposts are sticky
    "cost_penalty": 0.05,    # subtract cost * penalty to bias for efficiency
}

# ---------- Load / Save ----------
def load_weights(path: Optional[str] = None) -> Dict[str, float]:
    ensure_dirs()
    weights_path, _ = get_paths()
    if path:
        weights_path = Path(path).expanduser()
        weights_path.parent.mkdir(parents=True, exist_ok=True)

    if weights_path.exists():
        with weights_path.open("r") as f:
            data = json.load(f)
        w = DEFAULT_WEIGHTS.copy()
        w.update(data)
        return w
    return DEFAULT_WEIGHTS.copy()

def save_weights(weights: Dict[str, float], path: Optional[str] = None) -> None:
    ensure_dirs()
    weights_path, _ = get_paths()
    if path:
        weights_path = Path(path).expanduser()
        weights_path.parent.mkdir(parents=True, exist_ok=True)

    with weights_path.open("w") as f:
        json.dump(weights, f, indent=2, sort_keys=True)

# ---------- Training log (optional) ----------
def append_training_log(iteration: int, candidate_winrate: float, kept: bool) -> None:
    ensure_dirs()
    _, log_path = get_paths()
    new_file = not log_path.exists()
    with log_path.open("a") as f:
        if new_file:
            f.write("timestamp,iteration,winrate,kept\n")
        f.write(f"{datetime.utcnow().isoformat()},{iteration},{candidate_winrate:.4f},{int(kept)}\n")