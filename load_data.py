import os
import csv
import django
import pandas as pd

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "casa_cultura.settings")
django.setup()

from app.models import Book, Author, Copy, LibraryUser, Rating

def chunked_bulk_create(model, objects, batch_size=50000):
    for i in range(0, len(objects), batch_size):
        model.objects.bulk_create(objects[i:i+batch_size], ignore_conflicts=True)
        print(f"   -> Insertados {min(i+batch_size, len(objects))} registros...")

Rating.objects.all().delete()
Copy.objects.all().delete()
Book.authors.through.objects.all().delete()
Author.objects.all().delete()
Book.objects.all().delete()
LibraryUser.objects.all().delete()

print("\nCargando usuarios...")
users_batch = []
with open("data/users_clean.csv", newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        try: users_batch.append(LibraryUser(user_id=int(row.get("user_id", row.get("id")))))
        except: pass
chunked_bulk_create(LibraryUser, users_batch)

print("\nCargando libros...")
books_batch = []
with open("data/books_with_genre.csv", newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        try: books_batch.append(Book(book_id=int(row.get("book_id", row.get("id"))), title=row.get("title", "")))
        except: pass
chunked_bulk_create(Book, books_batch)

print("\nCargando autores...")
authors_set = set()
book_author_data = []
with open("data/book_authors_extended.csv", newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        try:
            author_name = row["author"].strip()
            book_id = int(row.get("book_id", row.get("id")))
            authors_set.add(author_name)
            book_author_data.append((book_id, author_name))
        except: pass
chunked_bulk_create(Author, [Author(name=n) for n in authors_set])

authors_dict = {a.name: a.id for a in Author.objects.all()}
books_dict = {b.book_id: b.id for b in Book.objects.all()}

print("\nVinculando libros y autores...")
BookAuthor = Book.authors.through
m2m_batch = [BookAuthor(book_id=books_dict[b_id], author_id=authors_dict[a_name]) 
             for b_id, a_name in book_author_data if b_id in books_dict and a_name in authors_dict]
chunked_bulk_create(BookAuthor, m2m_batch)

print("\nCargando copias...")
copies_batch = []
with open("data/copies_clean.csv", newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        try:
            b_id = int(row.get("book_id", row.get("id_libro")))
            if b_id in books_dict:
                copies_batch.append(Copy(copy_id=int(row.get("copy_id", row.get("id"))), book_id=books_dict[b_id]))
        except: pass
chunked_bulk_create(Copy, copies_batch)

print("\nCargando valoraciones en SQLite (sin límites)...")
users_dict = {u.user_id: u.id for u in LibraryUser.objects.all()}
copies_dict = {c.copy_id: c.id for c in Copy.objects.all()}

ratings_batch = []
with open("data/ratings.csv", newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        try:
            u_id = int(row.get("user_id", row.get("id")))
            c_id = int(row.get("copy_id", row.get("id")))
            if u_id in users_dict and c_id in copies_dict:
                ratings_batch.append(Rating(user_id=users_dict[u_id], copy_id=copies_dict[c_id], rating=int(row["rating"])))
        except: pass
chunked_bulk_create(Rating, ratings_batch)

print("\n[PRE-PROCESADO] Aprovechando la libertad del profesor...")
print("[PRE-PROCESADO] Calculando medias exactas de millones de ratings al vuelo...")
try:
    df_rat = pd.read_csv("data/ratings.csv", encoding="utf-8-sig")
    df_cop = pd.read_csv("data/copies_clean.csv", encoding="utf-8-sig")
    
    col_r_cop = 'copy_id' if 'copy_id' in df_rat.columns else 'id'
    col_c_cop = 'copy_id' if 'copy_id' in df_cop.columns else 'id'
    col_c_bok = 'book_id' if 'book_id' in df_cop.columns else 'id_libro'
    
    df_rat[col_r_cop] = pd.to_numeric(df_rat[col_r_cop], errors='coerce').fillna(0).astype(int)
    df_cop[col_c_cop] = pd.to_numeric(df_cop[col_c_cop], errors='coerce').fillna(0).astype(int)
    
    df_merge = pd.merge(df_rat, df_cop, left_on=col_r_cop, right_on=col_c_cop)
    df_merge[col_c_bok] = pd.to_numeric(df_merge[col_c_bok], errors='coerce').fillna(0).astype(int)
    
    df_agrupado = df_merge.groupby(col_c_bok).agg(votos=("rating", "count"), nota_media=("rating", "mean")).reset_index()
    df_agrupado["nota_media"] = df_agrupado["nota_media"].round(1)
    df_agrupado.rename(columns={col_c_bok: 'book_id'}, inplace=True)
    
    df_agrupado.to_csv("data/votos_precalculados.csv", index=False, encoding="utf-8-sig")
    print("[PRE-PROCESADO] ¡'votos_precalculados.csv' creado! El catálogo cargará en 0.01 segundos.")
except Exception as e:
    print(f"[ERROR] No se pudo pre-calcular las medias: {e}")

print(f"\n¡ÉXITO TOTAL!: {LibraryUser.objects.count()} usuarios, {Book.objects.count()} libros, {Copy.objects.count()} copias, {Rating.objects.count()} ratings guardados.")