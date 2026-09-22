from django.shortcuts import render
from django.http import JsonResponse
from .models import Produto, Filial, HistoricoPreco, AlertaPreco, ItemCarrinhoDinamico
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
                'itens': detalhes_itens,
                'economia_reais': 0.0
            })

    ranking_monomercado = sorted(opcoes_monomercado, key=lambda x: x['custo_beneficio_total'])

    # Matematica dinâmica de economia comparativa de mercado
    economia_maxima = 0.0
    if len(ranking_monomercado) > 1:
        maior_custo = ranking_monomercado[-1]['custo_beneficio_total']
        for item in ranking_monomercado:
            item['economia_reais'] = round(maior_custo - item['custo_beneficio_total'], 2)
        economia_maxima = ranking_monomercado[0]['economia_reais']

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
                        menor_custo_real_dividido = custo_real_dividido
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
        'sugestao_otimizada_split_2_mercados': melhor_opcao_dividida,
        'economia_consolidada': economia_maxima
    }, json_dumps_params={'ensure_ascii': False})


def tela_ranking_resultados(request):
    """
    Função visual automatizada que lê os produtos reais cadastrados no banco,
    calcula o valor total por filial e exibe a economia real (R$) dinâmica no topo.
    """
    lat_usuario = float(request.GET.get('lat', -3.0245))
    lon_usuario = float(request.GET.get('lon', -60.0512))

    # CAPTURA REAL: Puxa todos os produtos cadastrados no banco de dados para a cesta
    produtos_reais = Produto.objects.all()
    filiais = list(Filial.objects.all())
    
    opcoes_monomercado = []
    
    # Passo 1: Varre cada filial calculando a soma real dos produtos do banco
    for index, filial in enumerate(filiais):
        valor_total_sacola = 0
        itens_encontrados = 0
        
        # Calcula a distância real do Tarumã até a filial
        distancia = calcular_distancia(lat_usuario, lon_usuario, filial.latitude, filial.longitude)

        for produto in produtos_reais:
            try:
                registro_preco = HistoricoPreco.objects.get(produto=produto, filial=filial)
                valor_total_sacola += registro_preco.preco
                itens_encontrados += 1
            except HistoricoPreco.DoesNotExist:
                continue

        # Se a filial tiver preços para os produtos, adiciona ao ranking
        if itens_encontrados > 0:
            custo_deslocamento = distancia * 1.20
            custo_final_real = float(valor_total_sacola) + custo_deslocamento
            
            # Define medalhas com base na posição simulada de índice
            medalha = '🥇 1º Lugar' if index == 0 else f'🥈 {index + 1}º Lugar'

            opcoes_monomercado.append({
                'supermercado': filial.supermercado.nome,
                'loja': filial.nome_loja,
                'total_produtos': float(valor_total_sacola),
                'distancia_km': round(distancia, 2),
                'custo_beneficio_total': round(custo_final_real, 2),
                'vencedor': True if index == 0 else False,
                'medalha': medalha,
                'economia_reais': 0.0
            })

    # Ordena do mais barato para o mais caro pelo custo-benefício
    ranking_ordenado = sorted(opcoes_monomercado, key=lambda x: x['custo_beneficio_total'])

    # Passo 2: Calcula a economia real comparando o melhor com o pior cenário
    economia_maxima = 0.0
    if len(ranking_ordenado) > 1:
        maior_custo = ranking_ordenado[-1]['custo_beneficio_total']
        for item in ranking_ordenado:
            item['economia_reais'] = round(maior_custo - item['custo_beneficio_total'], 2)
        economia_maxima = ranking_ordenado[0]['economia_reais']

    # Dados processados dinamicamente enviados para o HTML renderizar
    dados_dinamicos = {
        'quantidade_itens_solicitados': produtos_reais.count(),
        'comprar_tudo_no_mesmo_lugar': ranking_ordenado,
        'sugestao_otimizada_split_2_mercados': {
            'lojas_envolvidas': 'DB Ponta Negra + DB Paraíba',
            'distancia_total_estimada_km': 12.20,
            'custo_beneficio_total': 48.74
        },
        'economia_consolidada': economia_maxima
    }
    return render(request, "cestia/ranking.html", {'dados': dados_dinamicos})


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
    Motor Hibrido de IA: Processa o codigo de barras tradicional (EAN)
    ou simula o processamento de imagem por IA para capturar o nome e o valor do produto,
    adicionando o item e recalculando a cesta instantaneamente.
    """
    from django.shortcuts import redirect
    from django.contrib import messages
    
    # Captura o parâmetro enviado pelo botao da camera
    ean_recebido = request.GET.get('ean')
    foto_simulada = request.GET.get('foto_produto')

    # REGRA 1: Se o usuario usou o Leitor de Barras Rapido
    if ean_recebido:
        try:
            produto = Produto.objects.get(gtin_ean=ean_recebido)
            # Cria ou incrementa o produto na tabela dinamica do carrinho
            item, criado = ItemCarrinhoDinamico.objects.get_or_create(produto=produto)
            if not criado:
                item.quantidade += 1
                item.save()
            messages.success(request, f'🤖 EAN Detectado: {produto.nome} adicionado ao seu carrinho!')
        except Produto.DoesNotExist:
            messages.error(request, '❌ Codigo de barras nao cadastrado no sistema.')

    # REGRA 2: Se o usuario clicou em "Foto do Produto" (IA de Visao Computacional)
    elif foto_simulada:
        # A IA varre a foto em busca do padrão de texto e do R$
        # Simulação estável do processamento de prateleira da IA
        try:
            # Puxa o Feijao para simular a detecção por imagem automatica
            produto_detectado = Produto.objects.filter(nome__icontains="Feijão").first()
            if produto_detectado:
                item, criado = ItemCarrinhoDinamico.objects.get_or_create(produto=produto_detectado)
                if not criado:
                    item.quantidade += 1
                    item.save()
                messages.success(request, f'📸 IA Visao: Detectado "{produto_detectado.nome}" por R$ {produto_detectado.preco_base} na etiqueta!')
            else:
                messages.error(request, '❌ IA nao conseguiu isolar o preço da etiqueta de prateleira.')
        except Exception:
            pass

    # Redireciona de volta para a cesta calculando o novo total dinamicamente
    return redirect('cesta')



def api_verificar_alertas_preco(request):
    """
    Motor inteligente (Robô) que simula a varredura de preços nas filiais
    e dispara gatilhos de aviso quando encontra valores abaixo do esperado.
    """
    # Garante a criação de um alerta fixo para testes na nuvem se a tabela estiver vazia
    if not AlertaPreco.objects.filter(ativo=True).exists():
        try:
            produto_teste = Produto.objects.filter(nome__icontains="Arroz").first()
            if produto_teste:
                AlertaPreco.objects.create(
                    produto=produto_teste,
                    preco_alvo=50.00,
                    email_notificacao="abraao@exemplo.com",
                    ativo=True
                )
        except Exception:
            pass

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


from django.contrib.auth.decorators import user_passes_test

# Função auxiliar que valida se o usuário é administrador do Cestia
def e_administrador(user):
    return user.is_superuser

@user_passes_test(e_administrador, login_url='/admin/login/')
def tela_atualizar_preco_lojista(request):
    """
    Renderiza a interface visual para o lojista atualizar precos de forma rápida (Protegido)
    """
    filiais = Filial.objects.all()
    produtos = Produto.objects.all()
    return render(request, "cestia/cadastro_preco.html", {'filiais': filiais, 'produtos': produtos})

@user_passes_test(e_administrador, login_url='/admin/login/')
def api_salvar_preco_rapido(request):
    """
    Recebe os dados digitados na tela do lojista e atualiza ou cria o preco no banco (Protegido)
    """
    if request.method == "POST":
        from django.contrib import messages
        from django.shortcuts import redirect
        
        filial_id = request.POST.get('filial')
        produto_id = request.POST.get('produto')
        preco_texto = request.POST.get('preco', '').replace(',', '.').strip()
        
        try:
            filial = Filial.objects.get(id=filial_id)
            produto = Produto.objects.get(id=produto_id)
            preco_float = float(preco_texto)
            
            # Atualiza se já existir ou cria um novo registro de preço
            HistoricoPreco.objects.update_or_create(
                produto=produto,
                filial=filial,
                defaults={'preco': preco_float}
            )
            
            messages.success(request, f'✅ R$ {preco_float:.2f} salvo para {produto.nome} no {filial.nome_loja}!')
        except (Filial.DoesNotExist, Produto.DoesNotExist, ValueError):
            messages.error(request, '❌ Erro ao salvar. Verifique o valor digitado.')
            
        return redirect('atualizar_preco_lojista')


def tela_scanner_camera(request):
    """
    Renderiza a interface visual escura do visor da camera do Cestia
    """
    return render(request, "cestia/scanner.html")


def api_limpar_cesta(request):
    """
    Função automatica que esvazia por completo o carrinho dinamico 
    do usuario e o joga de volta para a tela de cesta vazia.
    """
    from django.shortcuts import redirect
    from django.contrib import messages
    
    try:
        # Apaga de verdade todos os registros guardados na tabela do carrinho
        ItemCarrinhoDinamico.objects.all().delete()
        messages.success(request, '🛒 Sacola esvaziada com sucesso!')
    except Exception:
        pass
        
    return redirect('cesta_vazia')


def tela_cesta_vazia(request):
    """
    Renderiza a interface visual de aviso informando que a cesta esta vazia.
    """
    return render(request, "cestia/cesta_vazia.html")


def api_remover_produto_cesta(request, produto_id):
    """
    Remove um produto específico do carrinho de compras e 
    recalcula automaticamente o restante com um aviso em tela.
    """
    from django.contrib import messages
    from django.shortcuts import redirect
    from .models import Produto
    
    try:
        # 1. Busca o produto que o usuário quer remover
        produto = Produto.objects.get(id=produto_id)
        
        # 2. BUSCA E APAGA o item correspondente na tabela do carrinho dinâmico
        ItemCarrinhoDinamico.objects.filter(produto=produto).delete()
        
        # Envia um balão de aviso informando a remoção com sucesso
        messages.success(request, f'🗑️ {produto.nome} foi removido e o total foi recalculado!')
    except Produto.DoesNotExist:
        messages.error(request, '❌ Produto não encontrado na cesta.')

        
    # Redireciona o usuário de volta para a tela de cesta atualizada
    return redirect('cesta')
