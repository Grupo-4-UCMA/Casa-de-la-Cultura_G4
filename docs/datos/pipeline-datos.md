# Pipeline de datos — Casa de la Cultura

> Última actualización: 18/05/2026  
> Responsable: Jose Luis Mus Peñarroja (Ingeniero de Datos)

Describe el ciclo de vida completo de los datos: desde los ficheros brutos del cliente hasta los artefactos que consume la aplicación en tiempo de ejecución. Todos los scripts son independientes de Django y se ejecutan desde la raíz del proyecto.

---

## 1. Datos de origen

Los ficheros brutos entregados por el cliente se guardan en `data/raw/` y **nunca se modifican**. No están versionados en Git (carpeta excluida en `.gitignore`).

| Fichero | Descripción | Registros |
|---|---|---|
| `books.csv` | Catálogo bibliográfico con ISBN, título, autor, año e idioma | 9.998 |
| `copies.csv` | Ejemplares físicos del bibliobús | — |
| `user_info.csv` | Usuarios registrados | 53.424 |
| `ratings.csv` | Valoraciones históricas (1-5 estrellas) | 5,7 M |

---

## 2. ETL y limpieza

Scripts en `etl/`. Cada bloque puede ejecutarse por separado; todos leen de `data/raw/` y escriben en `data/clean/`.

### Bloque 1 — Libros (`etl_books_extended.py`)

- Normaliza `language_code`: variantes de inglés (`en`, `en-US`, `en-GB`) → `eng`.
- ISBNs de 9 dígitos recuperados con zero-padding.
- Años negativos (a.C.) conservados — son datos correctos.
- Libros sin ISBN reciben identificador sintético `SIN-ISBN-{book_id:05d}` para respetar la restricción UNIQUE del esquema sin perder registros con ejemplares físicos.
- Separa autores en tabla relacional.

**Salida:** `data/clean/books_clean_extended.csv`, `data/clean/book_authors_extended.csv`

> Existe una versión A (`etl_books.py`) que descarta los 718 libros sin ISBN. Se optó por la versión B (extendida) para no perder registros con ejemplares físicos reales.

### Bloque 2 — Ejemplares (`etl_copies_extended.py`)

Limpieza de `copies.csv`.

**Salida:** `data/clean/copies_clean_extended.csv`

### Bloque 3 — Usuarios (`etl_users.py`)

- Campo `sexo` eliminado: indicación expresa del cliente y principio de minimización GDPR.

**Salida:** `data/clean/users_clean.csv`

### Bloque 4A — Valoraciones (`etl_ratings.py`)

Limpieza de `ratings.csv`.

**Salida:** `data/clean/ratings_clean.csv`

### Bloque 4B — Géneros (`etl_genres.py`)

Infiere el género literario de los 9.998 libros a partir de título, autor y año usando la API de Anthropic (Claude Sonnet). Proceso en 4 fases idempotentes (se puede interrumpir y reanudar):

1. `generate-prompts` — divide libros en lotes y genera prompts
2. `process-prompts` — llama a la API y guarda respuestas en `data/responses/`
3. `merge-responses` — reconstruye el CSV con columna `genre`
4. `validate` — verifica taxonomía y reporta estadísticas

**Requiere:** variable de entorno `ANTHROPIC_API_KEY` y acceso a internet.  
**Salida:** `data/clean/books_clean_final.csv`, `data/clean/book_genres.csv`

---

## 3. Artefactos versionados en `data/`

Resultado del ETL, versionados en Git para que cualquier miembro del equipo pueda arrancar el sistema sin re-ejecutar el pipeline.

