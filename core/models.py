from django.db import models

class Categoria(models.Model):
    nome = models.CharField(max_length=100)
    def __str__(self): return self.nome

class Produto(models.Model):
    gtin_ean = models.CharField(max_length=13, unique=True, verbose_name="Código de Barras")
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
