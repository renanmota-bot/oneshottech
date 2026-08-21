from django.db import models
from django.contrib.auth.models import AbstractUser

class Empresa(models.Model):
    STATUS_CHOICES = (
        ('ATIVO', 'Ativo'),
        ('INADIMPLENTE', 'Inadimplente'),
        ('DEGUSTACAO', 'Degustação'),
        ('BLOQUEADO', 'Bloqueado'),
    )
    nome = models.CharField("Razão Social / Nome Fantasia", max_length=200)
    cnpj = models.CharField("CNPJ ou CPF", max_length=30, unique=True)
    inscricao_estadual = models.CharField("Inscrição Estadual", max_length=50, blank=True, null=True)
    whatsapp = models.CharField("WhatsApp da Empresa", max_length=20, blank=True, null=True)
    chave_pix = models.CharField("Chave Pix da Empresa", max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ATIVO')
    plano = models.CharField(max_length=50, default='MENSAL')
    valor_plano = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Empresa / Produtora"
        verbose_name_plural = "Empresas / Produtoras"

    def __str__(self):
        return self.nome

class Usuario(AbstractUser):
    PERFIL_CHOICES = (
        ('SUPER_ADMIN', 'Super Admin SaaS'),
        ('ADMIN', 'Admin Produtora'),
        ('STAFF', 'Staff / Colaborador'),
    )
    TIPO_PIX_CHOICES = (
        ('CPF', 'CPF'),
        ('CNPJ', 'CNPJ'),
        ('EMAIL', 'E-mail'),
        ('TELEFONE', 'Telefone'),
        ('ALEATORIA', 'Chave Aleatória'),
    )
    GENERO_CHOICES = (
        ('M', 'Masculino'),
        ('F', 'Feminino'),
        ('O', 'Outro / Não Informar'),
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, null=True, blank=True, related_name='usuarios')
    perfil = models.CharField(max_length=20, choices=PERFIL_CHOICES, default='SUPER_ADMIN')
    
    cpf = models.CharField("CPF", max_length=20, blank=True, null=True)
    rg = models.CharField("RG", max_length=20, blank=True, null=True)
    
    whatsapp = models.CharField("WhatsApp", max_length=20, blank=True, null=True)
    genero = models.CharField("Gênero", max_length=1, choices=GENERO_CHOICES, blank=True, null=True)
    tamanho_camiseta = models.CharField("Tamanho de Camiseta", max_length=10, blank=True, null=True)
    tamanho_calcado = models.CharField("Número de Calçado", max_length=10, blank=True, null=True)
    
    tipo_chave_pix = models.CharField("Tipo da Chave Pix", max_length=20, choices=TIPO_PIX_CHOICES, blank=True, null=True)
    chave_pix = models.CharField("Chave Pix", max_length=100, blank=True, null=True)
    
    foto = models.ImageField(upload_to='perfil/', blank=True, null=True)
    nota_media = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)

    # CORREÇÃO OBRIGATÓRIA DO DJANGO PARA AUTH_USER_MODEL (Evita o erro E304)
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='usuario_set',
        blank=True,
        help_text='Os grupos aos quais este usuário pertence.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='usuario_permissions_set',
        blank=True,
        help_text='Permissões específicas para este usuário.',
        verbose_name='user permissions',
    )

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return f"{self.first_name or self.username} ({self.perfil})"

class ChamadoSuporte(models.Model):
    STATUS_CHOICES = (
        ('ABERTO', 'Aberto'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('RESOLVIDO', 'Resolvido'),
        ('FECHADO', 'Fechado'),
    )
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='chamados')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='chamados')
    assunto = models.CharField("Assunto", max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTO')
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Chamado de Suporte"
        verbose_name_plural = "Chamados de Suporte"

    def __str__(self):
        return f"#{self.id} - {self.assunto} ({self.empresa.nome})"

class MensagemChamado(models.Model):
    chamado = models.ForeignKey(ChamadoSuporte, on_delete=models.CASCADE, related_name='mensagens')
    remetente = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    mensagem = models.TextField("Mensagem")
    data_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mensagem de Chamado"
        verbose_name_plural = "Mensagens de Chamados"