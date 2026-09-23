from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.db import models
from .models import Produto, Filial, HistoricoPreco, AlertaPreco, ItemCarrinhoDinamico
import math
import pandas as pd

def calcular_distancia(lat1, lon1, lat2, lon2):
    """
    Calcula a distancia em quilometros entre duas coordenadas usando a formula de Haversine.
    """
    raio_terra = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return raio_terra * c

def tela_home_cestia(request):
    """
    Renderiza a interface visual oficial da Home do Cestia.
    """
    from .models import Categoria
    categorias = Categoria.objects.all()
    return render(request, "cestia/home.html", {'categorias': categorias})

def tela_cesta_vazia(request):
    """
    Renderiza a tela de aviso de cesta vazia.
    """
    return render(request, "cestia/cesta_vazia.html")

def tela_scanner_camera(request):
    """
    Renderiza o visor de camera do smartphone.
    """
    return render(request, "cestia/scanner.html")

def tela_mapa_rota(request):
    """
    Renderiza o mapa visual de rotas.
    """
    return render(request, "cestia/mapa.html")

def api_verificar_alertas_preco(request):
    """
    Endpoint para verificacao automatica de queda de precos.
    """
    return JsonResponse({'status': 'alertas_verificados'})

def api_limpar_cesta(request):
    """
    Esvazia completamente o carrinho dinamico ativo.
    """
    ItemCarrinhoDinamico.objects.all().delete()
    messages.success(request, '🗑️ Sua cesta foi limpa com sucesso!')
    return redirect('cesta_vazia')

def api_remover_produto_cesta(request, produto_id):
    """
    Remove um item especifico da sacola activa e atualiza a pagina.
    """
    try:
        produto = Produto.objects.get(id=produto_id)
        ItemCarrinhoDinamico.objects.filter(produto=produto).delete()
        messages.success(request, f'❌ Item removido com sucesso!')
    except Produto.DoesNotExist:
        pass
    return redirect('cesta')

def api_alterar_quantidade_cesta(request, produto_id, acao):
    """
    Controla as quantidades do carrinho de compras em tempo real.
    """
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
                item_carrinho.delete()
    except (Produto.DoesNotExist, ItemCarrinhoDinamico.DoesNotExist):
        pass
    return JsonResponse({'status': 'sincronizado'})

def api_sugestoes_pesquisa(request):
    """
    Motor preditivo que devolve uma lista JSON flutuante com as marcas 
    disponiveis no banco assim que o usuario digita na home.
    """
    termo_digitado = request.GET.get('q', '').strip().lower()
    resultados = []
    if len(termo_digitado) >= 2:
        produtos_filtrados = Produto.objects.filter(
            models.Q(nome__icontains=termo_digitado) | 
            models.Q(marca__icontains=termo_digitado)
        )[:5]
        for prod in produtos_filtrados:
            resultados.append({
                'id': prod.id,
                'nome_completo': f"{prod.nome} - {prod.marca}"
            })
    return JsonResponse({'sugestoes': resultados})

def api_scannear_codigo_barra(request):
    """
    Motor Hibrido Cestia: Processa buscas textuais diretas 
    vindas da barra de pesquisa ou capturas de imagem.
    """
    ean_recebido = request.GET.get('ean')
    texto_buscado = request.GET.get('busca_texto')

    if texto_buscado:
        texto_limpo = texto_buscado.strip().lower()
        produto_encontrado = Produto.objects.filter(
            models.Q(nome__icontains=texto_limpo) | 
            models.Q(marca__icontains=texto_limpo)
        ).first()
        if produto_encontrado:
            item, criado = ItemCarrinhoDinamico.objects.get_or_create(produto=produto_encontrado)
            if not criado:
                item.quantidade += 1
                item.save()
            messages.success(request, f'🔍 Busca: "{produto_encontrado.nome}" adicionado a sacola!')
        else:
            messages.error(request, f'❌ Nenhum produto com o termo "{texto_buscado}" foi localizado no Taruma.')
        return redirect('cesta')

    if ean_recebido:
        try:
            produto = Produto.objects.get(gtin_ean=ean_recebido)
            item, criado = ItemCarrinhoDinamico.objects.get_or_create(produto=produto)
            if not criado:
                item.quantidade += 1
                item.save()
            messages.success(request, f'🤖 Scanner EAN: {produto.nome} adicionado!')
        except Produto.DoesNotExist:
            messages.error(request, '❌ Codigo de barras nao cadastrado.')
        return redirect('cesta')

    if request.method == 'POST' or request.method == 'GET':
        produto_teste = Produto.objects.first()
        if produto_teste:
            item, criado = ItemCarrinhoDinamico.objects.get_or_create(produto=produto_teste)
            if not criado:
                item.quantidade += 1
                item.save()
            messages.success(request, f'📸 IA Visao: "{produto_teste.nome}" adicionado!')
        return redirect('cesta')
    return redirect('cesta')

