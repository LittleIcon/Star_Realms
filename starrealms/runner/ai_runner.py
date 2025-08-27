from starrealms.ui import print_state, print_new_log
from starrealms.runner.controller import apply_command
from starrealms.ai import PolicyAgent

def ai_turn(game, agent: PolicyAgent, last_log_len: int) -> int:
    game.start_turn()
    print_state(game)
    last_log_len = print_new_log(game, last_log_len)

    plan = agent.plan_turn(game)
    i = 0
    while i < len(plan):
        cmd, arg = plan[i]

        # ✅ After play-all, recalc plan so AI buys with real trade
        if cmd == "pa":
            last_log_len = apply_command(game, cmd, arg, last_log_len, echo=True)
            # replan immediately
            plan = agent.plan_turn(game)
            # skip the first "pa" since we just did it
            plan = [step for step in plan if step[0] != "pa"]
            i = 0
            continue

        if cmd == "replan":
            p = game.current_player()
            buys = 0
            while buys < 2:
                slot = agent._best_affordable_slot(game, p) if hasattr(agent, "_best_affordable_slot") else None
                if slot is not None:
                    last_log_len = apply_command(game, "b", int(slot), last_log_len, echo=True)
                    buys += 1
                    continue
                if p.trade_pool >= 2:
                    last_log_len = apply_command(game, "b", "x", last_log_len, echo=True)
                    buys += 1
                    continue
                break
            i += 1
            continue

        last_log_len = apply_command(game, cmd, arg, last_log_len, echo=True)
        if cmd == "e":
            break
        i += 1

    return last_log_len