import uuid
from datetime import date, datetime
from django.db import models
from django.contrib.auth.models import AbstractUser


class Empresa(models.Model):
    PLANO_CHOICES = (
        ('BASICO', 'Básico'),
        ('PREMIUM', 'Premium'),
        ('CUSTOM', 'Personalizado / Enterprise'),
    )
    STATUS_CHOICES = (
        ('ATIVO', 'Ativo'),
        ('BLOQUEADO', 'Bloqueado'),
        ('SUSPENSO', 'Inadimplente / Suspenso'),
    )

    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ATIVO')
    plano = models.CharField(max_length=20, choices=PLANO_CHOICES, default='BASICO')
    valor_plano = models.DecimalField(max_digits=10, decimal_places=2, default=150.00)
    limite_staffs = models.IntegerField(default=300)
    limite_eventos_mes = models.IntegerField(default=10, verbose_name="Limite de Eventos por Mês")
    whatsapp = models.CharField(max_length=20, null=True, blank=True)
    inscricao_estadual = models.CharField(max_length=50, null=True, blank=True)

    # PERSONALIZAÇÃO WHITE-LABEL & IDENTIDADE VISUAL
    logo = models.ImageField(upload_to='logos_empresas/', null=True, blank=True, verbose_name="Logo da Empresa")
    cor_primaria = models.CharField(max_length=7, default='#A2673B', verbose_name="Cor Primária (Hex)")
    cor_secundaria = models.CharField(max_length=7, default='#1C0D07', verbose_name="Cor Secundária (Hex)")
    cor_fundo = models.CharField(max_length=7, default='#080605', verbose_name="Cor de Fundo (Hex)")

    # MÓDULOS & RECURSOS PREMIUM LIBERADOS INDIVIDUALMENTE
    recurso_nfse = models.BooleanField(default=False, verbose_name="Módulo Emissão NFS-e")
    recurso_whatsapp_api = models.BooleanField(default=False, verbose_name="Módulo Disparos WhatsApp")
    recurso_post_event_pdf = models.BooleanField(default=True, verbose_name="Módulo Relatório Post-Event PDF")
    recurso_portal_cliente = models.BooleanField(default=True, verbose_name="Módulo Portal do Cliente")
    recurso_exportacao_pix = models.BooleanField(default=True, verbose_name="Módulo Lote PIX (CSV)")
    recurso_checkin_gps = models.BooleanField(default=True, verbose_name="Módulo Check-in GPS")

    # RECURSOS PLANO PREMIUM & NFS-E
    inscricao_municipal = models.CharField(max_length=50, null=True, blank=True, verbose_name="Inscrição Municipal")
    nfse_api_key = models.CharField(max_length=255, null=True, blank=True, verbose_name="Chave API NFS-e")
    nfse_ambiente = models.CharField(
        max_length=20, 
        choices=(('HOMOLOGACAO', 'Homologação'), ('PRODUCAO', 'Produção')), 
        default='HOMOLOGACAO'
    )

    # WHATSAPP API
    whatsapp_api_instancia = models.CharField(max_length=100, null=True, blank=True, verbose_name="Instância WhatsApp API")
    whatsapp_api_token = models.CharField(max_length=255, null=True, blank=True, verbose_name="Token WhatsApp API")
    whatsapp_disparos_mes = models.IntegerField(default=0, verbose_name="Disparos Realizados no Mês")

    data_criacao = models.DateTimeField(auto_now_add=True)

    @property
    def is_premium(self):
        return self.plano in ['PREMIUM', 'CUSTOM']

    def pode_enviar_whatsapp(self):
        return self.recurso_whatsapp_api and bool(self.whatsapp_api_instancia and self.whatsapp_api_token)

    def pode_emitir_nfse(self):
        return self.recurso_nfse and bool(self.nfse_api_key and self.inscricao_municipal)

    def __str__(self):
        return f"{self.nome} ({self.get_plano_display()})"


