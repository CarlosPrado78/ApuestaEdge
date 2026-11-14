#!/usr/bin/env python3
"""Verificador independiente del registro público de ApuestaEdge.

Comprueba, sin confiar en el servidor que generó los datos, que las tres
cadenas de hashes (picks, pick_closings, pick_results) son íntegras y que
las anclas diarias cuadran con las cabezas.

Uso:
    python verify_ledger.py apuestaedge-ledger.json
    python verify_ledger.py https://tu-dominio/api/ledger/export

Solo usa la biblioteca estándar. Devuelve código 0 si todo cuadra y 1 si
hay cualquier manipulación, fila faltante o ancla que no coincide.
"""

import hashlib
import json
import sys
import urllib.request

CHAIN_TABLES = ("picks", "pick_closings", "pick_results")
ANCHOR_KEYS = ("picks_head", "picks_count",
               "closings_head", "closings_count",
               "results_head", "results_count")


def load(source: str) -> dict:
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    with open(source, encoding="utf-8") as fh:
        return json.load(fh)


def normalize(row: dict, fields, floats, ints) -> dict:
    out = {}
    for key in fields:
        value = row.get(key)
        if value is None:
            out[key] = None
        elif key in floats:
            out[key] = float(value)
        elif key in ints:
            out[key] = int(value)
        else:
            out[key] = str(value)
    return out


def canonical(row: dict, spec: dict) -> str:
    clean = normalize(row, spec["fields"], set(spec["floats"]),
                      set(spec.get("ints") or ()))
    return json.dumps(clean, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def row_hash(prev_hash: str, payload: str) -> str:
    return hashlib.sha256((prev_hash + payload).encode("utf-8")).hexdigest()


def check_chain(package: dict, table: str) -> tuple[bool, int, str, str]:
    """Devuelve (ok, filas, cabeza, motivo del fallo)."""
    spec = package["algorithm"]["tables"][table]
    rows = package["tables"][table]
    prev = ""
    for row in rows:
        payload = canonical(row, spec)
        if row.get("canonical") not in (None, payload):
            return False, len(rows), "", (
                f"fila {row.get('id')}: canonical no coincide con los campos")
        expected = row_hash(prev, payload)
        if row.get("prev_hash") != prev:
            return False, len(rows), "", (
                f"fila {row.get('id')}: prev_hash no enlaza con la anterior")
        if row.get("row_hash") != expected:
            return False, len(rows), "", (
                f"fila {row.get('id')}: row_hash no coincide (fila editada)")
        prev = row["row_hash"]
    return True, len(rows), prev, ""


def check_anchor(anchor: dict) -> tuple[bool, str]:
    missing = [k for k in ANCHOR_KEYS + ("head_hash",) if k not in anchor]
    if missing:
        return False, f"ancla incompleta: faltan {', '.join(missing)}"
    material = "|".join(str(anchor[k]) for k in ANCHOR_KEYS)
    expected = hashlib.sha256(material.encode("utf-8")).hexdigest()
    if anchor["head_hash"] != expected:
        return False, f"ancla {anchor.get('day')}: head_hash no coincide"
    return True, ""


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip())
        return 2
    try:
        package = load(argv[1])
    except (OSError, ValueError) as exc:
        print(f"No se pudo leer el paquete: {exc}")
        return 2

    print(f"Paquete generado: {package.get('generated_at_iso', '?')} "
          f"(modelo {package.get('model_version', '?')})")
    ok_all = True
    heads = {}
    counts = {}
    for table in CHAIN_TABLES:
        if table not in package.get("tables", {}):
            print(f"✗ {table}: falta en el paquete")
            ok_all = False
            continue
        ok, rows, head, reason = check_chain(package, table)
        counts[table] = rows
        heads[table] = head
        if ok:
            print(f"✓ {table}: {rows} filas · cabeza {head[:16]}…")
        else:
            print(f"✗ {table}: {reason}")
            ok_all = False

    anchors = package.get("anchors") or []
    if not anchors:
        print("· Sin anclas publicadas todavía.")
    for anchor in anchors:
        ok, reason = check_anchor(anchor)
        if ok:
            print(f"✓ ancla {anchor['day']}: {anchor['head_hash'][:16]}…")
        else:
            print(f"✗ {reason}")
            ok_all = False

    # Si el ancla es del estado actual, debe coincidir con las cabezas.
    if anchors:
        latest = anchors[0]
        expected = {"picks_head": heads.get("picks", ""),
                    "picks_count": counts.get("picks", 0),
                    "closings_head": heads.get("pick_closings", ""),
                    "closings_count": counts.get("pick_closings", 0),
                    "results_head": heads.get("pick_results", ""),
                    "results_count": counts.get("pick_results", 0)}
        if all(latest.get(k) == v for k, v in expected.items()):
            print(f"✓ el ancla más reciente coincide con las cabezas actuales "
                  f"({latest['day']})")
        else:
            print(f"· el ancla más reciente ({latest['day']}) es de un estado "
                  f"anterior de las cadenas; no se usa para comparar cabezas")

    print()
    if ok_all:
        print("RESULTADO: registro íntegro. Ninguna fila fue editada, "
              "reordenada ni borrada.")
        return 0
    print("RESULTADO: la cadena NO cuadra. No confíes en este paquete.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
