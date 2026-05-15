"""
ETL — Bloque 4: Enriquecimiento de género literario
Casa de la Cultura · Grupo 4 · Ingeniería de Datos

Infiere el género literario de los 9.998 libros del catálogo a partir
de título, autor y año, usando la API de Anthropic (Sonnet 4.5).

Arquitectura en 4 fases:
  1. generate-prompts   Divide los libros en lotes y genera un prompt por lote.
  2. process-prompts    Llama a la API por lote y guarda las respuestas.
  3. merge-responses    Reconstruye el CSV con la columna genre añadida.
  4. validate           Verifica la taxonomía y reporta estadísticas.

Cada fase es independiente. El script es idempotente: si se corta,
se reanuda sin reprocesar lotes ya completados.

Input:  data/clean/books_clean_extended.csv
        data/clean/book_authors_extended.csv
Output: data/clean/books_with_genre.csv
"""

import os
import pandas as pd
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic, APIError

load_dotenv()

# ── Rutas ────────────────────────────────────────────────────────────────
DATA_CLEAN   = os.path.join("data", "clean")
DATA_PROMPTS = os.path.join("data", "prompts")
DATA_RESPS   = os.path.join("data", "responses")

IN_BOOKS   = os.path.join(DATA_CLEAN, "books_clean_extended.csv")
IN_AUTHORS = os.path.join(DATA_CLEAN, "book_authors_extended.csv")
OUT_CSV    = os.path.join(DATA_CLEAN, "books_with_genre.csv")

# ── Taxonomía cerrada ────────────────────────────────────────────────────
# 29 categorías + "Desconocido" como salida de seguridad.
# Acordada en reunión del 13/05/2026. No modificar sin consenso del equipo.
TAXONOMIA = [
    "Arte", "Autoayuda", "Aventura", "Biografía", "Ciencia",
    "Ciencia ficción", "Clásicos", "Cocina", "Cómic y novela gráfica",
    "Deportes", "Ensayo", "Fantasía", "Ficción", "Ficción histórica",
    "Historia", "Infantil", "Juvenil", "Memorias", "Misterio", "Música",
    "Negocios", "No ficción", "Poesía", "Psicología",
    "Religión y espiritualidad", "Romántica", "Terror", "Thriller",
    "Viajes", "Desconocido",
]
# ── Configuración de la API ──────────────────────────────────────────────
MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 4096   # Margen amplio para 50 pares book_id -> género
TEMPERATURE = 0     # Determinista, sin creatividad para esta tarea

cliente_api = Anthropic()  # Lee ANTHROPIC_API_KEY del entorno
# ── Prompt ───────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """Eres un bibliotecario experto clasificando libros para una biblioteca pública municipal.

A continuación tienes una lista de {n_libros} libros. Para cada uno, asigna UN ÚNICO género de la siguiente taxonomía cerrada (no inventes géneros nuevos, no devuelvas varios):

{taxonomia}

Reglas:
- Usa exactamente la grafía de la taxonomía (con tildes y mayúsculas como están).
- Si dudas entre dos géneros, elige el más específico (p. ej. "Ciencia ficción" antes que "Ficción").
- Si un libro es clásico de cualquier género, prioriza "Clásicos" solo si está claramente reconocido como tal (Cervantes, Dickens, Tolstói, Homero...). Si no, usa el género literario.
- Usa "Infantil" para 0-12 años y "Juvenil" para 13-17.
- Usa "Desconocido" solo si realmente no puedes determinarlo con la información dada.

Devuelve EXCLUSIVAMENTE un objeto JSON con esta estructura, sin texto adicional, sin markdown, sin explicaciones:

{{
  "<book_id>": "<género>",
  "<book_id>": "<género>"
}}

Lista de libros:

