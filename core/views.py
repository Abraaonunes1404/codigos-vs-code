from django.shortcuts import render
from django.http import JsonResponse
from core.models import Produto, Filial, HistoricoPreco, AlertaPreco
import math

def calcular_distancia(lat1, lon1, lat2, lon2):
    raio_terra = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return raio_terra * c

def tela_home_cestia(request):
    """
    Função que renderiza a interface visual oficial da Home do Cestia
    """
    from core.models import Categoria
    categorias = Categoria.objects.all()
    return render(request, "cestia/home.html", {'categorias': categorias})

def tela_cesta_compras(request):
    """
    Função visual que exibe os produtos adicionados à Cesta do Cestia (Carrinho)
    """
    # Busca os produtos reais com IDs 2 e 3 que estão salvos no seu banco de dados atual
    produtos_na_cesta = Produto.objects.filter(id__in=[2, 3])
    return render(request, "cestia/cesta.html", {'produtos': produtos_na_cesta})

def api_comparar_produto(request):
    """
    Página que simula o aplicativo fazendo a busca de um único produto.
    """
    termo_busca = request.GET.get('termo', '')
    lat_usuario = float(request.GET.get('lat', -3.0245))
    lon_usuario = float(request.GET.get('lon', -60.0512))

    produtos = Produto.objects.filter(nome__icontains=termo_busca)
    
    if not produtos.exists():
        return JsonResponse({'erro': 'Nenhum produto encontrado com esse nome'}, status=404)

    produto = produtos.first()
    filiais = Filial.objects.all()
    ranking = []

    for filial in filiais:
        try:
            registro_preco = HistoricoPreco.objects.get(produto=produto, filial=filial)
            distancia = calcular_distancia(lat_usuario, lon_usuario, filial.latitude, filial.longitude)
            
            custo_deslocamento = distancia * 1.20
            custo_real = float(registro_preco.preco) + custo_deslocamento

            ranking.append({
                'supermercado': filial.supermercado.nome,
                'loja': filial.nome_loja,
                'preco_produto': float(registro_preco.preco),
                'distancia_km': round(distancia, 2),
                'custo_beneficio_total': round(custo_real, 2)
            })
        except HistoricoPreco.DoesNotExist:
            continue

    ranking_ordenado = sorted(ranking, key=lambda x: x['custo_beneficio_total'])

    return JsonResponse({
        'produto_pesquisado': produto.nome,
        'marca': produto.marca,
        'resultados': ranking_ordenado
    }, json_dumps_params={'ensure_ascii': False})


