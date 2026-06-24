"""Seed de polos hortifrutigranjeiros da América do Sul para o Bio-Command.

A base é curada em nível de polo/município-região. Não representa cadastro
exaustivo de fazendas/propriedades e deve ser substituída por séries oficiais
quando houver integração nacional por país.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "nia_flv.db"
DATA_PATH = Path(__file__).with_name("south_america_hf_poles.json")


def seed_south_america_hf_poles(db_path: str | os.PathLike = DB_PATH) -> tuple[int, int]:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    inserted = updated = 0
    for rec in records:
        name = f"Polo HF SA — {rec['name']}"
        products = [p.upper().replace(" ", "_") for p in rec.get("products", [])]
        volume = {p.upper().replace(" ", "_"): f"{int(rec.get('flvTons', 0))} ton/ano estimado-polo" for p in rec.get("products", [])[:3]}
        cur.execute("SELECT id FROM flv_producers WHERE name = ?", (name,))
        row = cur.fetchone()
        data = (
            rec["name"], rec["country"], rec["lat"], rec["lon"],
            json.dumps(products, ensure_ascii=False),
            json.dumps(volume, ensure_ascii=False),
            "Bio-Command/curated_south_america_hf_2026",
        )
        if row:
            cur.execute(
                """
                UPDATE flv_producers
                   SET city=?, state_uf=?, lat=?, lon=?, products=?, production_volume=?,
                       market_channel=?, status='ativo', updated_at=datetime('now')
                 WHERE id=?
                """,
                (*data, row[0]),
            )
            updated += 1
        else:
            cur.execute(
                """
                INSERT INTO flv_producers
                (name, city, state_uf, lat, lon, products, production_volume, market_channel, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ativo')
                """,
                (name, *data),
            )
            inserted += 1
    conn.commit()
    conn.close()
    return inserted, updated


if __name__ == "__main__":
    ins, upd = seed_south_america_hf_poles()
    print(f"✓ Polos HF América do Sul inseridos: {ins}")
    print(f"✓ Polos HF América do Sul atualizados: {upd}")
