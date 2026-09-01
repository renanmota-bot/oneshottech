import uuid
import random
from datetime import timedelta
from django.db import models
from core.models import Empresa, Usuario


class Evento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='eventos')
    nome = models.CharField(max_length=255)
    descricao = models.TextField(null=True, blank=True)
    local = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # DATAS E HORÁRIOS DO EVENTO (PRODUTORA)
    data_inicio = models.DateField()
    data_termino = models.DateField(null=True, blank=True)
    horario_inicio = models.TimeField(null=True, blank=True, verbose_name="Horário de Início do Evento")
    horario_termino = models.TimeField(null=True, blank=True, verbose_name="Horário de Término do Evento")

    orcamento_previsto = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    token_cliente = models.CharField(max_length=64, unique=True, null=True, blank=True)
    codigo_acesso_cliente = models.CharField(max_length=10, null=True, blank=True, verbose_name="Código/PIN de Acesso do Cliente")
    
    status = models.CharField(max_length=20, default='ATIVO')
    data_criacao = models.DateTimeField(auto_now_add=True)

    def gerar_token_cliente(self):
        if not self.token_cliente:
            self.token_cliente = uuid.uuid4().hex
        if not self.codigo_acesso_cliente:
            self.codigo_acesso_cliente = f"{random.randint(100000, 999999)}"
        self.save()
        return self.token_cliente

    def __str__(self):
        return f"{self.nome} - {self.empresa.nome}"


class Vaga(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='vagas')
    funcao = models.CharField(max_length=255)
    valor_diaria = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade = models.IntegerField(default=1)
    prazo_pagamento_dias = models.IntegerField(default=0)
    
    # DATAS E HORÁRIOS ESPECÍFICOS DA VAGA (EXIBIDOS PARA O STAFF)
    data_especifica_inicio = models.DateField(null=True, blank=True)
    data_especifica_termino = models.DateField(null=True, blank=True)
    horario_inicio = models.TimeField(null=True, blank=True, verbose_name="Horário de Entrada do Staff")
    horario_termino = models.TimeField(null=True, blank=True, verbose_name="Horário de Saída do Staff")

    dress_code = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, default='ABERTA')
    data_criacao = models.DateTimeField(auto_now_add=True)

    def data_prevista_pagamento(self):
        dt_ref = self.data_especifica_termino or self.evento.data_termino or self.evento.data_inicio
        if dt_ref:
            return dt_ref + timedelta(days=self.prazo_pagamento_dias)
        return None

    def __str__(self):
        return f"{self.funcao} ({self.evento.nome})"


class Candidatura(models.Model):
    STATUS_CHOICES = (
        ('PENDENTE', 'Aguardando Análise'),
        ('APROVADO_CLIENTE', 'Aprovado pelo Cliente'),
        ('APROVADO', 'Validado pela Produtora'),
        ('RECUSADO', 'Recusado'),
    )
    vaga = models.ForeignKey(Vaga, on_delete=models.CASCADE, related_name='candidaturas')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='candidaturas')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDENTE')
    
    aceitou_termo = models.BooleanField(default=False)
    data_aceite_termo = models.DateTimeField(null=True, blank=True)
    ip_aceite_termo = models.CharField(max_length=45, null=True, blank=True)
    user_agent_aceite_termo = models.TextField(null=True, blank=True)

    data_candidatura = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} -> {self.vaga.funcao}"


class PresencaPagamento(models.Model):
    STATUS_PAGAMENTO_CHOICES = (
        ('PENDENTE', 'Pendente'),
        ('PROCESSANDO', 'Em Processamento'),
        ('PAGO', 'Pago / Quitado'),
        ('CANCELADO', 'Cancelado / Faltou'),
    )

    candidatura = models.OneToOneField(Candidatura, on_delete=models.CASCADE, related_name='presenca_pagamento')
    checkin_horario = models.DateTimeField(null=True, blank=True)
    latitude_checkin = models.FloatField(null=True, blank=True)
    longitude_checkin = models.FloatField(null=True, blank=True)
    
    distancia_checkin_m = models.IntegerField(null=True, blank=True)
    checkin_fora_do_raio = models.BooleanField(default=False)
    
    status_pagamento = models.CharField(max_length=20, choices=STATUS_PAGAMENTO_CHOICES, default='PENDENTE')
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    data_pagamento = models.DateTimeField(null=True, blank=True)
    transacao_pix_id = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Operação: {self.candidatura.usuario.get_full_name() or self.candidatura.usuario.username}"


class AvisoEvento(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='avisos')
    titulo = models.CharField(max_length=255)
    mensagem = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} - {self.evento.nome}"


class PropostaComercial(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='propostas')
    evento = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank=True, related_name='propostas')
    cliente_nome = models.CharField(max_length=255)
    cliente_cnpj_cpf = models.CharField(max_length=20)
    cliente_email = models.EmailField(null=True, blank=True)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    descricao_servicos = models.TextField()
    status = models.CharField(max_length=20, default='ENVIADA')
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Proposta #{self.id} - {self.cliente_nome}"