from django.db import models
from django.contrib.auth.models import AbstractUser

class Empresa(models.Model):
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, default='ATIVO')
    plano = models.CharField(max_length=20, default='BASICO')
    valor_plano = models.DecimalField(max_digits=10, decimal_places=2, default=150.00)
    whatsapp = models.CharField(max_length=20, null=True, blank=True)
    inscricao_estadual = models.CharField(max_length=50, null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

class Usuario(AbstractUser):
    PERFIL_CHOICES = (
        ('SUPER_ADMIN', 'Super Admin'),
        ('ADMIN', 'Admin Produtora'),
        ('STAFF', 'Staff / Colaborador'),
    )
    GENERO_CHOICES = (
        ('MASCULINO', 'Masculino'),
        ('FEMININO', 'Feminino'),
        ('OUTRO', 'Outro'),
    )

    perfil = models.CharField(max_length=20, choices=PERFIL_CHOICES, default='STAFF')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, null=True, blank=True)
    cpf = models.CharField(max_length=14, null=True, blank=True)
    rg = models.CharField(max_length=20, null=True, blank=True)
    whatsapp = models.CharField(max_length=20, null=True, blank=True)
    genero = models.CharField(max_length=20, choices=GENERO_CHOICES, null=True, blank=True)
    tamanho_camiseta = models.CharField(max_length=10, null=True, blank=True)
    tamanho_calcado = models.CharField(max_length=10, null=True, blank=True)
    tipo_chave_pix = models.CharField(max_length=20, null=True, blank=True)
    chave_pix = models.CharField(max_length=100, null=True, blank=True)
    foto = models.ImageField(upload_to='perfis/', null=True, blank=True)
    nota_media = models.FloatField(default=5.0)

    # CORREÇÃO DEFINITIVA DO ERRO E304
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name="usuario_groups_set",
        related_query_name="usuario",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name="usuario_permissions_set",
        related_query_name="usuario",
    )

    def __str__(self):
        return self.get_full_name() or self.username

class ChamadoSuporte(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    assunto = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default='ABERTO')
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.id} - {self.assunto}"

class MensagemChamado(models.Model):
    chamado = models.ForeignKey(ChamadoSuporte, on_delete=models.CASCADE, related_name='mensagens')
    remetente = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    mensagem = models.TextField()
    data_envio = models.DateTimeField(auto_now_add=True)