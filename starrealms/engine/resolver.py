__all__ = [
    "apply_effect",
    "can_handle",
    "has_ally",
]

from typing import Callable, Dict, Any, List
from ..view import ui_common

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


def apply_effect(
    game: LegacyGame, player: LegacyPlayer, opponent: LegacyPlayer, spec: Effect
) -> None:
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
    if hasattr(game, "log"):
        game.log.append(f"{player.name} draws {n} card(s)")


@register("discard_then_draw")  # aka discard_up_to_then_draw
def _discard_then_draw(game, player, opponent, spec):
    max_discards = int(spec.get("amount") or 0)
    if max_discards <= 0:
        return
    actual = 0
    for _ in range(max_discards):
        if not player.hand:
            break
        card = player.hand.pop(0)
        player.discard_pile.append(card)
        actual += 1
        if hasattr(game, "log"):
            game.log.append(f"{player.name} discards {card['name']} (auto)")
    for _ in range(actual):
        player.draw_card()
    if actual and hasattr(game, "log"):
        game.log.append(f"{player.name} draws {actual} card(s) after discarding")


# --------- extras you’ll quickly benefit from ----------
@register("opponent_discards")
def _opponent_discards(game, player, opponent, spec):
    n = int(spec.get("amount") or 1)

    # Human opponent: prompt which card to discard (tests monkeypatch ui_input)
    if getattr(opponent, "human", False):
        for _ in range(n):
            if not getattr(opponent, "hand", None):
                break
            names = [c.get("name", "?") for c in opponent.hand]
            ui_common.ui_print("Choose a card to discard:", [f"{i+1}:{nm}" for i, nm in enumerate(names)])
            ans = (ui_common.ui_input("Pick hand index (1-based): ") or "").strip()
            try:
                idx = int(ans) - 1
            except Exception:
                idx = 0
            if idx < 0 or idx >= len(opponent.hand):
                idx = 0
            card = opponent.hand.pop(idx)
            opponent.discard_pile.append(card)
            if hasattr(game, "log"):
                game.log.append(f"{opponent.name} discards {card['name']}")
        return

    # AI / non-human: discard from the front
    for _ in range(n):
        if not getattr(opponent, "hand", None):
            break
        card = opponent.hand.pop(0)
        opponent.discard_pile.append(card)
        if hasattr(game, "log"):
            game.log.append(f"{opponent.name} discards {card['name']}")

@register("scrap_hand_or_discard")
def _scrap_one(game, player, opponent, spec):
    zone = (spec.get("args") or {}).get("zone")
    pile = (
        player.discard_pile
        if zone == "discard"
        else (player.hand if zone == "hand" else (player.discard_pile or player.hand))
    )
    if not pile:
        return
    idx = (spec.get("args") or {}).get("idx", 0)
    if not isinstance(idx, int) or not (0 <= idx < len(pile)):
        idx = 0
    card = pile.pop(idx)
    if hasattr(game, "scrap_heap"):
        game.scrap_heap.append(card)
    if hasattr(player, "scrap_heap"):
        player.scrap_heap.append(card)
    if hasattr(game, "log"):
        game.log.append(f"{player.name} scraps {card['name']}")


@register("destroy_base")
def _destroy_base(game, player, opponent, spec):
    if not opponent.bases:
        return
    outposts = [i for i, b in enumerate(opponent.bases) if b.get("outpost")]
    i = (spec.get("args") or {}).get("idx")
    if not isinstance(i, int) or not (0 <= i < len(opponent.bases)):
        i = outposts[0] if outposts else 0
    base = opponent.bases.pop(i)
    if hasattr(game, "scrap_heap"):
        game.scrap_heap.append(base)
    if hasattr(game, "log"):
        game.log.append(f"{player.name} destroys {base['name']}")


@register("destroy_target_trade_row")
def _destroy_trade_row(game, player, opponent, spec):
    row = game.trade_row
    if not row:
        return
    i = (spec.get("args") or {}).get("idx", 0)
    if not (0 <= i < len(row)):
        i = 0
    removed = row.pop(i)
    if hasattr(game, "scrap_heap"):
        game.scrap_heap.append(removed)
    if game.trade_deck:
        row.insert(i, game.trade_deck.pop())
    if hasattr(game, "log"):
        game.log.append(f"{player.name} scraps {removed['name']} from trade row")


@register("ally_any_faction")
def _ally_any(game, player, opponent, spec):
    setattr(player, "ally_wildcard_active", True)
    if hasattr(game, "log"):
        game.log.append(f"{player.name} counts as all factions this turn")


@register("topdeck_next_purchase")
def _topdeck_next_purchase(game, player, opponent, spec):
    setattr(player, "topdeck_next_purchase", True)
    if hasattr(game, "log"):
        game.log.append(f"{player.name} will top-deck next purchase")


