import pytest
from starrealms.runner.controller import apply_command

def _base(name, defense, outpost):
    return {"name": name, "type": "base", "defense": defense, "outpost": bool(outpost)}

@pytest.mark.mechanics
def test_ai_destroys_outpost_before_face_damage(game, p1, p2):
    b_out = _base("Outpost A", 3, True)
    b_norm = _base("Normal B", 5, False)
    p2.bases[:] = [b_out, b_norm]

    p1.combat_pool = 3
    apply_command(game, "a", None, last_log_len=0, echo=False)

    names = [b["name"] for b in p2.bases]
    assert "Outpost A" not in names      # outpost removed
    assert "Normal B" in names           # normal base still there
    assert p1.combat_pool == 0           # spent
