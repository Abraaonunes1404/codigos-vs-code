from django.contrib import admin
from django.urls import path
from core.views import (
    api_comparar_produto, api_comparar_lista_compras, 
    tela_home_cestia, tela_cesta_compras, tela_ranking_resultados, 
    tela_mapa_rota, api_scannear_codigo_barra, tela_scanner_camera,
    api_limpar_cesta, tela_cesta_vazia, api_verificar_alertas_preco,
    tela_atualizar_preco_lojista, api_salvar_preco_rapido,
    api_remover_produto_cesta, api_alterar_quantidade_cesta,
    api_sugestoes_pesquisa
)

urlpatterns = [
    path('api/sugestoes/', api_sugestoes_pesquisa, name='api_sugestoes'),
    path('', tela_home_cestia, name='home'),
    path('cesta/', tela_cesta_compras, name='cesta'),
    path('cesta-vazia/', tela_cesta_vazia, name='cesta_vazia'),
    path('resultado-cestia/', tela_ranking_resultados, name='ranking_visual'),
    path('rota-cestia/', tela_mapa_rota, name='mapa_visual'),
    path('scanner-cestia/', tela_scanner_camera, name='scanner_visual'),
    path('api/verificar-alertas/', api_verificar_alertas_preco, name='verificar_alertas'),
    path('limpar-cesta/', api_limpar_cesta, name='limpar_cesta'),
    path('api/scan/', api_scannear_codigo_barra, name='api_scan'),
    path('admin/', admin.site.urls),
    path('api/comparar/', api_comparar_produto, name='api_comparar'),
    path('api/comparar-lista/', api_comparar_lista_compras, name='api_comparar_lista'),
    
    # ROTA DE QUANTIDADES REATIVAS CONECTADA AO BACKEND:
    path('cesta/alterar/<int:produto_id>/<str:acao>/', api_alterar_quantidade_cesta, name='alterar_quantidade_cesta'),
    
    # ROTA DE REMOÇÃO DO ITEM DA CESTA:
    path('cesta/remover/<int:produto_id>/', api_remover_produto_cesta, name='remover_produto_cesta'),
    
    # NOVAS ROTAS DO PAINEL DO LOJISTA:
    path('gerente-precos/', tela_atualizar_preco_lojista, name='atualizar_preco_lojista'),
    path('gerente-precos/salvar/', api_salvar_preco_rapido, name='api_salvar_preco'),
]

