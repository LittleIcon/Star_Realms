# tests/test_unified_dispatcher_smoke.py
import importlib

def test_unified_dispatcher_imports():
    mod = importlib.import_module("starrealms.engine.unified_dispatcher")
    # basic presence
    assert hasattr(mod, "__name__")