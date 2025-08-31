from typing import Callable, Dict, Any, List

LegacyGame = Any
LegacyPlayer = Any
Effect = Dict[str, Any]
EffectFn = Callable[[LegacyGame, LegacyPlayer, LegacyPlayer, Effect], None]

_REG: Dict[str, EffectFn] = {}

def register(kind: str):
    def deco(fn: EffectFn):
        _REG[kind] = fn
        return fn
    return deco

def can_handle(kind: str) -> bool:
    return kind in _REG

def apply_effect(game: LegacyGame, player: LegacyPlayer, opponent: LegacyPlayer, spec: Effect) -> None:
    fn = _REG.get(spec.get("type"))
    if not fn:
        raise KeyError(f"resolver has no handler for kind={spec.get('type')}")
    fn(game, player, opponent, spec)

# ---------------- core effects (pure, no input/print) ----------------

@register("trade")
def _trade(game, player, opponent, spec):
    amt = int(spec.get("amount") or 0)
    player.trade_pool += amt
    if hasattr(game, "log"):
        game.log.append(f"{player.name} gains +{amt} trade")

@register("combat")
def _combat(game, player, opponent, spec):
    amt = int(spec.get("amount") or 0)
    player.combat_pool += amt
    if hasattr(game, "log"):
        game.log.append(f"{player.name} gains +{amt} combat")

@register("authority")
def _authority(game, player, opponent, spec):
    amt = int(spec.get("amount") or 0)
    player.authority += amt
    if hasattr(game, "log"):
        game.log.append(
            f"{player.name} {'gains' if amt >= 0 else 'loses'} {abs(amt)} authority"
        )

@register("draw")
def _draw(game, player, opponent, spec):
    n = int(spec.get("amount") or 1)
    for _ in range(n):
        player.draw_card()
    if hasattr(game, "log"): game.log.append(f"{player.name} draws {n} card(s)")

@register("discard_then_draw")  # aka discard_up_to_then_draw
def _discard_then_draw(game, player, opponent, spec):
    max_discards = int(spec.get("amount") or 0)
    if max_discards <= 0:
        return
    actual = 0
    for _ in range(max_discards):
        if not player.hand: break
        card = player.hand.pop(0)
        player.discard_pile.append(card)
        actual += 1
        if hasattr(game, "log"): game.log.append(f"{player.name} discards {card['name']} (auto)")
    for _ in range(actual):
        player.draw_card()
    if actual and hasattr(game, "log"):
        game.log.append(f"{player.name} draws {actual} card(s) after discarding")

# --------- extras you’ll quickly benefit from ----------
@register("opponent_discards")
def _opponent_discards(game, player, opponent, spec):
    n = int(spec.get("amount") or 1)
    for _ in range(n):
        if not opponent.hand: break
        card = opponent.hand.pop(0)
        opponent.discard_pile.append(card)
        if hasattr(game, "log"): game.log.append(f"{opponent.name} discards {card['name']}")

@register("scrap_hand_or_discard")
def _scrap_one(game, player, opponent, spec):
    zone = (spec.get("args") or {}).get("zone")
    pile = player.discard_pile if zone == "discard" else (player.hand if zone == "hand" else (player.discard_pile or player.hand))
    if not pile: return
    idx = (spec.get("args") or {}).get("idx", 0)
    if not isinstance(idx, int) or not (0 <= idx < len(pile)): idx = 0
    card = pile.pop(idx)
    if hasattr(game, "scrap_heap"): game.scrap_heap.append(card)
    if hasattr(player, "scrap_heap"): player.scrap_heap.append(card)
    if hasattr(game, "log"): game.log.append(f"{player.name} scraps {card['name']}")

@register("destroy_base")
def _destroy_base(game, player, opponent, spec):
    if not opponent.bases: return
    outposts = [i for i,b in enumerate(opponent.bases) if b.get("outpost")]
    i = (spec.get("args") or {}).get("idx")
    if not isinstance(i, int) or not (0 <= i < len(opponent.bases)):
        i = outposts[0] if outposts else 0
    base = opponent.bases.pop(i)
    if hasattr(game, "scrap_heap"): game.scrap_heap.append(base)
    if hasattr(game, "log"): game.log.append(f"{player.name} destroys {base['name']}")

@register("destroy_target_trade_row")
def _destroy_trade_row(game, player, opponent, spec):
    row = game.trade_row
    if not row: return
    i = (spec.get("args") or {}).get("idx", 0)
    if not (0 <= i < len(row)): i = 0
    removed = row.pop(i)
    if hasattr(game, "scrap_heap"): game.scrap_heap.append(removed)
    if game.trade_deck: row.insert(i, game.trade_deck.pop())
    if hasattr(game, "log"): game.log.append(f"{player.name} scraps {removed['name']} from trade row")

@register("ally_any_faction")
def _ally_any(game, player, opponent, spec):
    setattr(player, "ally_wildcard_active", True)
    if hasattr(game, "log"): game.log.append(f"{player.name} counts as all factions this turn")

@register("topdeck_next_purchase")
def _topdeck_next_purchase(game, player, opponent, spec):
    setattr(player, "topdeck_next_purchase", True)
    if hasattr(game, "log"): game.log.append(f"{player.name} will top-deck next purchase")