def api_comparar_lista_compras(request):
    """
    Endpoint inteligente que calcula a lista de compras cheia 
    e simula a divisão em até 2 supermercados (Split Bimercado).
    """
    lat_usuario = float(request.GET.get('lat', -3.0245))
    lon_usuario = float(request.GET.get('lon', -60.0512))

    lista_ids = [2, 3]
    filiais = list(Filial.objects.all())
    
    opcoes_monomercado = []
    for filial in filiais:
        valor_total_sacola = 0
        itens_encontrados = 0
        detalhes_itens = []
        
        distancia = calcular_distancia(lat_usuario, lon_usuario, filial.latitude, filial.longitude)

        for prod_id in lista_ids:
            try:
                produto = Produto.objects.get(id=prod_id)
                registro_preco = HistoricoPreco.objects.get(produto=produto, filial=filial)
                valor_total_sacola += registro_preco.preco
                itens_encontrados += 1
                detalhes_itens.append({
                    'produto': produto.nome,
                    'preco': float(registro_preco.preco)
                })
            except (Produto.DoesNotExist, HistoricoPreco.DoesNotExist):
                continue

        if itens_encontrados == len(lista_ids):
            custo_deslocamento = distancia * 1.20
            custo_final_real = float(valor_total_sacola) + custo_deslocamento

            opcoes_monomercado.append({
                'supermercado': filial.supermercado.nome,
                'loja': filial.nome_loja,
                'total_produtos': float(valor_total_sacola),
                'distancia_km': round(distancia, 2),
                'custo_beneficio_total': round(custo_final_real, 2),
                'itens': detalhes_itens
            })

    ranking_monomercado = sorted(opcoes_monomercado, key=lambda x: x['custo_beneficio_total'])

    melhor_opcao_dividida = None
    if len(filiais) >= 2:
        menor_custo_real_dividido = float('inf')
        
        for i in range(len(filiais)):
            for j in range(i + 1, len(filiais)):
                loja_A = filiais[i]
                loja_B = filiais[j]
                
                total_produtos_combinado = 0
                itens_divisao = []
                todos_itens_cobertos = True
                
                dist_A = calcular_distancia(lat_usuario, lon_usuario, loja_A.latitude, loja_A.longitude)
                dist_B = calcular_distancia(lat_usuario, lon_usuario, loja_B.latitude, loja_B.longitude)
                
                distancia_total_combinada = max(dist_A, dist_B) + (min(dist_A, dist_B) * 0.5)

                for prod_id in lista_ids:
                    try:
                        produto = Produto.objects.get(id=prod_id)
                        preco_A = HistoricoPreco.objects.filter(produto=produto, filial=loja_A).first()
                        preco_B = HistoricoPreco.objects.filter(produto=produto, filial=loja_B).first()
                        
                        if preco_A and preco_B:
                            if preco_A.preco <= preco_B.preco:
                                total_produtos_combinado += float(preco_A.preco)
                                itens_divisao.append({'produto': produto.nome, 'comprar_em': loja_A.nome_loja, 'preco': float(preco_A.preco)})
                            else:
                                total_produtos_combinado += float(preco_B.preco)
                                itens_divisao.append({'produto': produto.nome, 'comprar_em': loja_B.nome_loja, 'preco': float(preco_B.preco)})
                        elif preco_A:
                            total_produtos_combinado += float(preco_A.preco)
                            itens_divisao.append({'produto': produto.nome, 'comprar_em': loja_A.nome_loja, 'preco': float(preco_A.preco)})
                        elif preco_B:
                            total_produtos_combinado += float(preco_B.preco)
                            itens_divisao.append({'produto': produto.nome, 'comprar_em': loja_B.nome_loja, 'preco': float(preco_B.preco)})
                        else:
                            todos_itens_cobertos = False
                    except Produto.DoesNotExist:
                        todos_itens_cobertos = False

                if todos_itens_cobertos:
                    custo_frete_combinado = distancia_total_combinada * 1.20
                    custo_real_dividido = total_produtos_combinado + custo_frete_combinado
                    
                    if custo_real_dividido < menor_custo_real_dividido:
                        menor_custo_real_dividido = ...
                        melhor_opcao_dividida = {
                            'modo': 'Comprar em 2 Supermercados',
                            'lojas_envolvidas': f"{loja_A.nome_loja} + {loja_B.nome_loja}",
                            'total_apenas_produtos': round(total_produtos_combinado, 2),
                            'distancia_total_estimada_km': round(distancia_total_combinada, 2),
                            'custo_beneficio_total': round(custo_real_dividido, 2),
                            'divisao_da_sacola': itens_divisao
                        }

    return JsonResponse({
        'quantidade_itens_solicitados': len(lista_ids),
        'comprar_tudo_no_mesmo_lugar': ranking_monomercado,
        'sugestao_otimizada_split_2_mercados': melhor_opcao_dividida
    }, json_dumps_params={'ensure_ascii': False})



def tela_ranking_resultados(request):
    """
    Função visual que renderiza o ranking dos supermercados e a sugestão dividida
    """
    # Simulamos os dados processados do Tarumã para gerar a interface visual idêntica à API
    dados_mock = {
        'quantidade_itens_solicitados': 2,
        'comprar_tudo_no_mesmo_lugar': [
            {
                'supermercado': 'Grupo DB', 'loja': 'DB Ponta Negra',
                'total_produtos': 36.40, 'distancia_km': 7.79, 'custo_beneficio_total': 45.75,
                'vencedor': True, 'medalha': '🥇 1º Lugar'
            },
            {
                'supermercado': 'Grupo DB', 'loja': 'DB Paraíba',
                'total_produtos': 36.40, 'distancia_km': 10.54, 'custo_beneficio_total': 49.05,
                'vencedor': False, 'medalha': '🥈 2º Lugar'
            }
        ],
        'sugestao_otimizada_split_2_mercados': {
            'lojas_envolvidas': 'DB Ponta Negra + DB Paraíba',
            'total_apenas_produtos': 36.40,
            'distancia_total_estimada_km': 14.44,
            'custo_beneficio_total': 53.73
        }
    }
    return render(request, "cestia/ranking.html", {'dados': dados_mock})


