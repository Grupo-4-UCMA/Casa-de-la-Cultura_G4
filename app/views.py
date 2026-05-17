from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import Book, Copy, LibraryUser, Rating


def _format_authors(book):
    autores = ", ".join([a.name for a in book.authors.all()])
    return autores or "Autor desconocido"


def login_view(request):
    error = None

    if request.method == "POST":
        user_id = request.POST.get("user_id", "").strip()

        if not user_id.isdigit():
            error = "Introduce un identificador de usuario válido."
        else:
            user, _created = LibraryUser.objects.get_or_create(
                user_id=int(user_id)
            )
            request.session["user_id"] = user.user_id
            return redirect("buscador")

    return render(request, "login.html", {"error": error})


def logout_view(request):
    request.session.flush()
    return redirect("login")


def valorar_libro(request, book_id):
    user_id = request.session.get("user_id")

    if not user_id:
        messages.error(request, "Debes identificarte para guardar valoraciones.")
        return redirect("login")

    if request.method == "POST":
        rating_value = request.POST.get("rating")

        if rating_value not in ["1", "2", "3", "4", "5"]:
            messages.error(request, "La valoración debe estar entre 1 y 5.")
            return redirect("buscador")

        user = get_object_or_404(LibraryUser, user_id=user_id)
        book = get_object_or_404(Book, book_id=book_id)

        copy = book.copies.first()

        if copy is None:
            copy = Copy.objects.create(
                copy_id=Copy.objects.count() + 1,
                book=book
            )

        Rating.objects.update_or_create(
            user=user,
            copy=copy,
            defaults={"rating": int(rating_value)}
        )

        messages.success(request, "Valoración guardada correctamente en SQLite.")

    return redirect("buscador")


def buscador_catalogo(request):
    query = request.GET.get("q", "").strip()
    user_active = request.session.get("user_id")

    user = None
    if user_active:
        user = LibraryUser.objects.filter(user_id=user_active).first()

    libros = Book.objects.prefetch_related("authors", "copies").all()

    if query:
        libros = libros.filter(
            Q(title__icontains=query) |
            Q(authors__name__icontains=query) |
            Q(language_code__icontains=query)
        ).distinct()

    libros = libros[:20]

    libros_context = []

    for libro in libros:
        user_rating = None

        if user:
            rating_obj = Rating.objects.filter(
                user=user,
                copy__book=libro
            ).first()

            if rating_obj:
                user_rating = rating_obj.rating

        libros_context.append({
            "book_id": libro.book_id,
            "title": libro.title,
            "authors": _format_authors(libro),
            "user_rating": user_rating,
            "copies": libro.copies.count(),
        })

    top_libros = (
        Book.objects
        .prefetch_related("authors")
        .annotate(
            avg_rating=Avg("copies__ratings__rating"),
            num_ratings=Count("copies__ratings")
        )
        .order_by("-avg_rating", "-num_ratings", "title")[:5]
    )

    max_ratings = max(
        [libro.num_ratings for libro in top_libros],
        default=1
    )

    if max_ratings == 0:
        max_ratings = 1

    top_context = []

    for libro in top_libros:
        top_context.append({
            "title": libro.title,
            "authors": _format_authors(libro),
            "ratings": libro.num_ratings,
            "avg": round(libro.avg_rating or 0, 2),
            "pct": int((libro.num_ratings / max_ratings) * 100),
        })

    recomendaciones = obtener_recomendaciones(user)

    return render(request, "lista_libros.html", {
        "libros": libros_context,
        "top_libros": top_context,
        "recomendaciones": recomendaciones,
        "query": query,
        "user_active": user_active,
    })


def obtener_recomendaciones(user):
    if not user:
        libros = (
            Book.objects
            .prefetch_related("authors")
            .annotate(
                avg_rating=Avg("copies__ratings__rating"),
                num_ratings=Count("copies__ratings")
            )
            .order_by("-avg_rating", "-num_ratings", "title")[:5]
        )

        return [
            {
                "title": libro.title,
                "authors": _format_authors(libro),
            }
            for libro in libros
        ]

    libros_valorados = Rating.objects.filter(user=user).values_list(
        "copy__book_id",
        flat=True
    )

    generos_usuario = Book.objects.filter(
        book_id__in=libros_valorados
    ).values_list(
        "genres",
        flat=True
    )

    recomendaciones = (
        Book.objects
        .prefetch_related("authors")
        .filter(genres__in=generos_usuario)
        .exclude(book_id__in=libros_valorados)
        .annotate(
            avg_rating=Avg("copies__ratings__rating"),
            num_ratings=Count("copies__ratings")
        )
        .order_by("-avg_rating", "-num_ratings", "title")
        .distinct()[:5]
    )

    if not recomendaciones:
        recomendaciones = (
            Book.objects
            .prefetch_related("authors")
            .exclude(book_id__in=libros_valorados)
            .annotate(
                avg_rating=Avg("copies__ratings__rating"),
                num_ratings=Count("copies__ratings")
            )
            .order_by("-avg_rating", "-num_ratings", "title")[:5]
        )

    return [
        {
            "title": libro.title,
            "authors": _format_authors(libro),
        }
        for libro in recomendaciones
    ]