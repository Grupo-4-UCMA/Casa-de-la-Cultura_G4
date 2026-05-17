from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("buscador/", views.buscador_catalogo, name="buscador"),
    path("valorar/<int:book_id>/", views.valorar_libro, name="valorar_libro"),
]