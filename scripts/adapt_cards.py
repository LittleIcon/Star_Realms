# scripts/adapt_cards.py
import sys
from engine.card_adapter import adapt_file

if __name__ == "__main__":
    in_path  = sys.argv[1] if len(sys.argv) > 1 else "cards.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "cards_unified.json"
    adapt_file(in_path, out_path)


