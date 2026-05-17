"""
ETL — Bloque 4B: Limpieza de ratings.csv (versión extendida)
Casa de la Cultura · Grupo 4 · Ingeniería de Datos

VERSIÓN B — usa copies_clean_extended.csv (conserva libros sin ISBN o sin año)

DIFERENCIA CON etl_ratings.py (versión A):
  - La versión A filtraba contra copies_clean.csv (51.300 copies).
  - Esta versión filtra contra copies_clean_extended.csv (55.315 copies).
  - Se recuperan los ratings de los libros sin ISBN que la versión A descartaba.
  - Pendiente decisión del equipo/cliente antes de usar esta versión.

Input:  data/raw/ratings.csv
        data/clean/copies_clean_extended.csv
Output: data/clean/ratings_clean_extended.csv
"""

import pandas as pd
import os

# ── Rutas ──────────────────────────────────────────────────────────────────────
RAW_RATINGS  = os.path.join("data", "raw", "ratings.csv")
CLEAN_COPIES = os.path.join("data", "clean", "copies_clean_extended.csv")
OUT_RATINGS  = os.path.join("data", "clean", "ratings_clean_extended.csv")

CHUNK_SIZE = 500_000

# ── Carga de copies válidas ────────────────────────────────────────────────────
print("Cargando copies_clean_extended.csv...")
copies_validas = set(pd.read_csv(CLEAN_COPIES, usecols=["copy_id"])["copy_id"])
print(f"  Copies válidas: {len(copies_validas)}")

# ── Procesado en chunks ────────────────────────────────────────────────────────
print(f"\nProcesando ratings.csv en chunks de {CHUNK_SIZE:,} filas...")

chunks_limpios = []
n_raw = 0
n_descartados = 0

for i, chunk in enumerate(pd.read_csv(RAW_RATINGS, chunksize=CHUNK_SIZE)):
    n_raw += len(chunk)
    mask = chunk["copy_id"].isin(copies_validas)
    descartados_chunk = (~mask).sum()
    n_descartados += descartados_chunk
    chunks_limpios.append(chunk[mask])
    print(f"  Chunk {i+1}: {len(chunk):,} filas, {descartados_chunk:,} descartadas")

# ── Concatenar y guardar ───────────────────────────────────────────────────────
print("\nConcatenando y guardando...")
df_clean = pd.concat(chunks_limpios, ignore_index=True)
df_clean.to_csv(OUT_RATINGS, index=False)

print(f"\n✓ ratings_clean_extended.csv guardado ({len(df_clean):,} filas) → {OUT_RATINGS}")

# ── Resumen final ──────────────────────────────────────────────────────────────
print("\n── Resumen ──────────────────────────────────────────────────────────────")
print(f"  Ratings originales:   {n_raw:,}")
print(f"  Descartados:          {n_descartados:,}")
print(f"  Ratings limpios:      {len(df_clean):,}")
print(f"  Porcentaje perdido:   {n_descartados/n_raw*100:.1f}%")