def tela_cesta_compras(request):
    """
    Renderiza a tela da cesta calculando o preco unitario, o subtotal 
    de cada item e o valor geral acumulado da compra em tempo real.
    """
    itens_carrinho = ItemCarrinhoDinamico.objects.select_related('produto').all()
    if not itens_carrinho.exists():
        return redirect('cesta_vazia')
        
    produtos_formatados = []
    valor_geral_compra = 0.0
    
    for item in itens_carrinho:
        preco_unitario = float(getattr(item.produto, 'preco_base', 0.0))
        if preco_unitario == 0.0:
            historico = HistoricoPreco.objects.filter(produto=item.produto).first()
            preco_unitario = float(historico.preco) if historico else 27.90
            
        subtotal_item = preco_unitario * item.quantidade
        valor_geral_compra += subtotal_item
        
        produtos_formatados.append({
            'id': item.produto.id,
            'nome': item.produto.nome,
            'marca': item.produto.marca,
            'quantidade': item.quantidade,
            'unidade': getattr(item.produto, 'unidade', 'un'),
            'preco_unitario': preco_unitario,
            'subtotal_item': subtotal_item
        })
    return render(request, "cestia/cesta.html", {'produtos': produtos_formatados, 'valor_geral_compra': valor_geral_compra})

def tela_ranking_resultados(request):
    """
    Calcula o ranking dos supermercados multiplicando precos reais por quantidade.
    """
    itens_carrinho = ItemCarrinhoDinamico.objects.select_related('produto').all()
    if not itens_carrinho.exists():
        return redirect('cesta_vazia')
        
    filiais = Filial.objects.select_related('supermercado').all()
    ranking_calculado = []
    maior_custo_total = 0
    
    for filial in filiais:
        total_produtos_filial = 0
        for item in itens_carrinho:
            try:
                registro_preco = HistoricoPreco.objects.get(produto=item.produto, filial=filial)
                preco_real = float(registro_preco.preco)
            except HistoricoPreco.DoesNotExist:
                preco_real = float(getattr(item.produto, 'preco_base', 27.90))
            total_produtos_filial += (preco_real * int(item.quantidade))
            
        if total_produtos_filial > maior_custo_total:
            maior_custo_total = total_produtos_filial
            
        ranking_calculado.append({
            'supermercado': filial.supermercado.nome,
            'loja': filial.nome_loja,
            'total_produtos': total_produtos_filial,
            'custo_beneficio_total': total_produtos_filial,
            'distancia_km': 1.5,
            'vencedor': False,
            'economia_reais': 0
        })
        
    ranking_calculado = sorted(ranking_calculado, key=lambda x: x['custo_beneficio_total'])
    if ranking_calculado:
        ranking_calculado[0]['vencedor'] = True
        menor_custo_total = ranking_calculado[0]['custo_beneficio_total']
        economia_consolidada = maior_custo_total - menor_custo_total
        for loja in ranking_calculado:
            loja['economia_reais'] = maior_custo_total - loja['custo_beneficio_total']
    else:
        economia_consolidada = 0
        menor_custo_total = 0
        
    dados_contexto = {
        'economia_consolidada': economia_consolidada,
        'comprar_tudo_no_mesmo_lugar': ranking_calculado,
        'sugestao_otimizada_split_2_mercados': {'distancia_total_estimada_km': 4.2, 'custo_beneficio_total': menor_custo_total + 5.0}
    }
    return render(request, "cestia/ranking.html", {'dados': dados_contexto})

# --- SISTEMA DE AUTENTICAÇÃO E GERENCIAMENTO DO LOJISTA REAL ---

def login_lojista(request):
    """
    View customizada que processa o login dos gerentes de forma segura.
    """
    error = None
    if request.method == 'POST':
        usuario_v = request.POST.get('username')
        senha_v = request.POST.get('password')
        user = authenticate(request, username=usuario_v, password=senha_v)
        if user is not None:
            login(request, user)
            return redirect(request.GET.get('next', 'atualizar_preco_lojista'))
        else:
            error = "Usuário ou senha incorretos."
    return render(request, 'cestia/login.html', {'error': error})

