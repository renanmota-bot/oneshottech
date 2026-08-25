from django.db import models
from core.models import Empresa, Usuario


class Evento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='eventos')
    nome = models.CharField(max_length=255)
    local = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    data_inicio = models.DateField()
    data_termino = models.DateField(null=True, blank=True)
    dress_code = models.CharField(max_length=255, null=True, blank=True)
    
    # RECURSO PREMIUM: DASHBOARD DE CUSTO
    orcamento_previsto = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Orçamento Previsto (R$)")
    
    data_criacao = models.DateTimeField(auto_now_add=True)

    def custo_total_executado(self):
        total = 0.0
        for vaga in self.vagas.all():
            aprovados = vaga.candidaturas.filter(status='APROVADO').count()
            total += float(vaga.valor_diaria) * aprovados
        return total

    def __str__(self):
        return self.nome


class Vaga(models.Model):
    STATUS_CHOICES = (('ABERTA', 'Aberta'), ('PREENCHIDA', 'Preenchida'))
    
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='vagas')
    funcao = models.CharField(max_length=100)
    valor_diaria = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade = models.IntegerField(default=1)
    prazo_pagamento_dias = models.IntegerField(default=0)
    dress_code = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTA')

    def __str__(self):
        return f"{self.funcao} - {self.evento.nome}"


class Candidatura(models.Model):
    STATUS_CHOICES = (('PENDENTE', 'Pendente'), ('APROVADO', 'Aprovado'), ('RECUSADO', 'Recusado'))
    
    vaga = models.ForeignKey(Vaga, on_delete=models.CASCADE, related_name='candidaturas')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='candidaturas')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    
    # RECURSO PREMIUM: CONTRATO DIGITAL & TERMO DE IMAGEM
    aceitou_termo = models.BooleanField(default=False, verbose_name="Aceitou Contrato e Termo de Imagem")
    data_aceite_termo = models.DateTimeField(null=True, blank=True)
    
    data_candidatura = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('vaga', 'usuario')

    def __str__(self):
        return f"{self.usuario.username} -> {self.vaga.funcao}"


class PresencaPagamento(models.Model):
    STATUS_DESLOCAMENTO_CHOICES = (
        ('PENDENTE', 'Aguardando'),
        ('A_CAMINHO', 'A Caminho'),
        ('CHECKIN_REALIZADO', 'Check-in Realizado'),
        ('VALIDADO', 'Validado Presencial'),
        ('FALTOU', 'Faltou'),
    )
    STATUS_PAGAMENTO_CHOICES = (
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('CONFIRMADO', 'Confirmado pelo Staff'),
        ('CANCELADO', 'Cancelado'),
    )

    candidatura = models.OneToOneField(Candidatura, on_delete=models.CASCADE, related_name='presenca_pagamento')
    status_deslocamento = models.CharField(max_length=30, choices=STATUS_DESLOCAMENTO_CHOICES, default='PENDENTE')
    lat_checkin = models.FloatField(null=True, blank=True)
    lng_checkin = models.FloatField(null=True, blank=True)
    
    # ANTI-FRAUDE: SELFIE DE CHECKIN
    foto_checkin = models.ImageField(upload_to='checkins/', null=True, blank=True, verbose_name="Selfie de Check-in")
    
    dias_presentes = models.IntegerField(default=1)
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status_pagamento = models.CharField(max_length=20, choices=STATUS_PAGAMENTO_CHOICES, default='PENDENTE')

    # AVALIAÇÃO DE DESEMPENHO (1-5 ESTRELAS)
    nota_desempenho = models.IntegerField(null=True, blank=True, verbose_name="Nota (1 a 5 estrelas)")
    comentario_desempenho = models.TextField(null=True, blank=True, verbose_name="Comentário de Avaliação")

    data_checkin = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.candidatura.usuario.get_full_name()} - {self.candidatura.vaga.evento.nome}"


# MURAL DE AVISOS DINÂMICO
class AvisoEvento(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='avisos')
    titulo = models.CharField(max_length=150)
    mensagem = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_criacao']

    def __str__(self):
        return f"{self.evento.nome} - {self.titulo}"


# RECURSO PREMIUM: PROPOSTAS COMERCIAIS & NOTAS FISCAIS DO CLIENTE
class PropostaComercial(models.Model):
    STATUS_CHOICES = (
        ('RASCUNHO', 'Rascunho'),
        ('ENVIADA', 'Enviada'),
        ('APROVADA', 'Aprovada'),
        ('RECUSADA', 'Recusada'),
    )
    NFSE_STATUS_CHOICES = (
        ('NAO_EMITIDA', 'Não Emitida'),
        ('EMITIDA', 'Emitida'),
        ('ERRO', 'Erro na Emissão'),
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='propostas')
    evento = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank=True, related_name='propostas')
    cliente_nome = models.CharField(max_length=255, verbose_name="Razão Social / Nome do Cliente")
    cliente_cnpj_cpf = models.CharField(max_length=20, verbose_name="CNPJ / CPF do Cliente")
    cliente_email = models.EmailField(null=True, blank=True)
    cliente_endereco = models.CharField(max_length=255, null=True, blank=True)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor Total da Proposta (R$)")
    descricao_servicos = models.TextField(verbose_name="Descrição dos Serviços")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RASCUNHO')

    # NOTA FISCAL DO CLIENTE
    nfse_numero = models.CharField(max_length=50, null=True, blank=True)
    nfse_status = models.CharField(max_length=20, choices=NFSE_STATUS_CHOICES, default='NAO_EMITIDA')
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Proposta #{self.id} - {self.cliente_nome} (R$ {self.valor_total})"