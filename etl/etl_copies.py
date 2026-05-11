"""
ETL — Bloque 2: Limpieza de copies.csv
Casa de la Cultura · Grupo 4 · Ingeniería de Datos

Decisiones de limpieza aplicadas (ver auditoría 01_auditoria_calidad_datos.ipynb):
  - El archivo está limpio: sin nulos, sin duplicados, sin valores fuera de rango.
  - Se filtran 2 ejemplares huérfanos (book_id sin correspondencia en books_clean).

Input:  data/raw/copies.csv
        data/clean/books_clean.csv  (necesario para comprobar integridad referencial)
Output: data/clean/copies_clean.csv
"""

import pandas as pd
import os

# ── Rutas ──────────────────────────────────────────────────────────────────────
RAW_COPIES  = os.path.join("data", "raw", "copies(ejemplares).csv")
CLEAN_BOOKS = os.path.join("data", "clean", "books_clean.csv")
OUT_COPIES  = os.path.join("data", "clean", "copies_clean.csv")

# ── Carga ──────────────────────────────────────────────────────────────────────
print("Cargando copies.csv...")
df = pd.read_csv(RAW_COPIES)
n_raw = len(df)
print(f"  Filas cargadas: {n_raw}")

# ── Filtrado de huérfanos ──────────────────────────────────────────────────────
# Se eliminan los 2 ejemplares cuyo book_id no existe en books_clean.
# Sin libro asociado no tienen utilidad en el sistema.
books_validos = pd.read_csv(CLEAN_BOOKS, usecols=["book_id"])["book_id"]
mask_validos = df["book_id"].isin(books_validos)
huerfanos = (~mask_validos).sum()
df = df[mask_validos].copy()
print(f"  Huérfanos descartados (book_id sin libro válido): {huerfanos}")
print(f"  Quedan tras filtrado: {len(df)}")

# ── Guardado ───────────────────────────────────────────────────────────────────
df.to_csv(OUT_COPIES, index=False)
print(f"\n✓ copies_clean.csv guardado ({len(df)} filas) → {OUT_COPIES}")

# ── Resumen final ──────────────────────────────────────────────────────────────
print("\n── Resumen ──────────────────────────────────────────────────────────────")
print(f"  Filas originales:   {n_raw}")
print(f"  Huérfanos:          {huerfanos}")
print(f"  Ejemplares limpios: {len(df)}")


# Se eliminan los ejemplares cuyo book_id no existe en books_clean.
# Origen de los 4.027 huérfanos:
#   - 4.015 copies de los 718 libros descartados en bloque 1 (sin ISBN o sin año)
#   - 12 copies con book_id que nunca existió en books.csv
# Comportamiento esperado, integridad referencial correcta.