class Usuario(AbstractUser):
    PERFIL_CHOICES = (
        ('SUPER_ADMIN', 'Super Admin (Dev)'),
        ('ADMIN', 'Admin Produtora'),
        ('STAFF', 'Staff / Colaborador'),
    )
    GENERO_CHOICES = (
        ('MASCULINO', 'Masculino'),
        ('FEMININO', 'Feminino'),
        ('NAO_BINARIO', 'Não-binário'),
        ('OUTRO', 'Outro'),
    )
    STATUS_APROVACAO_CHOICES = (
        ('PENDENTE', 'Aguardando Aprovação'),
        ('APROVADO', 'Aprovado'),
        ('RECUSADO', 'Recusado'),
    )

    perfil = models.CharField(max_length=20, choices=PERFIL_CHOICES, default='STAFF')
    status_aprovacao = models.CharField(max_length=20, choices=STATUS_APROVACAO_CHOICES, default='PENDENTE')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, null=True, blank=True)
    
    # IDENTIFICADOR ÚNICO ANÔNIMO (LGPD)
    codigo_perfil = models.CharField(max_length=15, unique=True, editable=False, blank=True, null=True)

    # DADOS PESSOAIS & CONTATO DE EMERGÊNCIA
    nome_artistico = models.CharField(max_length=150, null=True, blank=True)
    cpf = models.CharField(max_length=14, null=True, blank=True)
    rg = models.CharField(max_length=20, null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True, verbose_name="Data de Nascimento")
    whatsapp = models.CharField(max_length=20, null=True, blank=True)
    genero = models.CharField(max_length=20, choices=GENERO_CHOICES, null=True, blank=True)
    
    emergencia_nome = models.CharField(max_length=150, null=True, blank=True)
    emergencia_vinculo = models.CharField(max_length=50, null=True, blank=True)
    emergencia_telefone = models.CharField(max_length=20, null=True, blank=True)

    # CARACTERÍSTICAS FÍSICAS & ATRIBUTOS DE ELENCO
    altura = models.IntegerField(null=True, blank=True, help_text="Altura em cm")
    manequim = models.CharField(max_length=10, null=True, blank=True)
    tamanho_camiseta = models.CharField(max_length=10, null=True, blank=True)
    tamanho_calcado = models.CharField(max_length=10, null=True, blank=True)
    etnia = models.CharField(max_length=50, null=True, blank=True)
    cor_olhos = models.CharField(max_length=50, null=True, blank=True)
    cor_cabelo = models.CharField(max_length=50, null=True, blank=True)

    # LOCALIZAÇÃO E MOBILIDADE
    cep = models.CharField(max_length=10, null=True, blank=True)
    estado = models.CharField(max_length=2, null=True, blank=True)
    cidade = models.CharField(max_length=100, null=True, blank=True)
    bairro = models.CharField(max_length=100, null=True, blank=True)
    rua_numero = models.CharField(max_length=255, null=True, blank=True)
    
    possui_veiculo = models.BooleanField(default=False)
    tipo_veiculo = models.CharField(max_length=50, null=True, blank=True)
    possui_cnh = models.BooleanField(default=False)
    categoria_cnh = models.CharField(max_length=10, null=True, blank=True)

    # FUNÇÕES E IDIOMAS
    funcoes = models.JSONField(default=list, blank=True)
    idiomas = models.JSONField(default=list, blank=True)

    # FINANCEIRO & PERFIL
    tipo_chave_pix = models.CharField(max_length=20, null=True, blank=True)
    chave_pix = models.CharField(max_length=100, null=True, blank=True)
    foto = models.ImageField(upload_to='perfis/', null=True, blank=True)
    nota_media = models.FloatField(default=5.0)

    # GESTÃO VIP & BLACKLIST
    is_vip = models.BooleanField(default=False, verbose_name="Destaque VIP")
    is_blacklist = models.BooleanField(default=False, verbose_name="Bloqueado na Blacklist")
    motivo_blacklist = models.TextField(null=True, blank=True, verbose_name="Motivo do Bloqueio Interno")

    # TERMOS LGPD
    aceite_termos = models.BooleanField(default=False)
    data_aceite_termos = models.DateTimeField(null=True, blank=True)

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

    def save(self, *args, **kwargs):
        if not self.codigo_perfil:
            self.codigo_perfil = f"BRV-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    @property
    def idade(self):
        if self.data_nascimento:
            try:
                if isinstance(self.data_nascimento, str):
                    dt = datetime.strptime(self.data_nascimento, '%Y-%m-%d').date()
                else:
                    dt = self.data_nascimento
                hoje = date.today()
                return hoje.year - dt.year - ((hoje.month, hoje.day) < (dt.month, dt.day))
            except Exception:
                return "N/I"
        return "N/I"

    def taxa_presenca(self):
        try:
            candidaturas_aprovadas = self.candidaturas.filter(status='APROVADO')
            total_aprovados = candidaturas_aprovadas.count()
            if total_aprovados == 0:
                return "100% (Novo)"
                
            faltas = 0
            for cand in candidaturas_aprovadas:
                if hasattr(cand, 'presenca_pagamento'):
                    st = getattr(cand.presenca_pagamento, 'status_pagamento', '')
                    if st == 'CANCELADO':
                        faltas += 1
                    
            presencas = total_aprovados - faltas
            porcentagem = int((presencas / total_aprovados) * 100)
            return f"{porcentagem}% ({presencas}/{total_aprovados})"
        except Exception:
            return "100%"

    def __str__(self):
        return self.get_full_name() or self.username


class FotoStaff(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='galeria_fotos')
    imagem = models.ImageField(upload_to='galeria_staff/')
    is_principal = models.BooleanField(default=False)
    data_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Foto de {self.usuario.username} #{self.id}"


class LogAuditoria(models.Model):
    usuario_executor = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='logs_executados')
    usuario_afetado = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs_sofridos')
    acao = models.CharField(max_length=100)
    descricao = models.TextField()
    ip = models.CharField(max_length=45, null=True, blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.data_hora.strftime('%d/%m/%Y %H:%M')}] {self.acao} por {self.usuario_executor}"


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