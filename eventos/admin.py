from django.contrib import admin
from .models import Evento, Vaga, Candidatura, PresencaPagamento

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'empresa', 'data_inicio', 'data_termino')
    search_fields = ('nome', 'local')
    list_filter = ('data_inicio', 'empresa')

@admin.register(Vaga)
class VagaAdmin(admin.ModelAdmin):
    list_display = ('id', 'evento', 'funcao', 'valor_diaria', 'quantidade', 'status')
    list_filter = ('status', 'funcao')

@admin.register(Candidatura)
class CandidaturaAdmin(admin.ModelAdmin):
    list_display = ('id', 'vaga', 'usuario', 'status', 'data_candidatura')
    list_filter = ('status',)

@admin.register(PresencaPagamento)
class PresencaPagamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidatura', 'status_deslocamento', 'status_pagamento', 'valor_pago')
    list_filter = ('status_deslocamento', 'status_pagamento')