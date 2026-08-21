from django.db import models
from core.models import Empresa, Usuario

class Evento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='eventos')
    nome = models.CharField("Nome do Evento", max_length=200)
    local = models.TextField("Localização / Endereço")
    latitude = models.FloatField("Latitude", null=True, blank=True)
    longitude = models.FloatField("Longitude", null=True, blank=True)
    dress_code = models.TextField("Dress Code / Uniforme Exigido", null=True, blank=True)
    data_inicio = models.DateField("Data Início")
    data_fim = models.DateField("Data Fim")
    hora_inicio = models.TimeField("Horário Início (24h)", null=True, blank=True)
    hora_fim = models.TimeField("Horário Fim (24h)", null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"

    def __str__(self):
        return f"{self.nome} ({self.empresa.nome})"

class Vaga(models.Model):
    STATUS_CHOICES = (
        ('ABERTA', 'Aberta'),
        ('PREENCHIDA', 'Preenchida'),
        ('CANCELADA', 'Cancelada'),
    )
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='vagas')
    funcao = models.CharField("Função / Cargo", max_length=100)
    valor_diaria = models.DecimalField("Valor da Diária (R$)", max_digits=10, decimal_places=2)
    quantidade = models.IntegerField("Quantidade de Vagas", default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTA')

    class Meta:
        verbose_name = "Vaga"
        verbose_name_plural = "Vagas"

    def __str__(self):
        return f"{self.funcao} - {self.evento.nome}"

class Candidatura(models.Model):
    STATUS_CHOICES = (
        ('PENDENTE', 'Pendente de Aprovação'),
        ('APROVADO', 'Aprovado'),
        ('RECUSADO', 'Recusado'),
    )
    vaga = models.ForeignKey(Vaga, on_delete=models.CASCADE, related_name='candidaturas')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='candidaturas')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    data_candidatura = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('vaga', 'usuario')
        verbose_name = "Candidatura"
        verbose_name_plural = "Candidaturas"

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} -> {self.vaga}"

class PresencaPagamento(models.Model):
    STATUS_PAG_CHOICES = (
        ('PENDENTE', 'Pendente'),
        ('PARCIAL', 'Parcial'),
        ('PAGO', 'Pago'),
    )
    STATUS_DESLOCAMENTO_CHOICES = (
        ('AGUARDANDO', 'Aguardando'),
        ('A_CAMINHO', 'A Caminho'),
        ('NO_LOCAL', 'No Local / Check-in Realizado'),
    )
    candidatura = models.OneToOneField(Candidatura, on_delete=models.CASCADE, related_name='presenca_pagamento')
    dias_presentes = models.IntegerField("Dias Presentes", default=0)
    ultima_data_checkin = models.DateField("Data do Último Check-in", null=True, blank=True)
    status_deslocamento = models.CharField("Status Deslocamento", max_length=20, choices=STATUS_DESLOCAMENTO_CHOICES, default='AGUARDANDO')
    lat_checkin = models.FloatField("Latitude Check-in", null=True, blank=True)
    lng_checkin = models.FloatField("Longitude Check-in", null=True, blank=True)
    status_pagamento = models.CharField("Status Pagamento", max_length=20, choices=STATUS_PAG_CHOICES, default='PENDENTE')
    valor_pago = models.DecimalField("Valor Pago (R$)", max_digits=10, decimal_places=2, default=0.00)
    data_pagamento = models.DateTimeField("Data do Pagamento", auto_now=True)

    class Meta:
        verbose_name = "Presença e Pagamento"
        verbose_name_plural = "Presenças e Pagamentos"

    def __str__(self):
        return f"{self.candidatura.usuario.get_full_name() or self.candidatura.usuario.username} - {self.status_deslocamento}"