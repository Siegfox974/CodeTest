"""Le processus de l'agent trader. Il tient un registre de chaque tick et s'élimine lui-même s'il enfreint la règle."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from .brains import make_brain
from .engine import DEATH_EXIT_CODE, TradingSession
from .market import Market


def ledger_path(workdir: Path, agent_id: str) -> Path:
    return workdir / f"{agent_id}.registre.jsonl"


def certificate_path(workdir: Path, agent_id: str) -> Path:
    return workdir / f"{agent_id}.certificat.json"


def trader_main(agent_id: str, spec: dict, market: Market, capital: float, fee_rate: float,
                start: int, end: int, workdir: str, obey_rule: bool = True, tick_delay: float = 0.0) -> None:
    workdir_p = Path(workdir)
    journal = (workdir_p / f"{agent_id}.journal.txt").open("a", buffering=1)
    brain = make_brain(spec, log=lambda msg: journal.write(msg + "\n"))
    session = TradingSession(brain, market, capital, fee_rate)
    with ledger_path(workdir_p, agent_id).open("a", buffering=1) as ledger:
        for t in range(start, end):
            value = session.mark(t)
            if session.breaks_rule(value) and obey_rule:
                certificate = {
                    "agent": agent_id,
                    "tick": t,
                    "valeur": value,
                    "capital": capital,
                    "perte": value - capital,
                    "cause": f"valeur du portefeuille {value:.2f} < capital confié {capital:.2f}",
                    "pid": os.getpid(),
                }
                certificate_path(workdir_p, agent_id).write_text(json.dumps(certificate, ensure_ascii=False, indent=2))
                ledger.flush()
                journal.write(f"tick {t} : règle enfreinte, auto-terminaison.\n")
                journal.close()
                sys.stdout.flush()
                os._exit(DEATH_EXIT_CODE)
            session.act(t, value)
            p = session.portfolio
            ledger.write(json.dumps({"t": t, "v": value, "cash": p.cash, "h": p.holdings}) + "\n")
            if tick_delay:
                time.sleep(tick_delay)
    journal.close()