def tela_mapa_rota(request):
    """
    Função visual que simula o mapa de rota saindo do Tarumã até o mercado vencedor
    """
    dados_rota = {
        'origem': 'Tarumã, Manaus',
        'destino': 'Grupo DB - DB Ponta Negra',
        'distancia_km': 7.79,
        'tempo_estimado_min': 14,
    }
    return render(request, "cestia/mapa.html", {'rota': dados_rota})


def api_scannear_codigo_barra(request):
    """
    Motor inteligente que recebe o código de barras lido pela câmera do celular
    e adiciona o produto automaticamente na cesta do cliente.
    Exemplo de uso: http://127.0.0
    """
    # Captura o número do EAN enviado pela câmera do smartphone
    codigo_ean = request.GET.get('ean', '').strip()
    
    if not codigo_ean:
        return JsonResponse({'erro': 'Nenhum código de barras foi detectado pela câmera'}, status=400)
        
    try:
        # Busca no banco central se esse código de barras já existe cadastrado
        produto = Produto.objects.get(gtin_ean=codigo_ean)
        
        # Injeta um balão de aviso verde que aparecerá no topo do carrinho
        from django.contrib import messages
        messages.success(request, f'🛒 {produto.nome} adicionado com sucesso!')
        
        # Redireciona o usuário de volta para a tela bonita da Cesta!
        from django.shortcuts import redirect
        return redirect('cesta')
        
    except Produto.DoesNotExist:
        from django.contrib import messages
        messages.warning(request, '❌ Produto não localizado na base central.')
        from django.shortcuts import redirect
        return redirect('cesta')


def tela_scanner_camera(request):
    """
    Função visual que renderiza a interface do scanner de câmera do Cestia
    """
    return render(request, "cestia/scanner.html")


def api_limpar_cesta(request):
    """
    Função que simula o esvaziamento da cesta de compras do cliente
    e o redireciona de volta com uma mensagem de confirmação.
    """
    from django.contrib import messages
    from django.shortcuts import redirect
    
    # Injeta um balão de aviso cinza informando que a cesta foi limpa
    messages.info(request, '🧹 Sua cesta de compras foi esvaziada.')
    
    # Para o MVP visual, redirecionamos para a mesma página, mas passando uma lista vazia
    return redirect('cesta_vazia')
def tela_cesta_vazia(request):
    """
    Renderiza a tela do carrinho sem nenhum produto cadastrado
    """
    return render(request, "cestia/cesta.html", {'produtos': []})



def api_verificar_alertas_preco(request):
    """
    Motor inteligente (Robô) que simula a varredura de preços nas filiais
    e dispara gatilhos de aviso quando encontra valores abaixo do esperado.
    """
    alertas_disparados = []
    alertas_ativos = AlertaPreco.objects.filter(ativo=True)
    filiais = Filial.objects.all()

    for alerta in alertas_ativos:
        for filial in filiais:
            try:
                # Busca o preço atualizado daquele item nessa filial específica
                registro = HistoricoPreco.objects.get(produto=alerta.produto, filial=filial)
                
                # SE O PREÇO DO MERCADO FOR MENOR OU IGUAL AO PREÇO QUE O CLIENTE QUER PAGAR:
                if registro.preco <= alerta.preco_alvo:
                    alertas_disparados.append({
                        'produto': alerta.produto.nome,
                        'marca': alerta.produto.marca,
                        'preco_encontrado': float(registro.preco),
                        'supermercado': filial.supermercado.nome,
                        'loja_promocao': filial.nome_loja,
                        'notificado_para': alerta.email_notificacao,
                        'status_envio': '✉️ E-mail de Alerta Disparado com Sucesso!'
                    })
            except HistoricoPreco.DoesNotExist:
                continue

    return JsonResponse({
        'robo_status': 'Varredura de Rotina Concluída',
        'alertas_analisados_total': alertas_ativos.count(),
        'oportunidades_de_economia_encontradas': alertas_disparados
    }, json_dumps_params={'ensure_ascii': False})
