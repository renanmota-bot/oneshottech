from django import forms
from .models import Usuario

class RegistroStaffForm(forms.ModelForm):
    senha = forms.CharField(widget=forms.PasswordInput, label="Senha *")
    foto = forms.ImageField(required=True, label="Foto de Perfil (Rosto/Selfie) *")

    class Meta:
        model = Usuario
        fields = [
            'first_name', 'last_name', 'email', 'cpf', 'rg',
            'whatsapp', 'genero', 'tamanho_camiseta', 'tamanho_calcado',
            'tipo_chave_pix', 'chave_pix', 'foto'
        ]