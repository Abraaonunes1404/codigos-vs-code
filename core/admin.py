import csv
import io
from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib import messages
from .models import Categoria, Produto, Supermercado, Filial, HistoricoPreco
from .forms import UploadPrecosForm

# Registros padrão no painel administrativo
admin.site.register(Categoria)
admin.site.register(Produto)
admin.site.register(Supermercado)
admin.site.register(Filial)

@admin.register(HistoricoPreco)
class HistoricoPrecoAdmin(admin.ModelAdmin):
    list_display = ('produto', 'filial', 'preco', 'data_coleta')
    list_filter = ('filial',)
    search_fields = ('produto__nome', 'produto__gtin_ean')
    
    # Adiciona a ferramenta na caixinha de "Ações em massa" do Django
    actions = ['ir_para_pagina_de_importacao']

    @admin.action(description='📂 Abrir Tela de Importação de Planilha CSV')
    def ir_para_pagina_de_importacao(self, request, queryset):
        return redirect('core_historicopreco_importar_csv')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('importar-csv/', self.admin_site.admin_view(self.importar_csv), name='core_historicopreco_importar_csv'),
        ]
        return custom_urls + urls

    def importar_csv(self, request):
        if request.method == "POST":
            form = UploadPrecosForm(request.POST, request.FILES)
            if form.is_valid():
                filial = form.cleaned_data['filial']
                arquivo = request.FILES['arquivo_csv']
                
                data_set = arquivo.read().decode('UTF-8')
                io_string = io.StringIO(data_set)
                leitor_csv = csv.reader(io_string, delimiter=';')
                
                atualizados = 0
                nao_encontrados = 0

                for linha in leitor_csv:
                    if not list(linha):
                        continue
                    try:
                        # O MVP agora aceita o ID do produto direto (ex: 2;27.90)
                        prod_id = int(linha[0].strip())
                        preco = float(linha[1].replace(',', '.').strip())
                        
                        produto = Produto.objects.get(id=prod_id)
                        
                        HistoricoPreco.objects.update_or_create(
                            produto=produto,
                            filial=filial,
                            defaults={'preco': preco}
                        )
                        atualizados += 1
                    except (Produto.DoesNotExist, ValueError, IndexError):
                        nao_encontrados += 1
                        continue

                messages.success(request, f"Sucesso! {atualizados} preços atualizados.")
                if nao_encontrados > 0:
                    messages.warning(request, f"{nao_encontrados} linhas não puderam ser processadas (verifique os IDs).")
                return redirect("..")
        else:
            form = UploadPrecosForm()

        contexto = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': 'Importar Planilha de Preços por Filial'
        }
        return render(request, "admin/importar_precos_csv.html", contexto)
