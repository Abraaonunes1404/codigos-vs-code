from django.contrib import admin
from django.urls import path
from core.views import (
    api_comparar_produto, api_comparar_lista_compras, 
    tela_home_cestia, tela_cesta_compras, tela_ranking_resultados, 
    tela_mapa_rota, api_scannear_codigo_barra, tela_scanner_camera,
    api_limpar_cesta, tela_cesta_vazia
)

urlpatterns = [
    path('', tela_home_cestia, name='home'),
    path('cesta/', tela_cesta_compras, name='cesta'),
    path('cesta-vazia/', tela_cesta_vazia, name='cesta_vazia'),
    path('resultado-cestia/', tela_ranking_resultados, name='ranking_visual'),
    path('rota-cestia/', tela_mapa_rota, name='mapa_visual'),
    path('scanner-cestia/', tela_scanner_camera, name='scanner_visual'),
    
    # Novas rotas para limpar o carrinho:
    path('limpar-cesta/', api_limpar_cesta, name='limpar_cesta'),
    
    path('api/scan/', api_scannear_codigo_barra, name='api_scan'),
    path('admin/', admin.site.urls),
    path('api/comparar/', api_comparar_produto, name='api_comparar'),
    path('api/comparar-lista/', api_comparar_lista_compras, name='api_comparar_lista'),
]
