from django.contrib import admin
from django.urls import path
from catalogo import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),
    path('catalogo/', views.buscador_catalogo, name='buscador'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('api/ia/', views.resumen_ia_view, name='resumen_ia'),
]