| Fichero | Origen | Descripción |
|---|---|---|
| `books_with_genre.csv` | ETL bloque 1B + 4B | Catálogo completo con género literario. Columnas: `book_id`, `isbn`, `title`, `original_title`, `original_publication_year`, `language_code`, `genre` |
| `book_authors_extended.csv` | ETL bloque 1B | Relación libro-autor. Columnas: `book_id`, `author` |
| `copies_clean.csv` | ETL bloque 2 | Ejemplares limpios |
| `users_clean.csv` | ETL bloque 3 | Usuarios limpios |
| `votos_precalculados.csv` | `train.py` | Votos y nota media por libro. Columnas: `book_id`, `votos`, `nota_media` |
| `recs_libros.csv` | `train.py` | Top-3 libros similares por libro (cosine similarity). Columnas: `book_id`, `rec_1`, `rec_2`, `rec_3` |
| `recs_usuarios.csv` | `train.py` | Top-3 recomendaciones por usuario. Columnas: `user_id`, `rec_1`, `rec_2`, `rec_3` |
| `isbn_recuperados.csv` | `recuperar_isbn.py` | ISBNs obtenidos de Open Library para los 700 libros sin ISBN local. Columnas: `book_id`, `title`, `isbn`. 171 recuperados, 529 no encontrados en OL |
| `sinopsis.csv` | `generar_sinopsis.py` | Sinopsis reales servidas offline por el botón "✨ Preguntar a la IA". Columnas: `title`, `sinopsis`, `isbn`. ~1.400 entradas (libros más populares) |

---

## 4. Carga en base de datos

```bash
python load_data_fast.py
```

Lee los artefactos de `data/` y los carga en SQLite mediante `bulk_create`. Pobla las tablas `Book`, `Author`, `Copy`, `LibraryUser` y `Rating`. Tiempo estimado: ~2 minutos.

**Requiere:** entorno virtual activo con dependencias instaladas (`pip install -r requirements.txt`).

---

## 5. Entrenamiento del motor de recomendaciones

```bash
python train.py
```

Calcula similitud coseno ítem-ítem sobre la matriz de valoraciones (53K usuarios × 10K libros, 5,7M ratings). Genera los CSVs de recomendaciones y los votos precalculados. Tiempo estimado: ~5 minutos.

**Requiere:** base de datos cargada (paso 4).

---

## 6. Enriquecimiento externo (requiere internet — ejecutar antes de la demo)

Estos scripts consultan la API gratuita de Open Library. Una vez generados los ficheros, la app los sirve **offline**.

### Recuperar ISBNs faltantes

```bash
python recuperar_isbn.py
```

Para los libros con `isbn = N/A` en `books_with_genre.csv`, busca su ISBN en Open Library por título y autor. Guarda en `data/isbn_recuperados.csv`. Tiempo: ~7 minutos (700 libros).

Tras ejecutarlo, integrar los ISBNs recuperados en `books_with_genre.csv`:

```python
import pandas as pd
books = pd.read_csv('data/books_with_genre.csv', encoding='utf-8-sig', dtype=str)
rec   = pd.read_csv('data/isbn_recuperados.csv', dtype=str)
rec   = rec[rec['isbn'].notna() & rec['isbn'].str.strip().ne('')][['book_id','isbn']].rename(columns={'isbn':'isbn_nuevo'})
books = books.merge(rec, on='book_id', how='left')
mask  = books['isbn_nuevo'].notna() & books['isbn_nuevo'].str.strip().ne('')
books.loc[mask, 'isbn'] = books.loc[mask, 'isbn_nuevo']
books.drop(columns=['isbn_nuevo']).to_csv('data/books_with_genre.csv', index=False, encoding='utf-8')
```

### Generar sinopsis

```bash
python generar_sinopsis.py
```

Obtiene descripciones reales de libros desde Open Library (ruta ISBN → works o título → works). Prioriza libros por número de votos. Guarda en `data/sinopsis.csv`. Tiempo: ~3-4 horas para los 9.998 libros (reanudable si se interrumpe).

---

## 7. Orden de ejecución completo (entorno nuevo)

```bash
# 1. Entorno
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. ETL (requiere data/raw/ con los ficheros del cliente)
python etl/etl_books_extended.py
python etl/etl_copies_extended.py
python etl/etl_users.py
python etl/etl_ratings.py
python etl/etl_genres.py        # requiere ANTHROPIC_API_KEY e internet

# 3. Carga en BD
python manage.py migrate
python load_data_fast.py

# 4. Motor de recomendaciones
python train.py

# 5. Enriquecimiento (con internet, antes de la demo)
python recuperar_isbn.py
python generar_sinopsis.py

# 6. Arrancar la app
python manage.py runserver
```

> Los pasos 2 y 5 requieren internet y ya están ejecutados — sus artefactos están versionados en `data/`. En un entorno limpio basta con los pasos 3, 4 y 6.

---

## Véase también

- [Esquema de base de datos](esquema-bd.md)
- [Requisitos del cliente](../requisitos/requisitos_cliente_foro.md)