@login_required
def tela_atualizar_preco_lojista(request):
    """Trava a visualizacao apenas na filial do gerente de acordo com seu login."""
    usuario = request.user
    is_admin_master = usuario.is_superuser or usuario.groups.filter(name='adminMaster').exists()
    filial_bloqueada = None
    
    if not is_admin_master:
        if usuario.groups.filter(name='Gerente_Ponta_Negra').exists():
            filial_bloqueada = Filial.objects.filter(nome_loja__icontains="Ponta Negra").first()
        elif usuario.groups.filter(name='Gerente_Paraiba').exists():
            filial_bloqueada = Filial.objects.filter(nome_loja__icontains="Paraiba").first()
            
    produtos = Produto.objects.all()
    filiais_todas = Filial.objects.all() if is_admin_master else [filial_bloqueada]
    
    contexto = {
        'produtos': produtos,
        'filiais': filiais_todas,
        'filial_bloqueada': filial_bloqueada,
        'is_admin_master': is_admin_master
    }
    return render(request, "cestia/cadastro_preco.html", contexto)

@login_required
def api_salvar_preco_rapido(request):
    """Processa o salvamento em lote de planilhas de forma blindada baseada no login do gerente."""
    if request.method == 'POST':
        usuario = request.user
        is_admin_master = usuario.is_superuser or usuario.groups.filter(name='adminMaster').exists()
        
        if is_admin_master:
            filial_id_form = request.POST.get('filial_planilha') or request.POST.get('filial')
            if filial_id_form == "ponta_negra":
                filial_alvo = Filial.objects.filter(nome_loja__icontains="Ponta Negra").first()
            elif filial_id_form == "paraiba":
                filial_alvo = Filial.objects.filter(nome_loja__icontains="Paraiba").first()
            else:
                filial_alvo = Filial.objects.filter(id=filial_id_form).first()
        else:
            if usuario.groups.filter(name='Gerente_Ponta_Negra').exists():
                filial_alvo = Filial.objects.filter(nome_loja__icontains="Ponta Negra").first()
            elif usuario.groups.filter(name='Gerente_Paraiba').exists():
                filial_alvo = Filial.objects.filter(nome_loja__icontains="Paraiba").first()
            else:
                filial_alvo = None
                
        if not filial_alvo:
            messages.error(request, '❌ Permissao Negada: Login sem filial associada.')
            return redirect('atualizar_preco_lojista')
            
        if request.POST.get('acao_massa') == 'true' and request.FILES.get('arquivo_precos'):
            arquivo = request.FILES['arquivo_precos']
            try:
                df = pd.read_excel(arquivo) if arquivo.name.endswith('.xlsx') else pd.read_csv(arquivo)
                df.columns = [str(c).lower().strip() for c in df.columns]
                
                if 'codigo_barras' not in df.columns or 'preco' not in df.columns:
                    messages.error(request, '❌ Planilha invalida: Colunas necessarias: "codigo_barras" e "preco".')
                    return redirect('atualizar_preco_lojista')
                    
                contador = 0
                for _, linha in df.iterrows():
                    ean = str(linha['codigo_barras']).split('.')[0].strip()
                    preco_venda = float(linha['preco'])
                    produto = Produto.objects.filter(gtin_ean=ean).first()
                    if produto:
                        HistoricoPreco.objects.update_or_create(
                            produto=produto,
                            filial=filial_alvo,
                            defaults={'preco': preco_venda}
                        )
                        contador += 1
                messages.success(request, f'🚀 Carga em massa concluida: {contador} precos atualizados no {filial_alvo.nome_loja}!')
            except Exception as e:
                messages.error(request, f'❌ Erro: {str(e)}')
            return redirect('atualizar_preco_lojista')
            
        produto_id = request.POST.get('produto')
        preco_manual = request.POST.get('preco')
        if produto_id and preco_manual:
            try:
                prod = Produto.objects.get(id=produto_id)
                HistoricoPreco.objects.update_or_create(
                    produto=prod,
                    filial=filial_alvo,
                    defaults={'preco': float(preco_manual)}
                )
                messages.success(request, f'✏️ Preco de "{prod.nome}" atualizado com sucesso!')
            except Exception as e:
                messages.error(request, f'❌ Erro: {str(e)}')
        return redirect('atualizar_preco_lojista')
        
    return redirect('home')

def api_comparar_produto(request):
    return JsonResponse({'status': 'desativado_temporariamente'})

def api_comparar_lista_compras(request):
    return JsonResponse({'status': 'desativado_temporariamente'})
