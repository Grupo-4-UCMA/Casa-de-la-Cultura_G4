import csv
from app.models import Book, Author, Copy, LibraryUser

# Usuarios
with open("data/users_clean.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        LibraryUser.objects.update_or_create(
            user_id=row["user_id"]
        )


# Libros
with open("data/books_with_genre.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        Book.objects.update_or_create(
            book_id=row["book_id"],
            defaults={
                "title": row["title"],
            }
        )

# Autores
with open("data/book_authors_extended.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        book = Book.objects.get(book_id=row["book_id"])
        author, _ = Author.objects.get_or_create(name=row["author"])
        book.authors.add(author)

# Copias
with open("data/copies_clean.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        book = Book.objects.get(book_id=row["book_id"])
        Copy.objects.update_or_create(
            copy_id=row["copy_id"],
            defaults={"book": book}
        )

print("Datos cargados correctamente")