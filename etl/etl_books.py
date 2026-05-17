"""
ETL — Bloque 1: Limpieza de books.csv
Casa de la Cultura · Grupo 4 · Ingeniería de Datos

Decisiones de limpieza aplicadas (ver auditoría 01_auditoria_calidad_datos.ipynb):
  - Se descartan filas sin ISBN o sin año de publicación (~718 registros).
  - ISBNs de 9 dígitos se recuperan con zero-padding (zfill(10)).
  - Variantes de inglés en language_code (en-US, en-GB, en-CA, en) → 'eng'.
  - Años negativos (a.C.) se conservan: son datos correctos.
  - Los autores se separan en lista para poblar las tablas author y book_author.

Input:  data/raw/books.csv
Output: data/clean/books_clean.csv
        data/clean/book_authors.csv   (relación libro–autor, una fila por autor)
"""

import pandas as pd
import os

# ── Rutas ──────────────────────────────────────────────────────────────────────
RAW_PATH   = os.path.join("data", "raw", "books.csv")
CLEAN_DIR  = os.path.join("data", "clean")
OUT_BOOKS  = os.path.join(CLEAN_DIR, "books_clean.csv")
OUT_AUTHS  = os.path.join(CLEAN_DIR, "book_authors.csv")

os.makedirs(CLEAN_DIR, exist_ok=True)

# ── Carga ──────────────────────────────────────────────────────────────────────
print("Cargando books.csv...")
df = pd.read_csv(RAW_PATH, dtype={"isbn": str}, on_bad_lines='skip')   # isbn como str para no perder ceros
n_raw = len(df)
print(f"  Filas cargadas: {n_raw}")

# ── Filtrado: sin ISBN o sin año ───────────────────────────────────────────────
# Se descartan registros que no tienen ISBN o que no tienen año de publicación.
# Sin ISBN no hay forma de identificar el libro en la BD.
# Sin año el motor de recomendación no puede usarlos correctamente.
mask_validos = df["isbn"].notna() & df["original_publication_year"].notna()
descartados = (~mask_validos).sum()
df = df[mask_validos].copy()
print(f"  Descartados (sin ISBN o sin año): {descartados}")
print(f"  Quedan tras filtrado: {len(df)}")

# ── Zero-padding en ISBNs de 9 dígitos ────────────────────────────────────────
# El sistema anterior guardó ~6.600 ISBNs sin el cero inicial.
# Los recuperamos rellenando con cero por la izquierda hasta 10 caracteres.
df["isbn"] = df["isbn"].str.strip().str.zfill(10)
n_padded = (df["isbn"].str.len() == 10).sum()
print(f"  ISBNs con zero-padding aplicado (ahora todos 10 dígitos): {n_padded}")

# ── Normalización de language_code ────────────────────────────────────────────
# Las variantes regionales del inglés se unifican en 'eng' para simplificar
# filtros y dashboards. El resto de códigos se dejan tal cual.
variantes_ingles = {"en-US", "en-GB", "en-CA", "en-AU", "en"}
df["language_code"] = df["language_code"].apply(
    lambda x: "eng" if x in variantes_ingles else x
)
print(f"  Valores únicos en language_code tras normalización: {df['language_code'].nunique()}")
print(f"  language_code nulos (se mantienen como NULL en BD): {df['language_code'].isna().sum()}")

# ── Separación de autores ──────────────────────────────────────────────────────
# Los autores vienen separados por coma en una sola columna.
# Se genera un DataFrame separado (book_authors) con una fila por autor,
# que servirá para poblar las tablas 'author' y 'book_author'.
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

# ── Limpieza de columnas finales para books_clean ─────────────────────────────
# Eliminamos la columna 'authors' (ya está en book_authors)
# e 'image_url' (no se va a cargar en la BD según el esquema).
cols_a_guardar = ["book_id", "isbn", "title", "original_title",
                  "original_publication_year", "language_code"]
df_clean = df[cols_a_guardar].copy()

# Aseguramos tipo entero en año (puede quedar como float tras el dropna)
df_clean["original_publication_year"] = df_clean["original_publication_year"].astype(int)

# ── Guardado ───────────────────────────────────────────────────────────────────
df_clean.to_csv(OUT_BOOKS, index=False)
book_authors.to_csv(OUT_AUTHS, index=False)

print(f"\n✓ books_clean.csv guardado ({len(df_clean)} filas) → {OUT_BOOKS}")
print(f"✓ book_authors.csv guardado ({len(book_authors)} filas) → {OUT_AUTHS}")

# ── Resumen final ──────────────────────────────────────────────────────────────
print("\n── Resumen ──────────────────────────────────────────────────────────────")
print(f"  Filas originales:      {n_raw}")
print(f"  Descartadas:           {descartados}")
print(f"  Libros limpios:        {len(df_clean)}")
print(f"  ISBNs recuperados:     ~6.600 (zero-padding)")
print(f"  language_code nulos:   {df_clean['language_code'].isna().sum()}")
