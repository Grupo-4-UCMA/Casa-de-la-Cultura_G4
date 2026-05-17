"""
Genera data/sinopsis.csv consultando la API gratuita de Open Library.
Script standalone — no requiere Django.

Uso:
    python generar_sinopsis.py

Reanuda automáticamente si se interrumpe (salta libros ya en el CSV).
Columnas de salida: title, sinopsis, isbn

Flujo de peticiones por libro:
  - Con ISBN:  /api/books?bibkeys=ISBN:…&jscmd=data  →  si tiene 'works', va a /works/{key}.json
  - Sin ISBN:  /search.json?title=…&author=…  →  extrae 'key'  →  /works/{key}.json
"""

import os
import time
import urllib.request
import urllib.parse
import json
import csv
import re

BOOKS_CSV     = 'data/books_with_genre.csv'
AUTHORS_CSV   = 'data/book_authors_extended.csv'
VOTOS_CSV     = 'data/votos_precalculados.csv'
OUTPUT_CSV    = 'data/sinopsis.csv'
PAUSA         = 0.6   # segundos entre peticiones
GUARDADO_CADA = 100


# ── helpers ───────────────────────────────────────────────────────────────────

def limpiar_texto(texto):
    if not texto:
        return ''
    texto = re.sub(r'<[^>]+>', ' ', texto)
    texto = re.sub(r'\{\{[^}]*\}\}', '', texto)
    texto = re.sub(r'\[\[([^\]|]+\|)?([^\]]+)\]\]', r'\2', texto)
    return re.sub(r'\s+', ' ', texto).strip()


def get_url(url, timeout=12):
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'CasaCulturaBot/1.0 (biblioteca-demo; contact jl@socjoseluis.com)'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f'[ERR {e}]', end=' ')
        return None


def extraer_desc_work(work_obj):
    """Extrae descripción de un objeto /works/OL….json."""
    d = work_obj.get('description') or work_obj.get('first_sentence')
    if not d:
        return ''
    if isinstance(d, dict):
        d = d.get('value', '')
    return limpiar_texto(str(d))


def isbn_es_valido(isbn):
    return bool(isbn) and isbn.upper() not in ('', 'N/A', 'NA', 'NONE')


# ── petición al works endpoint ────────────────────────────────────────────────

def desc_desde_work_key(work_key):
    """work_key p.ej. '/works/OL82592W'. Devuelve (sinopsis, isbn_extra)."""
    url = f'https://openlibrary.org{work_key}.json'
    data = get_url(url)
    if not data:
        return '', ''
    try:
        obj = json.loads(data)
    except Exception:
        return '', ''

    sinopsis = extraer_desc_work(obj)

    # ISBNs: a veces el work tiene editions con ISBNs; los dejamos vacíos aquí
    # (el caller ya tiene el ISBN si vino por esa ruta)
    return sinopsis, ''


# ── estrategia 1: ISBN → works ────────────────────────────────────────────────

def sinopsis_por_isbn(isbn):
    """Devuelve (sinopsis, work_key_o_vacio)."""
    url = f'https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data'
    data = get_url(url)
    if not data:
        return '', ''
    try:
        obj = json.loads(data)
    except Exception:
        return '', ''
    key = f'ISBN:{isbn}'
    if key not in obj:
        return '', ''
    book = obj[key]

    # Descripción directa (rara, pero existe en algunos libros)
    sinopsis = extraer_desc_work(book)
    if sinopsis:
        return sinopsis, ''

    # Buscar vía works
    works = book.get('works', [])
    if works:
        work_key = works[0].get('key', '')
        if work_key:
            return work_key, 'WORK_KEY'   # señal para el caller
    return '', ''


# ── estrategia 2: título+autor → works ───────────────────────────────────────

def buscar_work_key(title, author=''):
    """Devuelve (work_key, isbn_ol) desde search.json."""
    params = {'title': title, 'limit': '1', 'fields': 'key,isbn'}
    if author:
        params['author'] = author
    url = f'https://openlibrary.org/search.json?' + urllib.parse.urlencode(params)
    data = get_url(url)
    if not data:
        return '', ''
    try:
        obj = json.loads(data)
    except Exception:
        return '', ''
    docs = obj.get('docs', [])
    if not docs:
        return '', ''
    doc = docs[0]
    work_key = doc.get('key', '')

    isbn_lista = doc.get('isbn', [])
    isbn_ol = ''
    if isbn_lista:
        isbn13 = [x for x in isbn_lista if len(x) == 13]
        isbn_ol = isbn13[0] if isbn13 else isbn_lista[0]

    return work_key, isbn_ol


# ── carga de datos ────────────────────────────────────────────────────────────

