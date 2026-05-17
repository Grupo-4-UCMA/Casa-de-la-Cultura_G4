"""
ETL — Bloque 2B: Limpieza de copies.csv (versión extendida)
Casa de la Cultura · Grupo 4 · Ingeniería de Datos

DIFERENCIA CON etl_copies.py (versión A):
  - La versión A descartaba 4.027 copies (4.015 de libros sin ISBN/año + 12 huérfanas reales).
  - Esta versión (B) solo descarta las 12 copies con book_id que nunca existió en books.csv.
  - Las 4.015 copies de libros sin ISBN se recuperan al conservar esos libros.
  - Pendiente decisión del equipo/cliente antes de usar esta versión.

Input:  data/raw/copies(ejemplares).csv
        data/clean/books_clean_extended.csv
Output: data/clean/copies_clean_extended.csv
"""

import pandas as pd
import os

# ── Rutas ──────────────────────────────────────────────────────────────────────
RAW_COPIES  = os.path.join("data", "raw", "copies(ejemplares).csv")
CLEAN_BOOKS = os.path.join("data", "clean", "books_clean_extended.csv")
OUT_COPIES  = os.path.join("data", "clean", "copies_clean_extended.csv")

# ── Carga ──────────────────────────────────────────────────────────────────────
print("Cargando copies...")
df = pd.read_csv(RAW_COPIES)
n_raw = len(df)
print(f"  Filas cargadas: {n_raw}")

# ── Filtrado de huérfanos ──────────────────────────────────────────────────────
# Solo se descartan las copies cuyo book_id nunca existió en books.csv.
# En esta versión son 12 registros — los 4.015 de libros sin ISBN
# se recuperan porque books_clean_extended los conserva.
books_validos = pd.read_csv(CLEAN_BOOKS, usecols=["book_id"])["book_id"]
mask_validos = df["book_id"].isin(books_validos)
huerfanos = (~mask_validos).sum()
df = df[mask_validos].copy()
print(f"  Huérfanos descartados (book_id que nunca existió): {huerfanos}")
print(f"  Quedan tras filtrado: {len(df)}")

# ── Guardado ───────────────────────────────────────────────────────────────────
df.to_csv(OUT_COPIES, index=False)
print(f"\n✓ copies_clean_extended.csv guardado ({len(df)} filas) → {OUT_COPIES}")

# ── Resumen final ──────────────────────────────────────────────────────────────
print("\n── Resumen ──────────────────────────────────────────────────────────────")
print(f"  Filas originales:      {n_raw}")
print(f"  Huérfanos descartados: {huerfanos}")
print(f"  Ejemplares limpios:    {len(df)}")
