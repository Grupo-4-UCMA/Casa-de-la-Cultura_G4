"""
ETL — Bloque 4A: Limpieza de ratings.csv (versión estricta)
Casa de la Cultura · Grupo 4 · Ingeniería de Datos

VERSIÓN A — usa books_clean.csv (descarta libros sin ISBN o sin año)

Decisiones de limpieza aplicadas (ver auditoría 01_auditoria_calidad_datos.ipynb):
  - Se filtran ratings cuya copy no existe en copies_clean.csv
    (cubre tanto huérfanos reales como copies de libros descartados).
  - Los ratings de usuarios sin ficha se conservan — el cliente confirmó
    que el acceso es solo con el identificador.
  - ratings.csv es grande (~6M filas), se procesa en chunks para no
    saturar la memoria.

Input:  data/raw/ratings.csv
        data/clean/copies_clean.csv
Output: data/clean/ratings_clean.csv
"""

import pandas as pd
import os

# ── Rutas ──────────────────────────────────────────────────────────────────────
RAW_RATINGS  = os.path.join("data", "raw", "ratings.csv")
CLEAN_COPIES = os.path.join("data", "clean", "copies_clean.csv")
OUT_RATINGS  = os.path.join("data", "clean", "ratings_clean.csv")

CHUNK_SIZE = 500_000

# ── Carga de copies válidas ────────────────────────────────────────────────────
print("Cargando copies_clean.csv...")
copies_validas = set(pd.read_csv(CLEAN_COPIES, usecols=["copy_id"])["copy_id"])
print(f"  Copies válidas: {len(copies_validas)}")

# ── Procesado en chunks ────────────────────────────────────────────────────────
# ratings.csv tiene ~6M filas. Se procesa en bloques de 500k para no
# saturar la memoria del equipo.
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

print(f"\n✓ ratings_clean.csv guardado ({len(df_clean):,} filas) → {OUT_RATINGS}")

# ── Resumen final ──────────────────────────────────────────────────────────────
print("\n── Resumen ──────────────────────────────────────────────────────────────")
print(f"  Ratings originales:   {n_raw:,}")
print(f"  Descartados:          {n_descartados:,}")
print(f"  Ratings limpios:      {len(df_clean):,}")
print(f"  Porcentaje perdido:   {n_descartados/n_raw*100:.1f}%")
