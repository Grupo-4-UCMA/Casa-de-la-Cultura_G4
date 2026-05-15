from django.shortcuts import render, redirect
from django.db.models import Count
from .models import Book, LibraryUser


def login_view(request):
    error = None

    if request.method == "POST":
        user_id = request.POST.get("user_id")

        if LibraryUser.objects.filter(user_id=user_id).exists():
            request.session["user_id"] = user_id
            return redirect("buscador")

        error = "El identificador de usuario no existe."

    return render(request, "catalogo/login.html", {"error": error})


def logout_view(request):
    request.session.flush()
    return redirect("login")


def buscador_catalogo(request):
    query = request.GET.get("q", "")
    user_active = request.session.get("user_id")

    libros = Book.objects.prefetch_related("authors").all()

    if query:
        libros = libros.filter(title__icontains=query)

    libros = libros[:20]

    libros_context = []
    for libro in libros:
        autores = ", ".join([a.name for a in libro.authors.all()])
        libros_context.append({
            "title": libro.title,
            "authors": autores or "Autor desconocido",
        })

    top_libros = (
        Book.objects
        .annotate(num_copias=Count("copies"))
        .order_by("-num_copias")[:5]
    )

    top_context = []
    max_copias = top_libros[0].num_copias if top_libros else 1

    for libro in top_libros:
        autores = ", ".join([a.name for a in libro.authors.all()])
        top_context.append({
            "title": libro.title,
            "authors": autores or "Autor desconocido",
            "ratings": libro.num_copias,
            "pct": int((libro.num_copias / max_copias) * 100),
        })

    recomendaciones = []

    return render(request, "catalogo/lista_libros.html", {
        "libros": libros_context,
        "top_libros": top_context,
        "recomendaciones": recomendaciones,
        "query": query,
        "user_active": user_active,
    })