{libros}
"""


def generar_prompt(df_lote):
    """
    Construye el prompt completo para un lote de libros.
    df_lote debe tener las columnas: book_id, title, authors,
    original_publication_year.
    """
    lineas = []
    for _, row in df_lote.iterrows():
        year = row["original_publication_year"]
        year_str = str(int(year)) if pd.notna(year) else "desconocido"
        # Escapamos comillas dobles en title y authors por si acaso
        title = str(row["title"]).replace('"', "'")
        authors = str(row["authors"]).replace('"', "'")
        lineas.append(
            f'book_id={row["book_id"]} | title="{title}" | '
            f'authors="{authors}" | year={year_str}'
        )

    return PROMPT_TEMPLATE.format(
        n_libros=len(df_lote),
        taxonomia=", ".join(TAXONOMIA) + ".",
        libros="\n".join(lineas),
    )

# ── Carga de datos ───────────────────────────────────────────────────────
def cargar_libros_con_autores():
    """
    Devuelve un DataFrame con book_id, title, authors, year listo para
    construir prompts. Los autores se concatenan con ', ' cuando hay
    varios por libro. Si un libro no tiene autores asociados (no debería
    pasar tras la limpieza, pero por si acaso), authors queda como cadena
    vacía.
    """
    libros = pd.read_csv(IN_BOOKS)
    autores = pd.read_csv(IN_AUTHORS)

    # Concatenar autores por libro
    autores_por_libro = (
        autores.groupby("book_id")["author"]
               .apply(lambda s: ", ".join(s))
               .reset_index()
               .rename(columns={"author": "authors"})
    )

    # Merge y selección de columnas relevantes para el prompt
    df = libros.merge(autores_por_libro, on="book_id", how="left")
    df["authors"] = df["authors"].fillna("")
    df["original_publication_year"] = df["original_publication_year"].astype("Int64")

    return df[["book_id", "title", "authors", "original_publication_year"]]


# ── Fase 1: generar prompts ──────────────────────────────────────────────
def generate_prompts(batch_size=50):
    """
    Divide los libros en lotes y escribe un fichero .txt por lote en
    data/prompts/. Idempotente: si un fichero ya existe, lo sobrescribe
    (la generación es determinista, no hay riesgo).
    """
    os.makedirs(DATA_PROMPTS, exist_ok=True)

    df = cargar_libros_con_autores()
    n_total = len(df)
    n_lotes = (n_total + batch_size - 1) // batch_size

    print(f"Generando prompts: {n_total} libros en {n_lotes} lotes "
          f"de {batch_size}...")

    for i in range(n_lotes):
        ini = i * batch_size
        fin = min(ini + batch_size, n_total)
        lote = df.iloc[ini:fin]

        prompt = generar_prompt(lote)
        nombre = f"genre_batch_{i+1:03d}.txt"
        ruta = os.path.join(DATA_PROMPTS, nombre)

        with open(ruta, "w", encoding="utf-8") as f:
            f.write(prompt)

    print(f"✓ {n_lotes} prompts generados en {DATA_PROMPTS}/")

# ── Fase 2: procesar prompts contra la API ───────────────────────────────
def limpiar_respuesta(texto):
    """
    El modelo a veces envuelve el JSON en bloques de markdown
    (```json ... ```) a pesar de pedirle que no lo haga. Esta función
    elimina esas marcas si aparecen, dejando solo el JSON puro.
    """
    texto = texto.strip()
    if texto.startswith("```"):
        # Quitar la primera línea (``` o ```json)
        texto = texto.split("\n", 1)[1] if "\n" in texto else texto
        # Quitar el cierre ```
        if texto.endswith("```"):
            texto = texto[:-3].rstrip()
    return texto.strip()

def process_prompts():
    """
    Recorre todos los prompts de data/prompts/, llama a la API por cada
    uno y guarda la respuesta en data/responses/ como JSON.

    Idempotente: si la respuesta ya existe, salta el lote.
    Si la API falla en un lote, lo registra y sigue con el siguiente
    (los lotes fallidos se reintentan en la siguiente ejecución).
    """
    os.makedirs(DATA_RESPS, exist_ok=True)

    prompts = sorted(f for f in os.listdir(DATA_PROMPTS) if f.endswith(".txt"))
    total = len(prompts)
    print(f"Procesando {total} lotes contra {MODEL}...\n")

    procesados = 0
    saltados = 0
    fallidos = 0
    coste_total = 0.0
    inicio = time.time()

    for i, nombre_prompt in enumerate(prompts, 1):
        nombre_resp = nombre_prompt.replace(".txt", ".json")
        ruta_resp = os.path.join(DATA_RESPS, nombre_resp)

        # Idempotencia: si ya existe la respuesta, saltar
        if os.path.exists(ruta_resp):
            saltados += 1
            continue

        # Leer prompt
        with open(os.path.join(DATA_PROMPTS, nombre_prompt),
                  encoding="utf-8") as f:
            prompt = f.read()

        # Llamada a la API
        try:
            t0 = time.time()
            resp = cliente_api.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                messages=[{"role": "user", "content": prompt}],
            )
            dur = time.time() - t0

            # Calcular coste (Sonnet 4.5: $3/M input, $15/M output)
            coste = (resp.usage.input_tokens * 3
                     + resp.usage.output_tokens * 15) / 1_000_000
            coste_total += coste

            # Guardar respuesta en disco
            salida = {
                "result": limpiar_respuesta(resp.content[0].text),
                "model": resp.model,
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
                "duration_s": round(dur, 2),
                "cost_usd": round(coste, 6),
            }
            with open(ruta_resp, "w", encoding="utf-8") as f:
                json.dump(salida, f, ensure_ascii=False, indent=2)

            procesados += 1
            print(f"  [{i:3d}/{total}] {nombre_prompt}  "
                  f"{resp.usage.input_tokens}in / "
                  f"{resp.usage.output_tokens}out  "
                  f"{dur:.1f}s  ${coste:.4f}")

        except APIError as e:
            fallidos += 1
            print(f"  [{i:3d}/{total}] {nombre_prompt}  ERROR: {e}")

    duracion_total = time.time() - inicio
    print(f"\n── Resumen ──────────────────────────────────────────────")
    print(f"  Procesados ahora:   {procesados}")
    print(f"  Saltados (ya hechos): {saltados}")
    print(f"  Fallidos:           {fallidos}")
    print(f"  Coste total sesión: ${coste_total:.4f}")
    print(f"  Duración total:     {duracion_total/60:.1f} min")

# ── Fase 3: integrar respuestas en CSV final ─────────────────────────────
def merge_responses():
    """
    Lee todas las respuestas JSON de data/responses/, extrae el género
    de cada libro y produce books_with_genre.csv añadiendo una columna
    'genre' al CSV original.

    Si un libro no tiene respuesta (lote fallido o falta), se asigna
    'Desconocido'. Si un género devuelto no está en la taxonomía, también
    se reemplaza por 'Desconocido' y se reporta.
    """
    print("Cargando respuestas...")
    asignaciones = {}        # book_id (int) -> género (str)
    fuera_taxonomia = []     # (book_id, género) para reportar

    ficheros = sorted(f for f in os.listdir(DATA_RESPS) if f.endswith(".json"))
    for nombre in ficheros:
        ruta = os.path.join(DATA_RESPS, nombre)
        with open(ruta, encoding="utf-8") as f:
            data = json.load(f)

        try:
            generos_lote = json.loads(data["result"])
        except json.JSONDecodeError as e:
            print(f"  ⚠ {nombre}: JSON inválido, se omite ({e})")
            continue

        for book_id_str, genero in generos_lote.items():
            book_id = int(book_id_str)
            if genero not in TAXONOMIA:
                fuera_taxonomia.append((book_id, genero))
                genero = "Desconocido"
            asignaciones[book_id] = genero

    print(f"  Asignaciones recogidas: {len(asignaciones)}")
    if fuera_taxonomia:
        print(f"  ⚠ Géneros fuera de taxonomía corregidos a "
              f"'Desconocido': {len(fuera_taxonomia)}")
        for bid, g in fuera_taxonomia[:5]:
            print(f"      book_id={bid} → '{g}'")

    # Cargar el CSV base y añadir la columna
    print("\nIntegrando en books_clean_extended.csv...")
    df = pd.read_csv(IN_BOOKS)
    df["genre"] = df["book_id"].map(asignaciones).fillna("Desconocido")

    n_sin_asignar = (df["genre"] == "Desconocido").sum()
    n_total = len(df)
    df.to_csv(OUT_CSV, index=False)

    print(f"✓ {OUT_CSV} guardado ({n_total} filas)")
    print(f"  Con género asignado: {n_total - n_sin_asignar}")
    print(f"  Como 'Desconocido':  {n_sin_asignar}")


# ── Fase 4: validar resultado ────────────────────────────────────────────
def validate():
    """
    Verifica que el CSV final cumple las invariantes esperadas y
    muestra el reparto por género.
    """
    print(f"Validando {OUT_CSV}...\n")
    df = pd.read_csv(OUT_CSV)

    # Invariantes
    assert len(df) == 9998, f"Esperaba 9998 filas, hay {len(df)}"
    assert df["genre"].notna().all(), "Hay filas con genre NULL"

    # Verificar que todos los géneros están en la taxonomía
    fuera = set(df["genre"].unique()) - set(TAXONOMIA)
    assert not fuera, f"Géneros fuera de taxonomía: {fuera}"

    print(f"  ✓ {len(df)} libros con columna 'genre' rellena")
    print(f"  ✓ Todos los géneros están dentro de la taxonomía cerrada\n")

    # Reparto por género
    print("── Reparto por género ─────────────────────────────────")
    conteo = df["genre"].value_counts()
    for genero, n in conteo.items():
        pct = 100 * n / len(df)
        print(f"  {genero:<28} {n:>5}  ({pct:5.1f}%)")
    print(f"\n  Total: {len(df)} libros, {df['genre'].nunique()} géneros usados")

if __name__ == "__main__":
    # Pipeline completo. Cada fase es idempotente.
    # generate_prompts() solo se ejecuta una vez (los prompts ya existen).
    # process_prompts() salta los lotes que ya tienen respuesta.
    # merge_responses() + validate() reconstruyen el CSV final.
    generate_prompts(batch_size=50)
    process_prompts()
    merge_responses()
    print()
    validate()
