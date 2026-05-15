from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("catalogo/", views.buscador_catalogo, name="buscador"),
    path("logout/", views.logout_view, name="logout"),
]