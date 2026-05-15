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
Output: data/clean/books_clean_final.csv  (catálogo limpio sin género)
        data/clean/book_genres.csv        (tabla N:M libro-género)
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

IN_BOOKS        = os.path.join(DATA_CLEAN, "books_clean_extended.csv")
IN_AUTHORS      = os.path.join(DATA_CLEAN, "book_authors_extended.csv")
OUT_BOOKS_FINAL = os.path.join(DATA_CLEAN, "books_clean_final.csv")
OUT_BOOK_GENRES = os.path.join(DATA_CLEAN, "book_genres.csv")

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
MAX_TOKENS = 4096   # Margen amplio para 50 libros con 1-3 géneros cada uno
TEMPERATURE = 0     # Determinista, sin creatividad para esta tarea

cliente_api = Anthropic()  # Lee ANTHROPIC_API_KEY del entorno

# ── Prompt ───────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """Eres un bibliotecario experto clasificando libros para una biblioteca pública municipal.

A continuación tienes una lista de {n_libros} libros. Para cada uno, asigna entre 1 y 3 géneros aplicables de la siguiente taxonomía cerrada (no inventes géneros nuevos):

{taxonomia}

Reglas:
- Usa exactamente la grafía de la taxonomía (con tildes y mayúsculas como están).
- Mínimo 1 género, máximo 3. No abuses: solo añade un género extra si realmente aplica al libro.
- Combina géneros literarios con público objetivo cuando proceda. Ejemplos típicos:
    · Una novela de fantasía para adolescentes → ["Fantasía", "Juvenil"]
    · Un cuento ilustrado para niños → ["Infantil"] (o ["Infantil", "Aventura"] si la trama es claramente de aventuras)
    · Un thriller para adultos → ["Thriller"] (sin "Juvenil")
- Si dudas entre dos géneros literarios, elige el más específico (p. ej. "Ciencia ficción" antes que "Ficción").
- Usa "Clásicos" solo si el libro está claramente reconocido como tal (Cervantes, Dickens, Tolstói, Homero...). Suele combinarse con su género literario, p. ej. ["Clásicos", "Aventura"].
- Usa "Infantil" para libros dirigidos a 0-12 años y "Juvenil" para 13-17. Nunca ambos.
- Usa "Desconocido" como único género solo si realmente no puedes determinar nada.

Devuelve EXCLUSIVAMENTE un objeto JSON con esta estructura, sin texto adicional, sin markdown, sin explicaciones. Los valores son SIEMPRE listas, aunque tengan un único elemento:

{{
  "<book_id>": ["<género>"],
  "<book_id>": ["<género>", "<género>"],
  "<book_id>": ["<género>", "<género>", "<género>"]
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
    Lee todas las respuestas JSON de data/responses/ y produce dos
    artefactos:
      - books_clean_final.csv : el catálogo limpio sin columna de género.
      - book_genres.csv       : tabla N:M (book_id, genre), una fila por par.

    Si un género devuelto no está en la taxonomía, se descarta y se
    reporta. Si un libro queda sin ningún género válido tras descartar
    los fuera de taxonomía, se le asigna "Desconocido".
    """
    print("Cargando respuestas...")
    asignaciones = {}        # book_id (int) -> list[str]
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

        for book_id_str, generos in generos_lote.items():
            book_id = int(book_id_str)
            # Defensa: si el modelo devolvió string en vez de lista, lo
            # envolvemos. Si devolvió otra cosa rara, lo descartamos.
            if isinstance(generos, str):
                generos = [generos]
            elif not isinstance(generos, list):
                continue

            validos = []
            for g in generos:
                if g in TAXONOMIA:
                    validos.append(g)
                else:
                    fuera_taxonomia.append((book_id, g))

            if not validos:
                validos = ["Desconocido"]
            # Deduplicamos preservando orden
            asignaciones[book_id] = list(dict.fromkeys(validos))

    print(f"  Libros con asignaciones: {len(asignaciones)}")
    total_pares = sum(len(gs) for gs in asignaciones.values())
    print(f"  Pares libro-género: {total_pares}")
    print(f"  Media de géneros por libro: {total_pares / len(asignaciones):.2f}")

    if fuera_taxonomia:
        print(f"  ⚠ Géneros fuera de taxonomía descartados: "
              f"{len(fuera_taxonomia)}")
        for bid, g in fuera_taxonomia[:5]:
            print(f"      book_id={bid} → '{g}'")

    # Cargar el CSV base
    print("\nGenerando artefactos...")
    df = pd.read_csv(IN_BOOKS)

    # books_clean_final.csv : catálogo sin columna de género
    df.to_csv(OUT_BOOKS_FINAL, index=False)
    print(f"✓ {OUT_BOOKS_FINAL} guardado ({len(df)} filas)")

    # book_genres.csv : tabla N:M
    pares = []
    for book_id in df["book_id"]:
        for genero in asignaciones.get(book_id, ["Desconocido"]):
            pares.append({"book_id": book_id, "genre": genero})
    df_genres = pd.DataFrame(pares)
    df_genres.to_csv(OUT_BOOK_GENRES, index=False)
    print(f"✓ {OUT_BOOK_GENRES} guardado ({len(df_genres)} filas)")


# ── Fase 4: validar resultado ────────────────────────────────────────────
def validate():
    """
    Verifica que los artefactos finales cumplen las invariantes y
    muestra estadísticas del reparto.
    """
    print(f"Validando {OUT_BOOKS_FINAL} y {OUT_BOOK_GENRES}...\n")

    df_b = pd.read_csv(OUT_BOOKS_FINAL)
    df_g = pd.read_csv(OUT_BOOK_GENRES)

    # Invariantes
    assert len(df_b) == 9998, f"Esperaba 9998 libros, hay {len(df_b)}"
    libros_con_genero = df_g["book_id"].nunique()
    assert libros_con_genero == 9998, (
        f"Solo {libros_con_genero} libros tienen género asignado, "
        f"esperaba 9998"
    )

    # Verificar taxonomía
    fuera = set(df_g["genre"].unique()) - set(TAXONOMIA)
    assert not fuera, f"Géneros fuera de taxonomía: {fuera}"

    # Verificar 1-3 géneros por libro
    conteo_por_libro = df_g.groupby("book_id").size()
    max_g = conteo_por_libro.max()
    min_g = conteo_por_libro.min()
    media = conteo_por_libro.mean()

    print(f"  ✓ 9998 libros en books_clean_final.csv")
    print(f"  ✓ {libros_con_genero} libros con al menos un género")
    print(f"  ✓ Todos los géneros están dentro de la taxonomía cerrada")
    print(f"  ✓ Géneros por libro: min={min_g}, max={max_g}, "
          f"media={media:.2f}\n")

    # Reparto por género (en cuántos libros aparece cada uno)
    print("── Reparto por género (libros en los que aparece) ─────")
    conteo = df_g["genre"].value_counts()
    for genero, n in conteo.items():
        pct = 100 * n / len(df_b)
        print(f"  {genero:<28} {n:>5}  ({pct:5.1f}% de libros)")

    print(f"\n  Total pares libro-género: {len(df_g)}")
    print(f"  Géneros usados: {df_g['genre'].nunique()}")


if __name__ == "__main__":
    # Pipeline completo. Cada fase es idempotente.
    # generate_prompts() solo se ejecuta una vez (los prompts ya existen).
    # process_prompts() salta los lotes que ya tienen respuesta.
    # merge_responses() + validate() reconstruyen los CSVs finales.
    generate_prompts(batch_size=50)
    process_prompts()
    merge_responses()
    print()
    validate()
