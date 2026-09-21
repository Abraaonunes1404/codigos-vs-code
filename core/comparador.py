from core.models import Produto, Filial, HistoricoPreco
import math

def calcular_distancia(lat1, lon1, lat2, lon2):
    raio_terra = 6371  # Raio da Terra em km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return raio_terra * c

def rodar_comparacao():
    print("\n--- SIMULANDO CLIENTE NO BAIRRO TARUMÃ (MANAUS) ---")
    
    # Busca o primeiro produto cadastrado (Arroz)
    produto_teste = Produto.objects.first()
    if not produto_teste:
        print("Cadastre um produto no painel antes de testar!")
        return

    lista_de_compras = [produto_teste.id]
    
    # Coordenadas simuladas do cliente (Bairro Tarumã, Manaus)
    latitude_cliente = -3.0245
    longitude_cliente = -60.0512
    
    filiais = Filial.objects.all()
    resultados = []
    
    for filial in filiais:
        total_compra = 0
        itens_encontrados = 0
        distancia = calcular_distancia(latitude_cliente, longitude_cliente, filial.latitude, filial.longitude)
        
        for prod_id in lista_de_compras:
            try:
                registro_preco = HistoricoPreco.objects.get(produto_id=prod_id, filial=filial)
                total_compra += registro_preco.preco
                itens_encontrados += 1
            except HistoricoPreco.DoesNotExist:
                continue
        
        if itens_encontrados > 0:
            # Regra de Custo-Benefício: penalidade de R$ 1,20 por cada km de distância
            custo_deslocamento = distancia * 1.20
            custo_real_total = float(total_compra) + custo_deslocamento
            
            resultados.append({
                'loja': filial.nome_loja,
                'valor_produtos': float(total_compra),
                'distancia_km': round(distancia, 2),
                'custo_real': round(custo_real_total, 2)
            })
    
    ranking = sorted(resultados, key=lambda x: x['custo_real'])
    
    print(f"Produto pesquisado: {produto_teste.nome}\n")
    print(f"{'Supermercado':<15} | {'Preço':<10} | {'Distância':<10} | {'Custo-Benefício':<10}")
    print("-" * 65)
    
    for r in ranking:
        print(f"{r['loja']:<15} | R$ {r['valor_produtos']:<7.2f} | {r['distancia_km']:<7} km | R$ {r['custo_real']:.2f}")

# Executa a função automaticamente ao ser chamado
rodar_comparacao()
