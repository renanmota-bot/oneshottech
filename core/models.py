from django.db import models
from django.contrib.auth.models import AbstractUser


class Empresa(models.Model):
    PLANO_CHOICES = (
        ('BASICO', 'Básico'),
        ('PREMIUM', 'Premium'),
    )
    STATUS_CHOICES = (
        ('ATIVO', 'Ativo'),
        ('BLOQUEADO', 'Bloqueado'),
    )

    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ATIVO')
    plano = models.CharField(max_length=20, choices=PLANO_CHOICES, default='BASICO')
    valor_plano = models.DecimalField(max_digits=10, decimal_places=2, default=150.00)
    whatsapp = models.CharField(max_length=20, null=True, blank=True)
    inscricao_estadual = models.CharField(max_length=50, null=True, blank=True)

    # RECURSOS PLANO PREMIUM
    inscricao_municipal = models.CharField(max_length=50, null=True, blank=True, verbose_name="Inscrição Municipal")
    nfse_api_key = models.CharField(max_length=255, null=True, blank=True, verbose_name="Chave API NFS-e")
    nfse_ambiente = models.CharField(
        max_length=20, 
        choices=(('HOMOLOGACAO', 'Homologação'), ('PRODUCAO', 'Produção')), 
        default='HOMOLOGACAO'
    )

    whatsapp_api_instancia = models.CharField(max_length=100, null=True, blank=True, verbose_name="Instância WhatsApp API")
    whatsapp_api_token = models.CharField(max_length=255, null=True, blank=True, verbose_name="Token WhatsApp API")
    whatsapp_disparos_mes = models.IntegerField(default=0, verbose_name="Disparos Realizados no Mês")

    data_criacao = models.DateTimeField(auto_now_add=True)

    @property
    def is_premium(self):
        return self.plano == 'PREMIUM'

    def pode_enviar_whatsapp(self):
        return self.is_premium and bool(self.whatsapp_api_instancia and self.whatsapp_api_token)

    def pode_emitir_nfse(self):
        return self.is_premium and bool(self.nfse_api_key and self.inscricao_municipal)

    def __str__(self):
        return f"{self.nome} ({self.get_plano_display()})"


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

    def taxa_presenca(self):
        candidaturas_aprovadas = self.candidaturas.filter(status='APROVADO')
        total_aprovados = candidaturas_aprovadas.count()
        if total_aprovados == 0:
            return "100% (Novo)"
            
        faltas = 0
        for cand in candidaturas_aprovadas:
            if hasattr(cand, 'presenca_pagamento') and cand.presenca_pagamento.status_deslocamento == 'FALTOU':
                faltas += 1
                
        presencas = total_aprovados - faltas
        porcentagem = int((presencas / total_aprovados) * 100)
        return f"{porcentagem}% ({presencas}/{total_aprovados})"

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