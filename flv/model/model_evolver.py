"""
ModelEvolver — rotina de avaliação contínua.

Ideia: avaliar previsões recentes vs preço observado (CEASA) e registrar acurácia.
Isso permite que o sistema "perceba" quando está errando.
"""

from __future__ import annotations

from datetime import datetime, timedelta


class ModelEvolver:
    def __init__(self):
        pass

    def avaliar_previsoes_recentes(self, dias: int = 10):
        """
        Avalia previsões já vencidas (target_date <= hoje) cruzando com preço observado.
        Registra MAPE em `flv_accuracy`.
        """
        from flv.db import get_conn, init_db

        try:
            init_db()
        except Exception:
            pass

        conn = get_conn()
        today = datetime.now().strftime("%Y-%m-%d")
        min_date = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")

        # Para cada previsão vencida, pega preço real (avg) do mesmo dia/terminal/cultura.
        # (Se existir) grava avaliação.
        sql = """
            SELECT
                p.id as prediction_id,
                p.culture_id,
                p.terminal,
                p.target_date,
                p.predicted_price,
                cp.price_avg as actual_price
            FROM flv_predictions p
            JOIN flv_ceasa_prices cp
              ON cp.culture_id = p.culture_id
             AND cp.terminal = p.terminal
             AND cp.price_date = p.target_date
            WHERE p.target_date BETWEEN ? AND ?
              AND p.predicted_price IS NOT NULL
              AND cp.price_avg IS NOT NULL
        """
        rows = conn.execute(sql, (min_date, today)).fetchall()

        inserted = 0
        mape_vals = []

        for r in rows:
            pred = float(r["predicted_price"])
            actual = float(r["actual_price"])
            if actual <= 0:
                continue
            mape = abs(pred - actual) / actual * 100.0
            mape_vals.append(mape)
            try:
                conn.execute(
                    "INSERT INTO flv_accuracy (prediction_id, actual_price, actual_date, mape_pct) VALUES (?,?,?,?)",
                    (r["prediction_id"], actual, r["target_date"], mape),
                )
                inserted += 1
            except Exception:
                # evita falhar o job por duplicidade/lock
                pass

        try:
            conn.commit()
        except Exception:
            pass

        avg_mape = (sum(mape_vals) / len(mape_vals)) if mape_vals else None
        if avg_mape is not None:
            print(f"[FLV-Evolver] Avaliou {inserted}/{len(rows)} previsões. MAPE médio: {avg_mape:.2f}%")
        else:
            # Evita caracteres não-ASCII (alguns ambientes Windows usam cp1252 no stdout).
            print(f"[FLV-Evolver] Sem pares previsao-real para avaliar nos ultimos {dias} dias.")

        return {"avaliadas": inserted, "total_pares": len(rows), "mape_medio": avg_mape}

