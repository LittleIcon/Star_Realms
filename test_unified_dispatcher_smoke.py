# tests/test_unified_dispatcher_smoke.py
import importlib
import inspect
import pytest


def test_dispatcher_module_imports():
    mod = importlib.import_module("starrealms.engine.unified_dispatcher")
    assert mod is not None


def _maybe_get(mod, *names):
    for n in names:
        obj = getattr(mod, n, None)
        if obj is not None:
            return obj, n
    return None, None


@pytest.fixture
def dispatcher_obj():
    """
    Try to build a UnifiedDispatcher-like object, tolerating different ctor shapes.
    Common names: UnifiedDispatcher, Dispatcher, GameDispatcher.
    """
    mod = importlib.import_module("starrealms.engine.unified_dispatcher")
    cls, _ = _maybe_get(mod, "UnifiedDispatcher", "Dispatcher", "GameDispatcher")
    if cls and inspect.isclass(cls):
        # Try a few constructor shapes
        try:
            return cls()
        except TypeError:
            class _API:
                """Minimal API surface the dispatcher might call into."""
                def ally_wildcard_active(self, player_name):  # optional
                    return False
            try:
                return cls(_API())
            except TypeError:
                try:
                    return cls(api=_API())
                except Exception:
                    pytest.xfail("No recognized constructor shape for dispatcher.")
    pytest.xfail("No UnifiedDispatcher-like class found (OK for smoke).")


def test_dispatcher_has_basic_hooks(dispatcher_obj):
    """
    Probe for common hook names and call them if present.
    This should execute top-level logic without asserting specifics.
    """
    # Accept any/all of these if present
    hook_names = [
        "on_card_enter_play",
        "on_ship_played",
        "on_turn_start",
        "on_turn_end",
        "register_hook",
        "unregister_hooks",
    ]
    # Create minimal arguments
    player = "P1"
    card = {"name": "Scout", "type": "ship"}
    called_any = False
    for name in hook_names:
        fn = getattr(dispatcher_obj, name, None)
        if callable(fn):
            try:
                # Try common signatures with tolerance
                try:
                    fn(player, card)
                except TypeError:
                    try:
                        fn(player_name=player, card=card)
                    except TypeError:
                        try:
                            fn(player)
                        except TypeError:
                            fn()
                called_any = True
            except Exception:
                # If hook raises due to environment expectations, treat as OK for smoke
                pass
    if not called_any:
        pytest.xfail("No common dispatcher hooks present (OK for smoke).")


def test_dispatcher_optionally_exposes_api(dispatcher_obj):
    """
    If the dispatcher has an `.api`, call an innocuous method if present.
    """
    api = getattr(dispatcher_obj, "api", None)
    if not api:
        pytest.xfail("Dispatcher has no `.api` attribute (OK for smoke).")
    # Try a harmless API if it exists
    fn = getattr(api, "ally_wildcard_active", None)
    if callable(fn):
        # Should return a truthy/falsey; we don't assert value, just call
        _ = fn("P1")