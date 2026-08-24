from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Empresa, Usuario, ChamadoSuporte, MensagemChamado

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'cnpj', 'status', 'plano', 'valor_plano', 'data_criacao')
    list_filter = ('status', 'plano')
    search_fields = ('nome', 'cnpj')

@admin.register(Usuario)
class UsuarioCustomAdmin(UserAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'perfil', 'empresa', 'is_staff', 'is_superuser')
    list_filter = ('perfil', 'is_staff', 'is_superuser', 'empresa')
    search_fields = ('username', 'email', 'first_name', 'cpf', 'rg')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Informações Multi-Tenant', {'fields': ('empresa', 'perfil')}),
        ('Documentos e Contatos', {'fields': ('whatsapp', 'genero', 'tamanho_camiseta', 'tamanho_calcado', 'cpf', 'rg', 'tipo_chave_pix', 'chave_pix', 'foto', 'nota_media')}),
    )

@admin.register(ChamadoSuporte)
class ChamadoSuporteAdmin(admin.ModelAdmin):
    list_display = ('id', 'assunto', 'empresa', 'usuario', 'status', 'data_criacao')
    list_filter = ('status', 'empresa')
    search_fields = ('assunto', 'empresa__nome')

@admin.register(MensagemChamado)
class MensagemChamadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'chamado', 'remetente', 'data_envio')