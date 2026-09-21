from django.contrib import admin
from django.urls import path
from core.views import api_comparar_produto, api_comparar_lista_compras, tela_home_cestia, tela_cesta_compras, tela_ranking_resultados, tela_mapa_rota

urlpatterns = [
    path('', tela_home_cestia, name='home'),
    path('cesta/', tela_cesta_compras, name='cesta'),
    path('resultado-cestia/', tela_ranking_resultados, name='ranking_visual'),
    # Nova rota para visualizar o mapa do trajeto:
    path('rota-cestia/', tela_mapa_rota, name='mapa_visual'),
    path('admin/', admin.site.urls),
    path('api/comparar/', api_comparar_produto, name='api_comparar'),
    path('api/comparar-lista/', api_comparar_lista_compras, name='api_comparar_lista'),
]
