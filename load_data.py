import os
import csv
import django

# Configuración Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "casa_cultura.settings")
django.setup()

from app.models import Book, Author, Copy, LibraryUser, Rating


print("Iniciando carga de datos...")


# ==========================
# USUARIOS
# ==========================
print("Cargando usuarios...")

with open("data/users_clean.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:
        try:
            LibraryUser.objects.update_or_create(
                user_id=int(row["user_id"])
            )
        except Exception:
            continue

print(f"Usuarios cargados: {LibraryUser.objects.count()}")


# ==========================
# LIBROS
# ==========================
print("Cargando libros...")

with open("data/books_with_genre.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:
        try:
            Book.objects.update_or_create(
                book_id=int(row["book_id"]),
                defaults={
                    "title": row["title"],
                }
            )
        except Exception:
            continue

print(f"Libros cargados: {Book.objects.count()}")


# ==========================
# AUTORES
# ==========================
print("Cargando autores...")

with open("data/book_authors_extended.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:
        try:
            book = Book.objects.get(
                book_id=int(row["book_id"])
            )

            author, _ = Author.objects.get_or_create(
                name=row["author"]
            )

            book.authors.add(author)

        except Exception:
            continue

print(f"Autores cargados: {Author.objects.count()}")


# ==========================
# COPIAS
# ==========================
print("Cargando copias...")

with open("data/copies_clean.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:
        try:
            book = Book.objects.get(
                book_id=int(row["book_id"])
            )

            Copy.objects.update_or_create(
                copy_id=int(row["copy_id"]),
                defaults={
                    "book": book
                }
            )

        except Exception:
            continue

print(f"Copias cargadas: {Copy.objects.count()}")


# ==========================
# RATINGS (SOLO 50.000)
# ==========================
print("Cargando ratings (muestra de 50.000)...")

# limpiar ratings anteriores
Rating.objects.all().delete()

ratings_batch = []

creados = 0
omitidos = 0
LIMITE_RATINGS = 50000

with open("data/ratings.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for i, row in enumerate(reader, start=1):

        # límite para no cargar millones
        if i > LIMITE_RATINGS:
            break

        try:
            user_id = int(row["user_id"])
            copy_id = int(row["copy_id"])
            rating_value = int(row["rating"])

            user = LibraryUser.objects.filter(
                user_id=user_id
            ).first()

            copy = Copy.objects.filter(
                copy_id=copy_id
            ).first()

            if not user or not copy:
                omitidos += 1
                continue

            ratings_batch.append(
                Rating(
                    user=user,
                    copy=copy,
                    rating=rating_value
                )
            )

            # Guardado por lotes
            if len(ratings_batch) >= 5000:
                Rating.objects.bulk_create(
                    ratings_batch,
                    ignore_conflicts=True
                )

                creados += len(ratings_batch)
                ratings_batch = []

                print(
                    f"Ratings procesados: {i} "
                    f"| creados: {creados} "
                    f"| omitidos: {omitidos}"
                )

        except Exception:
            omitidos += 1
            continue

# guardar últimos pendientes
if ratings_batch:
    Rating.objects.bulk_create(
        ratings_batch,
        ignore_conflicts=True
    )

    creados += len(ratings_batch)

print("Carga de ratings terminada.")
print(f"Ratings creados: {creados}")
print(f"Ratings omitidos: {omitidos}")
print(f"Ratings en SQLite: {Rating.objects.count()}")


print("Datos cargados correctamente.")