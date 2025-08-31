def print_state(state):
    p1 = state.players["P1"]
    p2 = state.players["P2"]
    print(
        f"P1 {p1.name}: 💚{p1.authority} 🟡{p1.trade} 🔺{p1.combat} | Hand:{len(p1.hand)}"
    )
    print(
        f"P2 {p2.name}: 💚{p2.authority} 🟡{p2.trade} 🔺{p2.combat} | Hand:{len(p2.hand)}"
    )
    row = ", ".join(c.get("name", "?") for c in state.trade_row if c)
    print(f"Row: [{row}]")
