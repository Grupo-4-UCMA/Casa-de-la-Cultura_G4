"""
ETL — Bloque 3: Limpieza de user_info.csv
Casa de la Cultura · Grupo 4 · Ingeniería de Datos

Decisiones de limpieza aplicadas (ver auditoría 01_auditoria_calidad_datos.ipynb):
  - Se elimina la columna 'sexo' (decisión cliente + GDPR).
  - Los 52.924 usuarios que aparecen en ratings pero no en user_info se cargan
    en la BD solo con su user_id, sin comment ni birth_date. El cliente confirmó
    en el foro que el acceso se hace solo con el identificador.

Input:  data/raw/user_info.csv
        data/raw/ratings.csv      (solo se lee la columna user_id)
Output: data/clean/users_clean.csv
"""

import pandas as pd
import os

# ── Rutas ──────────────────────────────────────────────────────────────────────
RAW_USERS   = os.path.join("data", "raw", "user_info.csv")
RAW_RATINGS = os.path.join("data", "raw", "ratings.csv")
OUT_USERS   = os.path.join("data", "clean", "users_clean.csv")

# ── Carga de usuarios base ─────────────────────────────────────────────────────
print("Cargando user_info.csv...")
df = pd.read_csv(RAW_USERS)
n_raw = len(df)
print(f"  Filas cargadas: {n_raw}")

# ── Eliminar columna sexo ──────────────────────────────────────────────────────
# Decisión del cliente y obligación GDPR: el sexo no aporta valor al sistema
# de recomendación y no debe persistirse en la nueva BD.
df = df.drop(columns=["sexo"])
print(f"  Columna 'sexo' eliminada")

# ── Recuperar usuarios fantasma de ratings ────────────────────────────────────
# Hay 52.924 user_ids en ratings que no tienen ficha en user_info.
# El cliente confirmó que el acceso es solo con el identificador,
# así que los cargamos en la BD con user_id únicamente.
print("\nCargando user_ids de ratings...")
ratings_users = pd.read_csv(RAW_RATINGS, usecols=["user_id"])["user_id"].unique()
usuarios_conocidos = set(df["user_id"])
fantasmas = [uid for uid in ratings_users if uid not in usuarios_conocidos]
print(f"  user_ids únicos en ratings:      {len(ratings_users)}")
print(f"  Usuarios con ficha completa:     {n_raw}")
print(f"  Usuarios sin ficha (fantasmas):  {len(fantasmas)}")

# Añadimos los fantasmas con solo user_id, el resto de columnas quedan a NaN
df_fantasmas = pd.DataFrame({
    "user_id":        fantasmas,
    "comentario":     None,
    "fecha_nacimiento": None,
})
df = pd.concat([df, df_fantasmas], ignore_index=True)
print(f"\n  Total usuarios tras merge: {len(df)}")

# ── Guardado ───────────────────────────────────────────────────────────────────
df.to_csv(OUT_USERS, index=False)
print(f"\n✓ users_clean.csv guardado ({len(df)} filas) → {OUT_USERS}")

# ── Resumen final ──────────────────────────────────────────────────────────────
print("\n── Resumen ──────────────────────────────────────────────────────────────")
print(f"  Usuarios con ficha completa:  {n_raw}")
print(f"  Usuarios fantasma añadidos:   {len(fantasmas)}")
print(f"  Total usuarios en BD:         {len(df)}")
print(f"  Columna 'sexo' eliminada:     sí")
