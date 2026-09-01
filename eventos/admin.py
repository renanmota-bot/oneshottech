from django.contrib import admin
from .models import Evento, Vaga, Candidatura, PresencaPagamento, PropostaComercial, AvisoEvento


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'data_inicio', 'data_termino', 'horario_inicio', 'status')
    list_filter = ('empresa', 'status', 'data_inicio')
    search_fields = ('nome', 'local', 'codigo_acesso_cliente')


@admin.register(Vaga)
class VagaAdmin(admin.ModelAdmin):
    list_display = ('funcao', 'evento', 'valor_diaria', 'quantidade', 'data_especifica_inicio', 'status')
    list_filter = ('status', 'evento__empresa')
    search_fields = ('funcao', 'evento__nome')


@admin.register(Candidatura)
class CandidaturaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'vaga', 'status', 'aceitou_termo', 'data_candidatura')
    list_filter = ('status', 'aceitou_termo')
    search_fields = ('usuario__username', 'usuario__first_name', 'vaga__funcao')


@admin.register(PresencaPagamento)
class PresencaPagamentoAdmin(admin.ModelAdmin):
    list_display = ('candidatura', 'status_pagamento', 'checkin_horario', 'distancia_checkin_m', 'transacao_pix_id')
    list_filter = ('status_pagamento', 'checkin_fora_do_raio')
    search_fields = ('candidatura__usuario__username', 'transacao_pix_id')


@admin.register(PropostaComercial)
class PropostaComercialAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente_nome', 'empresa', 'valor_total', 'status', 'data_criacao')
    list_filter = ('status', 'empresa')
    search_fields = ('cliente_nome', 'cliente_cnpj_cpf')


@admin.register(AvisoEvento)
class AvisoEventoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'evento', 'data_criacao')
    search_fields = ('titulo', 'evento__nome')