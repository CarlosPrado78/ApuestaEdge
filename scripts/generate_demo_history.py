"""Genera data/history.json: historial de demostración del track record.

Uso:  python scripts/generate_demo_history.py  (desde apuesta_edge/)

Los picks se simulan con una tasa de acierto coherente con el edge
(p_win ≈ 1/cuota · (1 + edge·1.2)), es decir, el histórico refleja una
ventaja real modesta y no un 90% de aciertos irreal.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "history.json"

SPORTS = ["soccer", "basketball", "tennis", "americanfootball",
          "boxing", "baseball", "formula1", "motogp", "horseracing"]
MATCHES = {
    "soccer": ["Real Madrid vs Barcelona", "Arsenal vs Chelsea",
               "Manchester City vs Liverpool", "América vs Guadalajara",
               "Tigres vs Cruz Azul"],
    "basketball": ["Lakers vs Celtics", "Nuggets vs Warriors",
                   "Bucks vs Suns", "Heat vs Knicks"],
    "tennis": ["Alcaraz vs Sinner", "Swiatek vs Sabalenka",
               "Djokovic vs Medvedev"],
    "americanfootball": ["Chiefs vs Bills", "Eagles vs Cowboys",
                         "49ers vs Packers", "Lions vs Dolphins"],
    "boxing": ["Canelo vs Benavidez", "Usyk vs Fury"],
    "baseball": ["Dodgers vs Yankees", "Braves vs Astros", "Mets vs Phillies"],
    "formula1": ["GP de São Paulo"],
    "motogp": ["GP de Valencia"],
    "horseracing": ["Gran Premio de Otoño"],
}
SELECTIONS = {"soccer": ["home", "draw", "away"],
              "basketball": ["home", "away"],
              "tennis": ["home", "away"],
              "americanfootball": ["home", "away"],
              "boxing": ["home", "away"],
              "baseball": ["home", "away"],
              # Outright: la selección es el nombre del participante.
              "formula1": ["Verstappen", "Norris", "Piastri", "Leclerc",
                           "Russell"],
              "motogp": ["Bagnaia", "Martín", "Márquez", "Acosta"],
              "horseracing": ["Estrella Veloz", "Rey del Pacífico",
                              "Tornado Negro", "Duquesa Azul"]}


def main() -> None:
    rng = random.Random(20261110)
    rows = []
    ts = 1_700_000_000.0
    for i in range(96):
        # Distribución equilibrada entre los deportes (96 = 10-11 c/u).
        sport = SPORTS[i % len(SPORTS)]
        odds = round(rng.uniform(1.55, 3.60), 2)
        edge = round(rng.uniform(0.03, 0.11), 4)
        p_win = min((1.0 / odds) * (1.0 + edge * 1.8), 0.90)
        won = 1 if rng.random() < p_win else 0
        stake = round(rng.uniform(0.5, 2.5), 2)
        profit = round(stake * (odds - 1.0), 3) if won else -stake
        rows.append({
            "ts": ts,
            "sport": sport,
            "match": rng.choice(MATCHES[sport]),
            "selection": rng.choice(SELECTIONS[sport]),
            "odds": odds,
            "edge": edge,
            "stake_pct": stake,
            "won": won,
            "profit": profit,
            "clv_pct": round(rng.uniform(-2.0, 9.0), 2),
        })
        ts += rng.uniform(3600, 7200)
    OUT.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"{len(rows)} picks escritos en {OUT}")


if __name__ == "__main__":
    main()
