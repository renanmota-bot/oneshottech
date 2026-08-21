from django.contrib import admin
from .models import Evento, Vaga, Candidatura, PresencaPagamento

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'empresa', 'data_inicio', 'data_fim')
    search_fields = ('nome', 'empresa__nome', 'local')

@admin.register(Vaga)
class VagaAdmin(admin.ModelAdmin):
    list_display = ('id', 'funcao', 'evento', 'valor_diaria', 'quantidade', 'status')
    list_filter = ('status',)

@admin.register(Candidatura)
class CandidaturaAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'vaga', 'status', 'data_candidatura')
    list_filter = ('status',)

@admin.register(PresencaPagamento)
class PresencaPagamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidatura', 'dias_presentes', 'status_deslocamento', 'status_pagamento', 'valor_pago')
    list_filter = ('status_pagamento', 'status_deslocamento')