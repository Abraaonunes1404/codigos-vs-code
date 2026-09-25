from django.db import models

class Categoria(models.Model):
    nome = models.CharField(max_length=100)
    def __str__(self): return self.nome

class Produto(models.Model):
    gtin_ean = models.CharField(
        max_length=14,
        unique=True,
        verbose_name="Código de Barras"
    )
    nome = models.CharField(max_length=255)
    marca = models.CharField(max_length=100)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    unidade = models.CharField(max_length=10, choices=[('kg', 'Quilograma'), ('L', 'Litro'), ('un', 'Unidade')])
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    def __str__(self): return f"{self.nome} ({self.quantidade}{self.unidade})"

class Supermercado(models.Model):
    nome = models.CharField(max_length=150)
    def __str__(self): return self.nome

class Filial(models.Model):
    supermercado = models.ForeignKey(Supermercado, on_delete=models.CASCADE)
    nome_loja = models.CharField(max_length=150, help_text="Ex: DB Ponta Negra")
    endereco = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    def __str__(self): return f"{self.supermercado.nome} - {self.nome_loja}"

class HistoricoPreco(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    filial = models.ForeignKey(Filial, on_delete=models.CASCADE)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    data_coleta = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('produto', 'filial')
    def __str__(self): return f"{self.produto.nome} no {self.filial.nome_loja} - R$ {self.preco}"


class AlertaPreco(models.Model):
    """
    Tabela que armazena os alertas de preços configurados pelos clientes
    """
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, verbose_name="Produto")
    preco_alvo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço Alvo (R$)")
    email_notificacao = models.EmailField(verbose_name="E-mail para Aviso")
    ativo = models.BooleanField(default=True, verbose_name="Alerta Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alerta: {self.produto.nome} abaixo de R$ {self.preco_alvo}"


class ItemCarrinhoDinamico(models.Model):
    """
    Tabela automatica que gerencia a sacola de compras viva do usuario,
    permitindo acumular quantidades e recalcular valores em tempo real.
    """
    produto = models.ForeignKey('Produto', on_delete=models.CASCADE, verbose_name="Produto")
    quantidade = models.PositiveIntegerField(default=1, verbose_name="Quantidade")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Item do Carrinho Dinamico"
        verbose_name_plural = "Itens do Carrinho Dinamico"

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome}"


class EvidenciaPrecoCliente(models.Model):
    STATUS_CHOICES = [
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
        ('nova_foto_necessaria', 'Nova foto necessária'),
    ]

    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='evidencias_clientes'
    )

    filial = models.ForeignKey(
        Filial,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evidencias_clientes'
    )

    preco_informado = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    preco_encontrado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    ean_informado = models.CharField(
        max_length=14
    )

    ean_encontrado = models.CharField(
        max_length=14,
        null=True,
        blank=True
    )

    foto_url = models.URLField(
        max_length=1000,
        null=True,
        blank=True
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True
    )

    precisao_localizacao_metros = models.FloatField(
        null=True,
        blank=True
    )

    localizacao_confirmada = models.BooleanField(
        default=False
    )

    status_validacao = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES
    )

    resultado_ia = models.JSONField(
        default=dict,
        blank=True
    )

    criada_em = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.produto.nome} - "
            f"R$ {self.preco_informado} - "
            f"{self.status_validacao}"
        )


class OportunidadeEconomia(models.Model):
    evidencia = models.OneToOneField(
        EvidenciaPrecoCliente,
        on_delete=models.CASCADE,
        related_name='oportunidade'
    )

    preco_referencia = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    economia_unitaria = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    economia_percentual = models.DecimalField(
        max_digits=6,
        decimal_places=2
    )

    ativa = models.BooleanField(
        default=True
    )

    criada_em = models.DateTimeField(
        auto_now_add=True
    )

    encerrada_em = models.DateTimeField(
        null=True,
        blank=True
    )

    motivo_encerramento = models.CharField(
        max_length=255,
        blank=True
    )

    def __str__(self):
        return (
            f"Economia de R$ {self.economia_unitaria} em "
            f"{self.evidencia.produto.nome}"
        )
