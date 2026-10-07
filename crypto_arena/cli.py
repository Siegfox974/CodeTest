"""Ligne de commande : `python -m crypto_arena run` lance l'expérience, `fetch` télécharge des prix réels."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from .brains import DEFAULT_MODEL
from .market import fetch_binance, generate_synthetic, load_csv
from .supervisor import Supervisor


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="crypto_arena", description="Arène darwinienne d'agents traders crypto (simulation, argent fictif).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="lancer l'expérience")
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--ticks", type=int, default=4000, help="nombre d'heures du marché synthétique")
    run.add_argument("--csv", help="utiliser un historique réel (format de `fetch`) au lieu du marché synthétique")
    run.add_argument("--capital", type=float, default=1000.0)
    run.add_argument("--fee", type=float, default=0.001, help="frais par ordre (0.001 = 0,1 %%)")
    run.add_argument("--brain", choices=["genome", "claude"], default="genome")
    run.add_argument("--first-tick", type=int, default=600, help="naissance du premier agent (l'historique avant sert à le sélectionner)")
    run.add_argument("--max-generations", type=int, default=30)
    run.add_argument("--population", type=int, default=24, help="candidats évalués pour chaque succession")
    run.add_argument("--window", type=int, default=300, help="taille des fenêtres de backtest")
    run.add_argument("--tick-delay", type=float, default=0.0, help="pause entre deux ticks (pour regarder en direct)")
    run.add_argument("--model", default=DEFAULT_MODEL)
    run.add_argument("--decision-every", type=int, default=24, help="mode claude : heures entre deux décisions")
    run.add_argument("--out", default="runs")

    fetch = sub.add_parser("fetch", help="télécharger des clôtures Binance publiques en CSV")
    fetch.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT,DOGEUSDT")
    fetch.add_argument("--interval", default="1h")
    fetch.add_argument("--limit", type=int, default=1000)
    fetch.add_argument("--out", default="data/binance.csv")

    args = parser.parse_args(argv)
    if args.cmd == "fetch":
        market = fetch_binance(args.symbols.split(","), args.interval, args.limit)
        market.to_csv(args.out)
        print(f"{len(market)} ticks enregistrés dans {args.out}")
        return

    if args.brain == "claude":
        try:
            import anthropic  # noqa: F401
        except ImportError:
            parser.error("le mode claude nécessite le SDK : pip install anthropic")
    market = load_csv(args.csv) if args.csv else generate_synthetic(args.ticks, args.seed)
    workdir = Path(args.out) / time.strftime("%Y%m%d-%H%M%S")
    supervisor = Supervisor(
        market=market, workdir=workdir, capital=args.capital, fee_rate=args.fee, brain_kind=args.brain,
        first_tick=args.first_tick, max_generations=args.max_generations, population=args.population,
        window=args.window, tick_delay=args.tick_delay, seed=args.seed, model=args.model,
        decision_every=args.decision_every,
        hang_timeout=600.0 if args.brain == "claude" else 30.0,
    )
    lineage = supervisor.run()
    print_summary(lineage, args.capital)
    print(f"\nRegistres, certificats et rapport : {workdir}")


def print_summary(lineage, capital: float) -> None:
    print("\n=== Lignée ===")
    print(f"{'agent':<10} {'naissance':>9} {'fin':>6} {'vie (h)':>8} {'valeur':>10} {'issue':<10} {'bat son prédécesseur':>20}")
    for r in lineage:
        beat = {True: "oui", False: "non", None: "-"}[r.beat_predecessor]
        print(f"{r.agent_id:<10} {r.born_tick:>9} {r.end_tick:>6} {r.ticks_lived:>8} "
              f"{r.final_value:>10.2f} {r.outcome:<10} {beat:>20}")
    survivors = [r for r in lineage if r.outcome == "survivant"]
    longest = max(lineage, key=lambda r: r.ticks_lived)
    print(f"\nPlus longue vie : {longest.agent_id} ({longest.ticks_lived} h).")
    if survivors:
        s = survivors[0]
        print(f"Survivant final : {s.agent_id}, {s.final_value:.2f} USDT ({(s.final_value / capital - 1) * 100:+.2f} %).")
    else:
        print("Aucun agent n'a survécu jusqu'à la fin des données.")
