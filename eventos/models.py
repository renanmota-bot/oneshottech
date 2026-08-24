from django.db import models
from core.models import Empresa, Usuario

class Evento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)
    local = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    dress_code = models.TextField(null=True, blank=True)
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fim = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.nome} ({self.empresa.nome if self.empresa else 'Global'})"

class Vaga(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='vagas')
    funcao = models.CharField(max_length=100)
    valor_diaria = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade = models.IntegerField(default=1)
    prazo_pagamento_dias = models.IntegerField(default=0) # NOVO CAMPO
    status = models.CharField(max_length=20, default='ABERTA')

    def __str__(self):
        return f"{self.funcao} - {self.evento.nome}"

class Candidatura(models.Model):
    vaga = models.ForeignKey(Vaga, on_delete=models.CASCADE, related_name='candidaturas')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='PENDENTE')
    data_candidatura = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('vaga', 'usuario')

    def __str__(self):
        return f"{self.usuario.username} -> {self.vaga.funcao}"

class PresencaPagamento(models.Model):
    candidatura = models.OneToOneField(Candidatura, on_delete=models.CASCADE, related_name='presenca_pagamento')
    dias_presentes = models.IntegerField(default=0)
    ultima_data_checkin = models.DateField(null=True, blank=True)
    status_deslocamento = models.CharField(max_length=30, default='NAO_INICIADO')
    lat_checkin = models.FloatField(null=True, blank=True)
    lng_checkin = models.FloatField(null=True, blank=True)
    status_pagamento = models.CharField(max_length=20, default='PENDENTE')
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Presença #{self.id} - {self.candidatura.usuario.username}"