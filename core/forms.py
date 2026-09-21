from django import forms
from .models import Filial

class UploadPrecosForm(forms.Form):
    filial = forms.ModelChoiceField(
        queryset=Filial.objects.all(), 
        empty_label="Selecione a Filial correspondente"
    )
    arquivo_csv = forms.FileField(
        label="Selecione o arquivo CSV (EAN;PRECO)",
        help_text="O arquivo deve estar no formato .csv separado por ponto e vírgula."
    )