def cargar_libros():
    libros = {}
    with open(BOOKS_CSV, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            bid = row['book_id'].strip()
            libros[bid] = {
                'book_id': bid,
                'isbn':    row.get('isbn', '').strip(),
                'title':   row.get('title', '').strip(),
                'author':  '',
                'votos':   0,
            }
    with open(AUTHORS_CSV, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            bid = row['book_id'].strip()
            if bid in libros:
                libros[bid]['author'] = row.get('author', '').strip()
    with open(VOTOS_CSV, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            bid = row['book_id'].strip()
            if bid in libros:
                try:
                    libros[bid]['votos'] = int(float(row.get('votos', 0)))
                except ValueError:
                    pass
    return sorted(libros.values(), key=lambda x: x['votos'], reverse=True)


def cargar_sinopsis_existentes():
    existentes = {}
    if not os.path.exists(OUTPUT_CSV):
        return existentes
    with open(OUTPUT_CSV, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            t = row.get('title', '').strip()
            if t:
                existentes[t.lower()] = {
                    'title':    t,
                    'sinopsis': row.get('sinopsis', '').strip(),
                    'isbn':     row.get('isbn', '').strip(),
                }
    return existentes


# ── escritura incremental ─────────────────────────────────────────────────────

def guardar_sinopsis(resultados):
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['title', 'sinopsis', 'isbn'])
        writer.writeheader()
        for title, datos in resultados.items():
            writer.writerow({'title': title, 'sinopsis': datos['sinopsis'], 'isbn': datos['isbn']})


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print('Cargando datos...')
    libros   = cargar_libros()
    total    = len(libros)
    print(f'  {total} libros cargados')

    existentes = cargar_sinopsis_existentes()
    resultados = {v['title']: {'sinopsis': v['sinopsis'], 'isbn': v['isbn']}
                  for v in existentes.values()}
    ya_hechos  = set(existentes.keys())

    pendientes = [l for l in libros if l['title'].lower() not in ya_hechos]
    print(f'  {len(ya_hechos)} ya en CSV, {len(pendientes)} pendientes\n')

    procesados       = 0
    con_sinopsis     = 0
    isbn_recuperados = 0

    for i, libro in enumerate(pendientes, 1):
        title  = libro['title']
        isbn   = libro['isbn']
        author = libro['author']
        votos  = libro['votos']

        pos = total - len(pendientes) + i
        print(f'[{pos}/{total}] "{title[:55]}" ({votos}v) — ', end='', flush=True)

        sinopsis   = ''
        isbn_final = isbn if isbn_es_valido(isbn) else ''

        if isbn_es_valido(isbn):
            resultado, flag = sinopsis_por_isbn(isbn)
            time.sleep(PAUSA)
            if flag == 'WORK_KEY':
                # resultado es la work_key
                sinopsis, _ = desc_desde_work_key(resultado)
                time.sleep(PAUSA)
                etiqueta = f'ISBN→work: {len(sinopsis)}c' if sinopsis else 'ISBN→work: sin desc'
            elif resultado:
                sinopsis = resultado
                etiqueta = f'ISBN directo: {len(sinopsis)}c'
            else:
                # ISBN no encontrado → fallback búsqueda por título
                work_key, isbn_ol = buscar_work_key(title, author)
                time.sleep(PAUSA)
                if work_key:
                    sinopsis, _ = desc_desde_work_key(work_key)
                    time.sleep(PAUSA)
                etiqueta = f'título→work: {len(sinopsis)}c' if sinopsis else 'sin desc'
        else:
            work_key, isbn_ol = buscar_work_key(title, author)
            time.sleep(PAUSA)
            if work_key:
                sinopsis, _ = desc_desde_work_key(work_key)
                time.sleep(PAUSA)
            if isbn_ol:
                isbn_final = isbn_ol
                isbn_recuperados += 1
            etiqueta = f'título→work: {len(sinopsis)}c' if sinopsis else 'sin desc'
            if isbn_ol:
                etiqueta += f' + ISBN({isbn_ol})'

        print(etiqueta)
        resultados[title] = {'sinopsis': sinopsis, 'isbn': isbn_final}
        if sinopsis:
            con_sinopsis += 1

        procesados += 1

        if procesados % GUARDADO_CADA == 0:
            guardar_sinopsis(resultados)
            pct = len(resultados) / total * 100
            print(f'\n── Guardado: {len(resultados)} ({pct:.1f}%), '
                  f'{con_sinopsis} sinopsis, {isbn_recuperados} ISBN nuevos ──\n')

    guardar_sinopsis(resultados)
    total_con  = sum(1 for d in resultados.values() if d['sinopsis'])
    total_isbn = sum(1 for d in resultados.values() if d['isbn'])
    print(f'\nFinalizado.')
    print(f'  Entradas totales   : {len(resultados)}')
    print(f'  Con sinopsis       : {total_con}')
    print(f'  Con ISBN           : {total_isbn}')
    print(f'  ISBN recuperados   : {isbn_recuperados}')
    print(f'  Sin sinopsis       : {len(resultados) - total_con}')


if __name__ == '__main__':
    main()
