from django.contrib import admin
from django.urls import path
from core.views import (
    tela_produto_nao_encontrado,
    tela_cadastro_produto_cliente,
    tela_home_cestia,
    tela_cesta_compras,
    tela_ranking_resultados,
    tela_mapa_rota,
    api_scannear_codigo_barra,
    tela_scanner_camera,
    api_limpar_cesta,
    tela_cesta_vazia,
    api_verificar_alertas_preco,
    api_remover_produto_cesta,
    api_alterar_quantidade_cesta,
    api_sugestoes_pesquisa,
    login_lojista,
    tela_atualizar_preco_lojista,
    api_salvar_preco_rapido
)

urlpatterns = [
    # ROTA DE AUTOCOMPLETAR FLUTUANTE DE MARCAS
    path('api/sugestoes/', api_sugestoes_pesquisa, name='api_sugestoes'),
    
    # ROTAS DO CONSUMIDOR (TELA INICIAL, CESTA E RESULTADOS)
    path('', tela_home_cestia, name='home'),
    path('cesta/', tela_cesta_compras, name='cesta'),
    path('cesta-vazia/', tela_cesta_vazia, name='cesta_vazia'),
    path('resultado-cestia/', tela_ranking_resultados, name='ranking_visual'),
    path('rota-cestia/', tela_mapa_rota, name='mapa_visual'),
    path('scanner-cestia/', tela_scanner_camera, name='scanner_visual'),
    path(
        'produto-nao-encontrado/',
        tela_produto_nao_encontrado,
        name='produto_nao_encontrado'
    ),

    path(
        'cadastrar-produto/',
        tela_cadastro_produto_cliente,
        name='cadastro_produto_cliente'
    ),
    path('api/scan/', api_scannear_codigo_barra, name='api_scan'),
    path('limpar-cesta/', api_limpar_cesta, name='limpar_cesta'),
    
    # SISTEMA DE QUANTIDADES E RECOMENDAÇÕES REATIVAS
    path('cesta/alterar/<int:produto_id>/<str:acao>/', api_alterar_quantidade_cesta, name='alterar_quantidade_cesta'),
    path('cesta/remover/<int:produto_id>/', api_remover_produto_cesta, name='remover_produto_cesta'),
    path('api/verificar-alertas/', api_verificar_alertas_preco, name='verificar_alertas'),
    
    # NOVO MOTOR SEGURO DE AUTENTICAÇÃO E CARGA EM MASSA DO LOJISTA
    path('login/', login_lojista, name='login_lojista'),
    path('gerente-precos/', tela_atualizar_preco_lojista, name='atualizar_preco_lojista'),
    path('gerente-precos/salvar/', api_salvar_preco_rapido, name='api_salvar_preco'),
    
    # BACKEND ADMINISTRATIVO DO DJANGO
    path('admin/', admin.site.urls),
]
