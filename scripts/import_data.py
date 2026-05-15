import os
import sys
import django
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "casa_cultura.settings")
django.setup()

from catalog.models import Author, Genre, Book, Copy, LibraryUser


def clean_value(value):
    if pd.isna(value):
        return None
    return value


def import_books():
    print("Importando libros...")
    df = pd.read_csv("data/clean/books_with_genre.csv")

    for _, row in df.iterrows():
        genre_name = clean_value(row.get("genre"))

        book, _ = Book.objects.update_or_create(
            book_id=int(row["book_id"]),
            defaults={
                "title": clean_value(row.get("title")) or "",
                "original_title": clean_value(row.get("original_title")),
                "isbn": clean_value(row.get("isbn")),
                "publication_year": clean_value(row.get("original_publication_year")),
                "language_code": clean_value(row.get("language_code")),
                "image_url": clean_value(row.get("image_url")),
            },
        )

        if genre_name:
            genre, _ = Genre.objects.get_or_create(name=str(genre_name))
            book.genres.add(genre)

    print("Libros importados.")


def import_authors():
    print("Importando autores...")
    df = pd.read_csv("data/clean/book_authors_extended.csv")

    for _, row in df.iterrows():
        book_id = int(row["book_id"])
        author_name = clean_value(row.get("author"))

        if not author_name:
            continue

        try:
            book = Book.objects.get(book_id=book_id)
        except Book.DoesNotExist:
            continue

        author, _ = Author.objects.get_or_create(name=str(author_name))
        book.authors.add(author)

    print("Autores importados.")


def import_copies():
    print("Importando ejemplares...")
    df = pd.read_csv("data/clean/copies_clean.csv")

    for _, row in df.iterrows():
        try:
            book = Book.objects.get(book_id=int(row["book_id"]))
        except Book.DoesNotExist:
            continue

        Copy.objects.update_or_create(
            copy_id=int(row["copy_id"]),
            defaults={
                "book": book,
                "available": True,
            },
        )

    print("Ejemplares importados.")


def import_users():
    print("Importando usuarios...")
    df = pd.read_csv("data/clean/users_clean.csv")

    for _, row in df.iterrows():
        LibraryUser.objects.update_or_create(
            user_id=int(row["user_id"]),
            defaults={
                "comment": clean_value(row.get("comment")),
            },
        )

    print("Usuarios importados.")


def main():
    import_books()
    import_authors()
    import_copies()
    import_users()

    print("Importación completada.")
    print(f"Libros: {Book.objects.count()}")
    print(f"Autores: {Author.objects.count()}")
    print(f"Géneros: {Genre.objects.count()}")
    print(f"Ejemplares: {Copy.objects.count()}")
    print(f"Usuarios: {LibraryUser.objects.count()}")


if __name__ == "__main__":
    main()