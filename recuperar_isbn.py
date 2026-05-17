"""
Recupera ISBNs para los libros que tienen isbn = N/A en books_with_genre.csv.
Consulta Open Library search.json (1 petición por libro).
Guarda resultados en data/isbn_recuperados.csv (book_id, title, isbn).

Uso:
    python recuperar_isbn.py

Reanuda automáticamente si se interrumpe.
"""

import os
import time
import urllib.request
import urllib.parse
import json
import csv

BOOKS_CSV   = 'data/books_with_genre.csv'
AUTHORS_CSV = 'data/book_authors_extended.csv'
OUTPUT_CSV  = 'data/isbn_recuperados.csv'
PAUSA       = 0.6
GUARDADO_CADA = 50


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


def buscar_isbn(title, author=''):
    params = {'title': title, 'limit': '1', 'fields': 'key,isbn,title'}
    if author:
        params['author'] = author
    url = 'https://openlibrary.org/search.json?' + urllib.parse.urlencode(params)
    data = get_url(url)
    if not data:
        return ''
    try:
        docs = json.loads(data).get('docs', [])
    except Exception:
        return ''
    if not docs:
        return ''
    isbn_lista = docs[0].get('isbn', [])
    if not isbn_lista:
        return ''
    isbn13 = [x for x in isbn_lista if len(x) == 13]
    return isbn13[0] if isbn13 else isbn_lista[0]


def isbn_valido(isbn):
    return bool(isbn) and isbn.upper() not in ('', 'N/A', 'NA', 'NONE')


def cargar_libros_sin_isbn():
    autores = {}
    with open(AUTHORS_CSV, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            autores[row['book_id'].strip()] = row.get('author', '').strip()

    libros = []
    with open(BOOKS_CSV, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            isbn = row.get('isbn', '').strip()
            if not isbn_valido(isbn):
                bid = row['book_id'].strip()
                libros.append({
                    'book_id': bid,
                    'title':   row.get('title', '').strip(),
                    'author':  autores.get(bid, ''),
                })
    return libros


def cargar_ya_procesados():
    procesados = {}
    if not os.path.exists(OUTPUT_CSV):
        return procesados
    with open(OUTPUT_CSV, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            bid = row.get('book_id', '').strip()
            if bid:
                procesados[bid] = row.get('isbn', '').strip()
    return procesados


def guardar(resultados):
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['book_id', 'title', 'isbn'])
        writer.writeheader()
        for bid, (title, isbn) in resultados.items():
            writer.writerow({'book_id': bid, 'title': title, 'isbn': isbn})


def main():
    print('Cargando libros sin ISBN...')
    libros = cargar_libros_sin_isbn()
    total  = len(libros)
    print(f'  {total} libros sin ISBN')

    ya_hechos  = cargar_ya_procesados()
    resultados = {bid: (title_isbn[0] if isinstance(title_isbn, tuple) else '', title_isbn)
                  for bid, title_isbn in ya_hechos.items()}

    # Reconstruir resultados correctamente desde el CSV existente
    resultados = {}
    if os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                bid = row.get('book_id', '').strip()
                if bid:
                    resultados[bid] = (row.get('title', ''), row.get('isbn', ''))

    pendientes = [l for l in libros if l['book_id'] not in resultados]
    print(f'  {len(resultados)} ya procesados, {len(pendientes)} pendientes\n')

    recuperados  = 0
    procesados   = 0
    base_offset  = len(resultados)

    for i, libro in enumerate(pendientes, 1):
        bid    = libro['book_id']
        title  = libro['title']
        author = libro['author']

        pos = base_offset + i
        print(f'[{pos}/{total}] "{title[:60]}" — ', end='', flush=True)

        isbn = buscar_isbn(title, author)

        if isbn:
            recuperados += 1
            print(f'ISBN: {isbn}')
        else:
            print('no encontrado')

        resultados[bid] = (title, isbn)
        procesados += 1
        time.sleep(PAUSA)

        if procesados % GUARDADO_CADA == 0:
            guardar(resultados)
            pct = len(resultados) / total * 100
            print(f'\n── Guardado: {len(resultados)}/{total} ({pct:.1f}%), {recuperados} ISBNs nuevos ──\n')

    guardar(resultados)
    print(f'\nFinalizado.')
    print(f'  Libros sin ISBN procesados : {len(resultados)}')
    print(f'  ISBNs recuperados          : {recuperados}')
    print(f'  Sin ISBN en Open Library   : {len(resultados) - recuperados}')
    print(f'  Fichero: {OUTPUT_CSV}')


if __name__ == '__main__':
    main()