def _card_provides_ally_wildcard(card) -> bool:
    """Infer Mech World–style wildcard from the card contents."""
    if not isinstance(card, dict):
        return False
    if card.get("name") == "Mech World":
        return True

    # abilities[] form
    for ab in card.get("abilities", []) or []:
        trig = ab.get("trigger", "")
        if isinstance(trig, str) and trig.startswith("continuous"):
            for eff in ab.get("effects", []) or []:
                if isinstance(eff, dict) and eff.get("type") == "ally_any_faction":
                    return True

    # legacy effects[] form
    for eff in card.get("effects", []) or []:
        if (
            isinstance(eff, dict)
            and eff.get("type") == "ally_any_faction"
            and eff.get("trigger") in (None, "continuous")
        ):
            return True
    return False


def _wildcard_active(game, player) -> bool:
    """True if ally-any-faction is active via dispatcher, per-turn flag, or inference from cards in play."""
    # per-turn effect flag (e.g., from an effect)
    if getattr(player, "ally_wildcard_active", False):
        return True

    # dispatcher-provided aura (e.g., Mech World registered on enter)
    if (
        hasattr(game, "dispatcher")
        and hasattr(game.dispatcher, "api")
        and hasattr(game.dispatcher.api, "ally_wildcard_active")
        and game.dispatcher.api.ally_wildcard_active(player.name)
    ):
        return True

    # fallback inference if dispatcher wasn’t notified
    for c in getattr(player, "bases", []):
        if _card_provides_ally_wildcard(c):
            return True
    for c in getattr(player, "in_play", []):
        if _card_provides_ally_wildcard(c):
            return True

    return False


def has_ally(
    game,
    player,
    faction: str | None = None,
    min_count: int = 1,
    scope: str = "this_turn",
) -> bool:
    """
    When called with only (game, player), return True iff an 'ally any faction' wildcard is active.
    When a faction is provided, return True if the wildcard is active OR the player meets the
    same-faction ally requirement (>= min_count in the given scope).
    """
    wildcard = _wildcard_active(game, player)
    if faction is None:
        return wildcard
    if wildcard:
        return True

    # Count same-faction cards
    if scope == "this_turn" and hasattr(game, "played_this_turn"):
        pool = list(
            getattr(game.played_this_turn, "get", lambda *_: [])(player.name, [])
        )
    else:
        pool = list(getattr(player, "in_play", [])) + list(getattr(player, "bases", []))

    def _matches_faction(c):
        f = c.get("faction")
        if isinstance(f, str):
            return f == faction
        if isinstance(f, (list, tuple, set)):
            return faction in f
        return False

    return sum(1 for c in pool if _matches_faction(c)) >= int(min_count)

    # --- Ally helper used by tests ---


def _card_provides_ally_wildcard(card) -> bool:
    """
    Infer Mech World–style wildcard from the card itself.
    Recognizes:
      - name == "Mech World"
      - abilities with trigger starting with 'continuous' that include {"type":"ally_any_faction"}
      - legacy effects[] entry {"type":"ally_any_faction"} with trigger None/'continuous'
    """
    if not isinstance(card, dict):
        return False
    if card.get("name") == "Mech World":
        return True

    # abilities[] form
    for ab in card.get("abilities", []) or []:
        trig = ab.get("trigger", "")
        if isinstance(trig, str) and trig.startswith("continuous"):
            for eff in ab.get("effects", []) or []:
                if isinstance(eff, dict) and eff.get("type") == "ally_any_faction":
                    return True

    # legacy effects[] form
    for eff in card.get("effects", []) or []:
        if (
            isinstance(eff, dict)
            and eff.get("type") == "ally_any_faction"
            and eff.get("trigger") in (None, "continuous")
        ):
            return True

    return False


def has_ally(player, faction: str) -> bool:
    """
    Test helper: True if the player effectively satisfies an ally condition for `faction`.
    Succeeds if:
      - An 'ally any faction' wildcard is active this turn, OR
      - The player has at least one card of `faction` in play/bases.
    Note: Signature intentionally omits `game` to match the tests.
    """
    # Per-turn effect flag from effects engine (e.g., ally_any_faction this turn)
    if getattr(player, "ally_wildcard_active", False):
        return True

    # Infer wildcard directly from cards in play (covers cases where dispatcher hooks aren’t wired)
    for zone in (getattr(player, "bases", []), getattr(player, "in_play", [])):
        for c in zone:
            if _card_provides_ally_wildcard(c):
                return True

    # Otherwise, check for any same-faction card in play/bases
    pool = list(getattr(player, "in_play", [])) + list(getattr(player, "bases", []))

    def _matches_faction(c):
        f = c.get("faction")
        if isinstance(f, str):
            return f == faction
        if isinstance(f, (list, tuple, set)):
            return faction in f
        return False

    return any(_matches_faction(c) for c in pool)
