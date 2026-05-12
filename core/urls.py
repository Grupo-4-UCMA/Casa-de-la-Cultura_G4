from django.contrib import admin
from django.urls import path
from catalogo.views import buscador_catalogo, login_view, logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='login'),
    path('catalogo/', buscador_catalogo, name='buscador'),
    path('logout/', logout_view, name='logout'),
]