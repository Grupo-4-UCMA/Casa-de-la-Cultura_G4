"""
ETL — Bloque 1B: Limpieza de books.csv (versión extendida)
Casa de la Cultura · Grupo 4 · Ingeniería de Datos

DIFERENCIA CON etl_books.py (versión A):
  - La versión A descarta 718 libros sin ISBN o sin año.
  - Esta versión (B) conserva todos los registros — todos tienen al menos
    título y autor, son libros reales con ejemplares físicos en el bibliobús.
  - Los campos faltantes (isbn, año) quedan como NULL en la BD.
  - Pendiente decisión del equipo/cliente antes de usar esta versión.

Decisiones de limpieza aplicadas:
  - No se descarta ningún registro (todos tienen título y autor).
  - ISBNs de 9 dígitos se recuperan con zero-padding (zfill(10)).
  - Variantes de inglés en language_code (en-US, en-GB, en-CA, en) → 'eng'.
  - Años negativos (a.C.) se conservan: son datos correctos.
  - Los autores se separan en lista para poblar las tablas author y book_author.

Input:  data/raw/books.csv
Output: data/clean/books_clean_extended.csv
        data/clean/book_authors_extended.csv
"""

import pandas as pd
import os

# ── Rutas ──────────────────────────────────────────────────────────────────────
RAW_PATH   = os.path.join("data", "raw", "books.csv")
CLEAN_DIR  = os.path.join("data", "clean")
OUT_BOOKS  = os.path.join(CLEAN_DIR, "books_clean_extended.csv")
OUT_AUTHS  = os.path.join(CLEAN_DIR, "book_authors_extended.csv")

os.makedirs(CLEAN_DIR, exist_ok=True)

# ── Carga ──────────────────────────────────────────────────────────────────────
print("Cargando books.csv...")
df = pd.read_csv(RAW_PATH, dtype={"isbn": str}, on_bad_lines='skip')
n_raw = len(df)
print(f"  Filas cargadas: {n_raw}")

# ── Sin filtrado ───────────────────────────────────────────────────────────────
# Conservamos todos los registros. Tras el análisis, los 718 sin ISBN o sin año
# tienen todos al menos título y autor — son libros reales con ejemplares físicos
# en el bibliobús. Los campos faltantes quedan como NULL en la BD.
print(f"  Sin ISBN:  {df['isbn'].isna().sum()}")
print(f"  Sin año:   {df['original_publication_year'].isna().sum()}")
print(f"  Sin ambos: {(df['isbn'].isna() & df['original_publication_year'].isna()).sum()}")

# ── Zero-padding en ISBNs de 9 dígitos ────────────────────────────────────────
# Solo se aplica a los que tienen ISBN. Los que tienen isbn=None se dejan tal cual.
df["isbn"] = df["isbn"].apply(
    lambda x: x.strip().zfill(10) if pd.notna(x) else x
)
print(f"\n  ISBNs con zero-padding aplicado (ahora todos 10 dígitos): {df['isbn'].notna().sum()}")
print(f"  ISBNs nulos conservados: {df['isbn'].isna().sum()}")

# ── Normalización de language_code ────────────────────────────────────────────
# Las variantes regionales del inglés se unifican en 'eng'.
variantes_ingles = {"en-US", "en-GB", "en-CA", "en-AU", "en"}
df["language_code"] = df["language_code"].apply(
    lambda x: "eng" if x in variantes_ingles else x
)
print(f"  Valores únicos en language_code tras normalización: {df['language_code'].nunique()}")
print(f"  language_code nulos: {df['language_code'].isna().sum()}")

# ── Separación de autores ──────────────────────────────────────────────────────
print("\nSeparando autores...")
book_authors = (
    df[["book_id", "authors"]]
    .dropna(subset=["authors"])
    .assign(author=lambda d: d["authors"].str.split(","))
    .explode("author")
    .assign(author=lambda d: d["author"].str.strip())
    .drop(columns=["authors"])
    .drop_duplicates()
    .reset_index(drop=True)
)
print(f"  Relaciones libro–autor generadas: {len(book_authors)}")
print(f"  Autores únicos: {book_authors['author'].nunique()}")

# ── Limpieza de columnas finales ───────────────────────────────────────────────
cols_a_guardar = ["book_id", "isbn", "title", "original_title",
                  "original_publication_year", "language_code"]
df_clean = df[cols_a_guardar].copy()

# ── Guardado ───────────────────────────────────────────────────────────────────
df_clean.to_csv(OUT_BOOKS, index=False)
book_authors.to_csv(OUT_AUTHS, index=False)

print(f"\n✓ books_clean_extended.csv guardado ({len(df_clean)} filas) → {OUT_BOOKS}")
print(f"✓ book_authors_extended.csv guardado ({len(book_authors)} filas) → {OUT_AUTHS}")

# ── Resumen final ──────────────────────────────────────────────────────────────
print("\n── Resumen ──────────────────────────────────────────────────────────────")
print(f"  Filas originales:          {n_raw}")
print(f"  Descartadas:               0 (versión extendida conserva todos)")
print(f"  Libros limpios:            {len(df_clean)}")
print(f"  Con ISBN:                  {df_clean['isbn'].notna().sum()}")
print(f"  Sin ISBN (isbn=None):      {df_clean['isbn'].isna().sum()}")
print(f"  Con año:                   {df_clean['original_publication_year'].notna().sum()}")
print(f"  Sin año:                   {df_clean['original_publication_year'].isna().sum()}")
