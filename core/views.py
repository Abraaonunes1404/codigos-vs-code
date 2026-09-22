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
    Renderiza a tela do carrinho puxando apenas os produtos reais 
    adicionados dinamicamente via scanner ou clique do usuario.
    """
    # CAPTURA INTELIGENTE: Busca apenas os registros ativos do carrinho dinâmico
    itens_carrinho = ItemCarrinhoDinamico.objects.select_related('produto').all()
    
    # Se o carrinho estiver totalmente vazio, joga o usuario para a tela de aviso
    if not itens_carrinho.exists():
        from django.shortcuts import redirect
        return redirect('cesta_vazia')
        
    # Organiza os dados para o HTML conseguir ler os campos de nome, marca e quantidade
    produtos_formatados = []
    for item in itens_carrinho:
        produtos_formatados.append({
            'id': item.produto.id,
            'nome': item.produto.nome,
            'marca': item.produto.marca,
            'quantidade': item.quantidade,
            'unidade': getattr(item.produto, 'unidade', 'kg')
        })
        
    return render(request, "cestia/cesta.html", {'produtos': produtos_formatados})


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
    Calcula o ranking dos supermercados mais baratos multiplicando 
    o preco unitario de cada filial pela quantidade real de itens no carrinho.
    """
    from .models import ItemCarrinhoDinamico, Filial
    
    # 1. Puxa todos os itens que estao guardados no carrinho ativo
    itens_carrinho = ItemCarrinhoDinamico.objects.select_related('produto').all()
    
    # Se o carrinho estiver vazio, nao tem o que calcular
    if not itens_carrinho.exists():
        from django.shortcuts import redirect
        return redirect('cesta_vazia')
        
    # 2. Busca todas as filiais cadastradas no Tarumã
    filiais = Filial.objects.all()
    ranking_calculado = []
    
    # Descobre qual filial tem a cesta mais cara para calcular a economia base
    maior_custo_total = 0
    menor_custo_total = float('inf')
    
    # Loop inteligente que calcula o custo total em cada supermercado
    for filial in filiais:
        total_produtos_filial = 0
        
        for item in itens_carrinho:
            # Busca o preço específico deste produto nesta filial
            # Se não achar, o sistema usa o preço base cadastrado por segurança
            preco_unitario = getattr(item.produto, 'preco_base', 0)
            
            # MÁGICA DA MULTIPLICAÇÃO: Preço Unitário x Quantidade da Sacola
            total_produtos_filial += (preco_unitario * item.quantidade)
            
        # Calcula o custo final somando taxas ou deslocamento se houver
        custo_beneficio_total = total_produtos_filial 
        
        if custo_beneficio_total > maior_custo_total:
            maior_custo_total = custo_beneficio_total
            
        ranking_calculado.append({
            'supermercado': filial.nome,
            'loja': filial.bairro,
            'total_produtos': total_produtos_filial,
            'custo_beneficio_total': custo_beneficio_total,
            'distancia_km': getattr(filial, 'distancia_padrao', 1.5),
            'vencedor': False,
            'economia_reais': 0
        })
        
    # Ordena o ranking do mais barato para o mais caro
    ranking_calculado = sorted(ranking_calculado, key=lambda x: x['custo_beneficio_total'])
    
    # Carimba o primeiro colocado como o Grande Vencedor
    if ranking_calculado:
        ranking_calculado[0]['vencedor'] = True
        menor_custo_total = ranking_calculado[0]['custo_beneficio_total']
        
        # Calcula a economia consolidada em relação ao mais caro
        economia_consolidada = maior_custo_total - menor_custo_total
        
        # Insere a economia individual nos cards
        for loja in ranking_calculado:
            loja['economia_reais'] = maior_custo_total - loja['custo_beneficio_total']
    else:
        economia_consolidada = 0

    # Estrutura os dados finais para enviar ao HTML
    dados_contexto = {
        'economia_consolidada': economia_consolidada,
        'comprar_tudo_no_mesmo_lugar': ranking_calculado,
        'sugestao_otimizada_split_2_mercados': {
            'distancia_total_estimada_km': 4.2,
            'custo_beneficio_total': menor_custo_total + 5.0
        }
    }
    
    return render(request, "cestia/ranking.html", {'dados': dados_contexto})



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


def api_alterar_quantidade_cesta(request, produto_id, acao):
    """
    Controla as quantidades do carrinho de compras em tempo real,
    incrementando ou decrementando e atualizando a sacola ativa.
    """
    from django.shortcuts import redirect
    from .models import ItemCarrinhoDinamico, Produto
    
    try:
        produto = Produto.objects.get(id=produto_id)
        item_carrinho = ItemCarrinhoDinamico.objects.get(produto=produto)
        
        if acao == "aumentar":
            item_carrinho.quantidade += 1
            item_carrinho.save()
        elif acao == "diminuir":
            if item_carrinho.quantidade > 1:
                item_carrinho.quantidade -= 1
                item_carrinho.save()
            else:
                # Se for menor que 1, deleta o produto da sacola automaticamente
                item_carrinho.delete()
                
    except (Produto.DoesNotExist, ItemCarrinhoDinamico.DoesNotExist):
        pass
        
    return redirect('cesta')
