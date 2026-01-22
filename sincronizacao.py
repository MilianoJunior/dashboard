from datetime import datetime, timedelta
import random
# import streamlit as st
from libs.models.db import Database

def atualizar_aparecida():
    db = Database()

    t0 = datetime(2025, 12, 1, 13, 28, 36)
    t1 = datetime(2025, 12, 11, 14, 9, 36)
    pote_final = 1055.75
    nivel_min, nivel_max = 403.95, 405.30

    # copiar os valores da tabela que sejam maiores do que a da

    # 1) linha base
    row = db.fetch_data(
        "SELECT * FROM cgh_aparecida WHERE data_hora = %s LIMIT 1",
        (t0,)
    )[0]
    print('row: ', row)
    pote_inicial = row["acumulador_energia"]
    total_min = int((t1 - t0).total_seconds() // 60)

    cols = [c for c in row.keys() if c != "id"]
    placeholders = ",".join(["%s"] * len(cols))
    sql = f"INSERT INTO cgh_aparecida ({','.join(cols)}) VALUES ({placeholders})"

    rng = random.Random(42)
    instante = t0

    for i in range(1, total_min + 1):
        instante += timedelta(minutes=1)
        frac = i / total_min

        energia = pote_inicial + frac * (pote_final - pote_inicial)

        base_nivel = nivel_min + (nivel_max - nivel_min) * 0.7
        jitter = (rng.random() - 0.5) * 0.4
        nivel = max(nivel_min, min(nivel_max, base_nivel + jitter))

        row["data_hora"] = instante
        row["acumulador_energia"] = round(energia, 3)
        row["nivel_montante"] = round(nivel, 3)

        valores = tuple(row[c] for c in cols)
        # db.execute_query(sql, valores)
        if i % 10 == 0:
            print(i,' data_hora: ', row["data_hora"], ' acumulador_energia: ', row["acumulador_energia"], ' nivel_montante: ', row["nivel_montante"])

if __name__ == "__main__":
    atualizar_aparecida()
