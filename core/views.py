import csv
import os
import math
import re
import urllib.parse
import json
import urllib.request
import random
from datetime import datetime, date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.core.management import call_command
from django.core.mail import send_mail

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from .models import Empresa, Usuario, ChamadoSuporte, MensagemChamado
from eventos.models import Evento, Vaga, Candidatura, PresencaPagamento, PropostaComercial


def converter_data_iso(data_str):
    if not data_str:
        return date.today()
    data_clean = str(data_str).strip()
    
    if '/' in data_clean:
        try:
            p = data_clean.split('/')
            return datetime.strptime(f"{p[2]}-{p[1]}-{p[0]}", '%Y-%m-%d').date()
        except Exception:
            pass
    elif '-' in data_clean:
        try:
            return datetime.strptime(data_clean, '%Y-%m-%d').date()
        except Exception:
            pass
            
    return date.today()


def validar_cpf(cpf_input):
    cpf = re.sub(r'\D', '', str(cpf_input))
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        val = sum(int(cpf[num]) * ((i + 1) - num) for num in range(0, i))
        digit = ((val * 10) % 11) % 10
        if int(cpf[i]) != digit:
            return False
    return True


def obter_lat_lng_endereco(endereco):
    try:
        end_clean = re.sub(r'CEP:\s*\d+', '', endereco).strip(' .-,')
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(end_clean)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'OneShotTech/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data and len(data) > 0:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        pass
    return None, None


def redirect_por_perfil(user):
    perfil_usr = getattr(user, 'perfil', '')
    if user.is_superuser or perfil_usr == 'SUPER_ADMIN':
        return redirect('super_admin_dashboard')
    elif perfil_usr == 'ADMIN':
        return redirect('admin_dashboard')
    else:
        return redirect('staff_dashboard')


def login_view(request):
    if request.user.is_authenticated:
        return redirect_por_perfil(request.user)

    if request.method == 'POST':
        usuario_input = request.POST.get('username')
        senha_input = request.POST.get('password')
        
        user = authenticate(request, username=usuario_input, password=senha_input)
        if user is not None:
            login(request, user)
            return redirect_por_perfil(user)
        else:
            messages.error(request, 'E-mail ou senha inválidos.')

    return render(request, 'core/login.html')


@login_required
def super_admin_dashboard(request):
    if not (getattr(request.user, 'perfil', '') == 'SUPER_ADMIN' or request.user.is_superuser):
        return redirect('login')

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'criar_empresa':
            nome = request.POST.get('nome')
            cnpj = request.POST.get('cnpj')
            plano = request.POST.get('plano', 'BASICO')
            limite = request.POST.get('limite_staffs', 300)

            emp = Empresa.objects.create(
                nome=nome,
                cnpj=cnpj,
                plano=plano,
                status='ATIVO'
            )
            if hasattr(emp, 'limite_staffs'):
                emp.limite_staffs = limite
                emp.save()

            messages.success(request, f'✅ Empresa "{nome}" cadastrada com sucesso!')
            return redirect('super_admin_dashboard')

        elif acao == 'editar_empresa_permissoes':
            empresa_id = request.POST.get('empresa_id')
            emp = get_object_or_404(Empresa, id=empresa_id)

            emp.nome = request.POST.get('nome', emp.nome)
            emp.cnpj = request.POST.get('cnpj', emp.cnpj)
            emp.plano = request.POST.get('plano', emp.plano)
            emp.status = request.POST.get('status', emp.status)

            if hasattr(emp, 'limite_staffs'):
                emp.limite_staffs = request.POST.get('limite_staffs', 300)

            emp.save()
            messages.success(request, f'⚙️ Configurações da empresa "{emp.nome}" atualizadas!')
            return redirect('super_admin_dashboard')

    empresas = Empresa.objects.all().order_by('-id')
    for emp in empresas:
        emp.total_staffs_cadastrados = Usuario.objects.filter(empresa=emp, perfil='STAFF').count()

    usuarios_qs = Usuario.objects.all().select_related('empresa').order_by('-id')

    context = {
        'empresas': empresas,
        'todos_usuarios': usuarios_qs,
        'total_empresas': empresas.count(),
        'total_staffs': Usuario.objects.filter(perfil='STAFF').count(),
        'total_eventos': Evento.objects.count(),
    }
    return render(request, 'core/super_admin.html', context)


@login_required
def ghost_login_view(request, user_id):
    if not (getattr(request.user, 'perfil', '') == 'SUPER_ADMIN' or request.user.is_superuser):
        return redirect('login')
        
    target_user = get_object_or_404(Usuario, id=user_id)
    login(request, target_user, backend='django.contrib.auth.backends.ModelBackend')
    messages.info(request, f'👁️ Acesso ativado como "{target_user.first_name or target_user.username}"')
    return redirect_por_perfil(target_user)


@csrf_exempt
def registro_staff_view(request):
    empresa_id = request.GET.get('empresa')
    empresa = Empresa.objects.filter(id=empresa_id).first() if empresa_id else None

    if request.method == 'POST':
        email_input = request.POST.get('email')
        cpf_input = request.POST.get('cpf')

        usuario_existente = Usuario.objects.filter(username=email_input).first() or Usuario.objects.filter(cpf=cpf_input).first()
        if usuario_existente:
            if empresa:
                usuario_existente.empresa = empresa
                usuario_existente.save()
            messages.info(request, 'ℹ️ Seu cadastro já existe e foi vinculado a esta produtora. Faça login!')
            return redirect('login')

        f_rosto = request.FILES.get('foto_rosto')
        f_corpo = request.FILES.get('foto_corpo')
        f_meio = request.FILES.get('foto_meio_corpo')
        f_perfil = request.FILES.get('foto_perfil')
        f_selfie = request.FILES.get('foto_selfie')

        fotos_obrigatorias = [f_rosto, f_corpo, f_meio, f_perfil, f_selfie]
        if any(f is None for f in fotos_obrigatorias):
            messages.error(request, '❌ É obrigatório enviar as 5 fotos solicitadas!')
            return render(request, 'core/registro_staff.html', {'empresa': empresa, 'post_data': request.POST})

        if not validar_cpf(cpf_input):
            messages.error(request, '❌ O CPF informado é inválido!')
            return render(request, 'core/registro_staff.html', {'empresa': empresa, 'post_data': request.POST})

        user = Usuario.objects.create_user(
            username=email_input,
            email=email_input,
            password=request.POST.get('senha'),
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            cpf=cpf_input,
            rg=request.POST.get('rg'),
            whatsapp=request.POST.get('whatsapp'),
            genero=request.POST.get('genero'),
            tamanho_camiseta=request.POST.get('tamanho_camiseta'),
            tamanho_calcado=request.POST.get('tamanho_calcado'),
            tipo_chave_pix=request.POST.get('tipo_chave_pix'),
            chave_pix=request.POST.get('chave_pix'),
            perfil='STAFF',
            status_aprovacao='PENDENTE',
            empresa=empresa
        )

        user.foto = f_rosto
        user.save()

        messages.success(request, '✅ Cadastro realizado com sucesso! Aguarde a aprovação da produtora.')
        return redirect('login')

    return render(request, 'core/registro_staff.html', {'empresa': empresa, 'post_data': {}})


def logout_view(request):
    logout(request)
    return redirect('login')


@csrf_exempt
def portal_aprovacao_cliente_view(request, token):
    evento = get_object_or_404(Evento, token_cliente=token)
    empresa = evento.empresa

    is_premium = (getattr(empresa, 'plano', 'BASICO') == 'PREMIUM')
    if not is_premium:
        return render(request, 'core/recurso_premium_bloqueado.html', {
            'empresa': empresa,
            'mensagem': 'A aprovação interativa pelo cliente é um recurso exclusivo do Plano Premium. Utilize a exportação de PDF do casting.'
        })

    candidaturas = Candidatura.objects.filter(vaga__evento=evento).select_related('usuario', 'vaga').prefetch_related('usuario__galeria_fotos')

    if request.method == 'POST':
        cand_id = request.POST.get('candidatura_id')
        novo_status = request.POST.get('novo_status')
        cand = get_object_or_404(Candidatura, id=cand_id, vaga__evento=evento)
        
        cand.status = 'APROVADO_CLIENTE' if novo_status in ['APROVADO', 'APROVADO_CLIENTE'] else 'RECUSADO'
        cand.save()

        messages.success(request, f"Seleção salva para {cand.usuario.get_full_name() or cand.usuario.username}!")
        return redirect('portal_aprovacao_cliente', token=token)

    return render(request, 'core/portal_aprovacao.html', {'evento': evento, 'candidaturas': candidaturas, 'empresa': empresa})


@login_required
def admin_dashboard(request):
    if not (getattr(request.user, 'perfil', '') == 'ADMIN' or request.user.is_superuser):
        return redirect('login')

    empresa = request.user.empresa or Empresa.objects.first()
    hoje = date.today()
    is_premium = (getattr(empresa, 'plano', 'BASICO') == 'PREMIUM') or request.user.is_superuser

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'iniciar_evento':
            evento_id = request.POST.get('evento_id')
            ev = get_object_or_404(Evento, id=evento_id, empresa=empresa)
            ev.status = 'EM_ANDAMENTO' if hasattr(ev, 'status') else 'ATIVO'
            ev.save()
            Vaga.objects.filter(evento=ev).update(status='FECHADA')
            messages.success(request, f'🚀 Evento "{ev.nome}" iniciado! Vagas ocultadas no app do Staff.')
            return redirect('admin_dashboard')

        elif acao == 'excluir_proposta':
            proposta_id = request.POST.get('proposta_id')
            prop = get_object_or_404(PropostaComercial, id=proposta_id, empresa=empresa)
            prop.delete()
            messages.success(request, f'🗑️ Proposta #{proposta_id} removida!')
            return redirect('admin_dashboard')

        elif acao == 'salvar_mural_evento':
            evento_id = request.POST.get('evento_id')
            ev = get_object_or_404(Evento, id=evento_id, empresa=empresa)
            ev.descricao = request.POST.get('aviso_mural', '')
            ev.save()
            messages.success(request, f'📢 Mural atualizado para o evento {ev.nome}!')
            return redirect('admin_dashboard')

        elif acao == 'finalizar_evento':
            evento_id = request.POST.get('evento_id')
            ev = get_object_or_404(Evento, id=evento_id, empresa=empresa)
            ev.data_termino = hoje - timedelta(days=1)
            ev.save()
            messages.success(request, f'🏁 O evento "{ev.nome}" foi finalizado!')
            return redirect('admin_dashboard')

        elif acao == 'aprovar_cadastro_staff':
            staff_id = request.POST.get('staff_id')
            usr = get_object_or_404(Usuario, id=staff_id, perfil='STAFF')
            usr.status_aprovacao = 'APROVADO'
            usr.empresa = empresa
            usr.save()
            messages.success(request, f'✅ Cadastro/Perfil de {usr.get_full_name()} aprovado!')
            return redirect('admin_dashboard')

        elif acao == 'alterar_candidatura':
            cand_id = request.POST.get('candidatura_id')
            novo_status = request.POST.get('novo_status', 'APROVADO')
            cand = get_object_or_404(Candidatura, id=cand_id)
            cand.status = novo_status
            cand.save()
            if novo_status == 'APROVADO':
                PresencaPagamento.objects.get_or_create(candidatura=cand)
            messages.success(request, f'✅ Candidatura atualizada!')
            return redirect('admin_dashboard')

        elif acao == 'salvar_proposta':
            proposta_id = request.POST.get('proposta_id')
            evento_id = request.POST.get('evento_id')
            evento = Evento.objects.filter(id=evento_id, empresa=empresa).first() if evento_id else None
            val_total = str(request.POST.get('valor_total', '0')).replace(',', '.')

            if proposta_id:
                prop = get_object_or_404(PropostaComercial, id=proposta_id, empresa=empresa)
                prop.evento = evento
                prop.cliente_nome = request.POST.get('cliente_nome')
                prop.cliente_cnpj_cpf = request.POST.get('cliente_cnpj_cpf')
                prop.cliente_email = request.POST.get('cliente_email')
                prop.valor_total = val_total
                prop.descricao_servicos = request.POST.get('descricao_servicos')
                prop.status = request.POST.get('status', prop.status)
                prop.save()
            else:
                PropostaComercial.objects.create(
                    empresa=empresa,
                    evento=evento,
                    cliente_nome=request.POST.get('cliente_nome'),
                    cliente_cnpj_cpf=request.POST.get('cliente_cnpj_cpf'),
                    cliente_email=request.POST.get('cliente_email'),
                    valor_total=val_total,
                    descricao_servicos=request.POST.get('descricao_servicos'),
                    status=request.POST.get('status', 'ENVIADA')
                )
            messages.success(request, '📑 Proposta comercial salva!')
            return redirect('admin_dashboard')

        elif acao == 'aprovar_massa_cliente':
            evento_id = request.POST.get('evento_id')
            cand_ids = request.POST.getlist('candidatura_ids')
            cands = Candidatura.objects.filter(id__in=cand_ids, vaga__evento_id=evento_id)
            for cand in cands:
                cand.status = 'APROVADO'
                cand.save()
                PresencaPagamento.objects.get_or_create(candidatura=cand)
            messages.success(request, f'✅ Colaboradores validados com sucesso!')
            return redirect('admin_dashboard')

        elif acao == 'criar_evento':
            dt_inicio_obj = converter_data_iso(request.POST.get('data_inicio'))
            dt_termino_obj = converter_data_iso(request.POST.get('data_termino'))

            if dt_termino_obj < dt_inicio_obj:
                messages.error(request, '❌ A data de término precisa ser posterior à data de início!')
                return redirect('admin_dashboard')

            rua = request.POST.get('rua', '')
            numero = request.POST.get('numero', '')
            bairro = request.POST.get('bairro', '')
            cidade = request.POST.get('cidade', '')
            cep = request.POST.get('cep', '')
            
            partes_end = [p for p in [rua, f"Nº {numero}" if numero else "", bairro, cidade, f"CEP: {cep}" if cep else ""] if p]
            endereco_local = " - ".join(partes_end) if partes_end else request.POST.get('local', 'Local a definir')
            lat_auto, lng_auto = obter_lat_lng_endereco(endereco_local)

            ev = Evento.objects.create(
                empresa=empresa,
                nome=request.POST.get('nome'),
                local=endereco_local,
                latitude=lat_auto,
                longitude=lng_auto,
                data_inicio=dt_inicio_obj,
                data_termino=dt_termino_obj,
                orcamento_previsto=str(request.POST.get('orcamento_previsto', 0.00)).replace(',', '.')
            )
            ev.gerar_token_cliente()
            messages.success(request, '✅ Evento cadastrado com sucesso!')
            return redirect('admin_dashboard')

        elif acao == 'criar_vaga':
            evento = get_object_or_404(Evento, id=request.POST.get('evento_id'), empresa=empresa)
            Vaga.objects.create(
                evento=evento,
                funcao=request.POST.get('funcao'),
                valor_diaria=str(request.POST.get('valor_diaria', '0')).replace(',', '.'),
                quantidade=request.POST.get('quantidade', 1),
                status='ABERTA'
            )
            messages.success(request, '🎯 Vaga publicada!')
            return redirect('admin_dashboard')

    eventos = Evento.objects.filter(empresa=empresa).order_by('-data_inicio') if empresa else []
    eventos_ativos = []
    eventos_concluidos = []

    for ev in eventos:
        dt_ref = ev.data_termino if ev.data_termino else ev.data_inicio
        if isinstance(dt_ref, str):
            dt_ref = converter_data_iso(dt_ref)

        if dt_ref >= hoje:
            eventos_ativos.append(ev)
        else:
            eventos_concluidos.append(ev)

    for ev in eventos:
        cands_all = Candidatura.objects.filter(vaga__evento=ev).select_related('usuario', 'vaga', 'presenca_pagamento')
        ev.cands_pendentes = [c for c in cands_all if c.status == 'PENDENTE']
        ev.cands_aprovados_cliente = [c for c in cands_all if c.status == 'APROVADO_CLIENTE']
        ev.cands_confirmados = [c for c in cands_all if c.status == 'APROVADO']

        custo_equipe = sum([float(c.vaga.valor_diaria or 0.0) for c in ev.cands_confirmados])
        faturamento_ev = float(ev.orcamento_previsto or 0.0)
        lucro_ev = faturamento_ev - custo_equipe
        ev.margem_lucro_pct = round((lucro_ev / faturamento_ev * 100), 1) if faturamento_ev > 0 else 0.0

    equipe_staff = Usuario.objects.filter(perfil='STAFF').filter(empresa=empresa).order_by('-id') if empresa else []
    if not equipe_staff and empresa:
        equipe_staff = Usuario.objects.filter(perfil='STAFF').order_by('-id')

    staffs_pendentes = [s for s in equipe_staff if s.status_aprovacao == 'PENDENTE']
    staffs_aprovados = [s for s in equipe_staff if s.status_aprovacao != 'PENDENTE']

    propostas = PropostaComercial.objects.filter(empresa=empresa).order_by('-id') if empresa else []
    total_faturado_geral = sum([float(p.valor_total or 0.0) for p in propostas if p.status == 'APROVADA']) or sum([float(ev.orcamento_previsto or 0.0) for ev in eventos])
    
    financeiro = PresencaPagamento.objects.filter(candidatura__vaga__evento__empresa=empresa, candidatura__status='APROVADO') if empresa else []
    total_custo_staff_geral = sum([float(f.candidatura.vaga.valor_diaria or 0.0) for f in financeiro])

    context = {
        'empresa': empresa,
        'is_premium': is_premium,
        'eventos_ativos': eventos_ativos,
        'eventos_concluidos': eventos_concluidos,
        'staffs_pendentes': staffs_pendentes,
        'staffs_aprovados': staffs_aprovados,
        'propostas': propostas,
        'total_faturado_geral': total_faturado_geral,
        'total_custo_staff_geral': total_custo_staff_geral,
        'lucro_liquido_geral': total_faturado_geral - total_custo_staff_geral,
        'link_convite': request.build_absolute_uri(f"/registro/staff/?empresa={empresa.id}") if empresa else "",
    }
    return render(request, 'core/admin_dashboard.html', context)


@login_required
def staff_dashboard(request):
    if getattr(request.user, 'perfil', '') not in ['STAFF', 'SUPER_ADMIN'] and not request.user.is_superuser:
        return redirect('login')

    hoje = date.today()
    empresa = request.user.empresa or Empresa.objects.first()

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'solicitar_alteracao_dados':
            request.user.first_name = request.POST.get('first_name', request.user.first_name)
            request.user.last_name = request.POST.get('last_name', request.user.last_name)
            request.user.whatsapp = request.POST.get('whatsapp', request.user.whatsapp)
            request.user.chave_pix = request.POST.get('chave_pix', request.user.chave_pix)
            request.user.tipo_chave_pix = request.POST.get('tipo_chave_pix', request.user.tipo_chave_pix)
            request.user.tamanho_camiseta = request.POST.get('tamanho_camiseta', request.user.tamanho_camiseta)
            request.user.tamanho_calcado = request.POST.get('tamanho_calcado', request.user.tamanho_calcado)
            request.user.status_aprovacao = 'PENDENTE'
            request.user.save()

            messages.success(request, '✅ Solicitação enviada! Aguarde a aprovação da produtora.')
            return redirect('staff_dashboard')

        elif acao == 'candidatar':
            vaga_id = request.POST.get('vaga_id')
            vaga = get_object_or_404(Vaga, id=vaga_id)
            ev_alvo = vaga.evento

            dt_i_alvo = converter_data_iso(ev_alvo.data_inicio)
            dt_f_alvo = converter_data_iso(ev_alvo.data_termino) if ev_alvo.data_termino else dt_i_alvo

            minhas_cands = Candidatura.objects.filter(usuario=request.user).select_related('vaga__evento')
            for c in minhas_cands:
                ev_ex = c.vaga.evento
                dt_i_ex = converter_data_iso(ev_ex.data_inicio)
                dt_f_ex = converter_data_iso(ev_ex.data_termino) if ev_ex.data_termino else dt_i_ex

                if (dt_i_alvo <= dt_f_ex) and (dt_f_alvo >= dt_i_ex):
                    messages.error(request, f'❌ Você já tem candidatura no evento "{ev_ex.nome}" nesta mesma data!')
                    return redirect('staff_dashboard')

            total_aprovados = Candidatura.objects.filter(vaga=vaga, status='APROVADO').count()
            if total_aprovados >= vaga.quantidade:
                messages.error(request, '⚠️ Essa vaga já foi preenchida!')
                return redirect('staff_dashboard')

            cand, created = Candidatura.objects.get_or_create(usuario=request.user, vaga=vaga, defaults={'status': 'PENDENTE'})
            if created:
                messages.success(request, f'🎯 Candidatura enviada para {vaga.funcao}!')
            else:
                messages.warning(request, 'Você já se candidatou a esta vaga.')
            return redirect('staff_dashboard')

        elif acao == 'checkin_gps':
            cand_id = request.POST.get('candidatura_id')
            cand = get_object_or_404(Candidatura, id=cand_id, usuario=request.user)
            pres, _ = PresencaPagamento.objects.get_or_create(candidatura=cand)
            pres.checkin_horario = timezone.now()
            pres.save()

            messages.success(request, '📍 Check-in via GPS realizado!')
            return redirect('staff_dashboard')

    minhas_candidaturas = Candidatura.objects.filter(usuario=request.user).select_related('vaga__evento__empresa', 'presenca_pagamento').order_by('-id')
    vagas_candidatadas_ids = list(minhas_candidaturas.values_list('vaga_id', flat=True))
    vagas_aprovadas_todas = minhas_candidaturas.filter(status='APROVADO')

    vagas_aprovadas = []
    eventos_finalizados_staff = []

    for cand in vagas_aprovadas_todas:
        ev = cand.vaga.evento
        dt_fim = converter_data_iso(ev.data_termino if ev.data_termino else ev.data_inicio)
        pres = getattr(cand, 'presenca_pagamento', None)
        st_pagamento = pres.status_pagamento if pres else 'PENDENTE'

        if dt_fim < hoje or st_pagamento in ['PAGO', 'CONFIRMADO']:
            eventos_finalizados_staff.append(cand)
        else:
            cand.empresa_is_premium = (getattr(ev.empresa, 'plano', 'BASICO') == 'PREMIUM') or request.user.is_superuser
            vagas_aprovadas.append(cand)

    vagas_qs = Vaga.objects.filter(status='ABERTA').select_related('evento__empresa').order_by('-id')
    vagas_disponiveis = []

    for v in vagas_qs:
        dt_i = converter_data_iso(v.evento.data_inicio)
        dt_f = converter_data_iso(v.evento.data_termino if v.evento.data_termino else v.evento.data_inicio)

        st_ev = getattr(v.evento, 'status', 'ATIVO')
        if st_ev == 'EM_ANDAMENTO' or dt_i <= hoje or dt_f < hoje:
            continue

        aprovados_count = Candidatura.objects.filter(vaga=v, status='APROVADO').count()
        if aprovados_count >= v.quantidade:
            continue

        dias = max((dt_f - dt_i).days + 1, 1)
        v.dias_evento = dias
        v.cache_total_calculado = float(v.valor_diaria or 0.0) * dias
        vagas_disponiveis.append(v)

    funcoes_unicas = sorted(list(set(v.funcao for v in vagas_disponiveis if v.funcao)))
    extrato_pagamentos = PresencaPagamento.objects.filter(candidatura__usuario=request.user, candidatura__status='APROVADO').order_by('-id')

    context = {
        'empresa': empresa,
        'vagas_disponiveis': vagas_disponiveis,
        'funcoes_unicas': funcoes_unicas,
        'vagas_candidatadas_ids': vagas_candidatadas_ids,
        'vagas_aprovadas': vagas_aprovadas,
        'eventos_finalizados_staff': eventos_finalizados_staff,
        'extrato_pagamentos': extrato_pagamentos,
        'tot_recebido': sum(float(p.candidatura.vaga.valor_diaria or 0) for p in extrato_pagamentos if p.status_pagamento in ['PAGO', 'CONFIRMADO']),
        'tot_a_receber': sum(float(p.candidatura.vaga.valor_diaria or 0) for p in extrato_pagamentos if p.status_pagamento not in ['PAGO', 'CONFIRMADO']),
    }
    return render(request, 'core/staff_dashboard.html', context)


def login_demo_direto_view(request, tipo):
    empresa, _ = Empresa.objects.get_or_create(
        cnpj='11.222.333/0001-99', 
        defaults={
            'nome': 'One Shot Eventos & BTL', 
            'status': 'ATIVO', 
            'plano': 'PREMIUM', 
            'valor_plano': 299.00
        }
    )

    if tipo in ['super_admin', 'superadmin', 'dev']:
        user, _ = Usuario.objects.get_or_create(
            username='dev@oneshot.com.br',
            defaults={
                'email': 'dev@oneshot.com.br',
                'first_name': 'Super Admin',
                'last_name': 'Dev',
                'perfil': 'SUPER_ADMIN',
                'empresa': empresa,
                'is_staff': True,
                'is_superuser': True
            }
        )
        user.perfil = 'SUPER_ADMIN'
        user.is_superuser = True
        user.is_staff = True
        user.empresa = empresa
        user.set_password('senha123')
        user.save()

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('super_admin_dashboard')

    elif tipo == 'admin':
        user, _ = Usuario.objects.get_or_create(
            username='admin@oneshot.com.br', 
            defaults={
                'email': 'admin@oneshot.com.br', 
                'first_name': 'Produtora', 
                'last_name': 'Demo', 
                'perfil': 'ADMIN', 
                'empresa': empresa, 
                'is_staff': True
            }
        )
        user.perfil = 'ADMIN'
        user.empresa = empresa
        user.set_password('senha123')
        user.save()

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('admin_dashboard')

    elif tipo == 'staff':
        user, _ = Usuario.objects.get_or_create(
            username='staff@oneshot.com.br', 
            defaults={
                'email': 'staff@oneshot.com.br', 
                'first_name': 'Staff', 
                'last_name': 'Demo', 
                'perfil': 'STAFF', 
                'empresa': empresa
            }
        )
        user.perfil = 'STAFF'
        user.status_aprovacao = 'APROVADO'
        user.set_password('senha123')
        user.save()

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('staff_dashboard')

    return redirect('login')


@login_required
def exportar_caches_excel(request):
    empresa = request.user.empresa or Empresa.objects.first()
    financeiro = PresencaPagamento.objects.filter(candidatura__vaga__evento__empresa=empresa, candidatura__status='APROVADO')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="caches_{empresa.id}.csv"'
    response.write('\ufeff'.encode('utf8'))

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Beneficiario', 'CPF', 'Evento', 'Funcao', 'Valor', 'Status Pagamento'])

    for p in financeiro:
        usr = p.candidatura.usuario
        writer.writerow([usr.get_full_name() or usr.username, usr.cpf or 'N/A', p.candidatura.vaga.evento.nome, p.candidatura.vaga.funcao, f"{float(p.candidatura.vaga.valor_diaria or 0):.2f}".replace('.', ','), p.status_pagamento])

    return response


@login_required
def exportar_caches_pdf(request):
    empresa = request.user.empresa or Empresa.objects.first()
    financeiro = PresencaPagamento.objects.filter(candidatura__vaga__evento__empresa=empresa, candidatura__status='APROVADO').select_related('candidatura__usuario', 'candidatura__vaga__evento')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="caches_{empresa.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"Relatório de Cachês — {empresa.nome}", styles['Heading1'])]

    data_table = [["Beneficiário", "CPF", "Evento", "Função", "Valor (R$)"]]
    for p in financeiro:
        usr = p.candidatura.usuario
        data_table.append([usr.get_full_name() or usr.username, usr.cpf or 'N/A', p.candidatura.vaga.evento.nome, p.candidatura.vaga.funcao, f"R$ {p.candidatura.vaga.valor_diaria}"])

    t = Table(data_table, colWidths=[150, 90, 130, 90, 80])
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1'))]))
    elements.append(t)
    doc.build(elements)
    return response


# ADICIONADO PARA RESOLVER O ERRO DO RENDER EXIGIDO NO URLS.PY
@login_required
def exportar_ficha_staff_pdf(request, user_id):
    usr = get_object_or_404(Usuario, id=user_id)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ficha_staff_{usr.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"Ficha de Cadastro — {usr.get_full_name() or usr.username}", styles['Heading1']),
        Spacer(1, 10),
        Paragraph(f"<b>CPF:</b> {usr.cpf or 'N/A'} | <b>WhatsApp:</b> {usr.whatsapp or 'N/A'}", styles['Normal']),
        Paragraph(f"<b>Chave PIX:</b> {usr.chave_pix or 'N/A'} ({usr.tipo_chave_pix or 'N/A'})", styles['Normal']),
        Paragraph(f"<b>Camiseta:</b> {usr.tamanho_camiseta or 'N/A'} | <b>Calçado:</b> {usr.tamanho_calcado or 'N/A'}", styles['Normal']),
    ]
    doc.build(elements)
    return response


@login_required
def exportar_relatorio_post_event_pdf(request, evento_id):
    if not (getattr(request.user, 'perfil', '') in ['ADMIN', 'SUPER_ADMIN'] or request.user.is_superuser):
        return redirect('login')

    empresa = request.user.empresa or Empresa.objects.first()
    if getattr(empresa, 'plano', 'BASICO') != 'PREMIUM' and not request.user.is_superuser:
        messages.error(request, '⭐ Esta funcionalidade de Relatório Post-Event em PDF é exclusiva do Plano Premium!')
        return redirect('admin_dashboard')

    evento = get_object_or_404(Evento, id=evento_id, empresa=empresa)
    candidaturas = Candidatura.objects.filter(vaga__evento=evento, status='APROVADO').select_related('usuario', 'vaga', 'presenca_pagamento')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="post_event_{evento.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"Relatório Executivo Post-Event — {evento.nome}", ParagraphStyle('T', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#0284c7')))]

    data_table = [["Staff", "Função", "Diária (R$)", "Check-in GPS", "Status PIX"]]
    for cand in candidaturas:
        usr = cand.usuario
        pres = getattr(cand, 'presenca_pagamento', None)
        chk = pres.checkin_horario.strftime('%H:%M') if (pres and pres.checkin_horario) else "Pendente"
        st_pix = pres.status_pagamento if pres else "PENDENTE"
        data_table.append([usr.get_full_name() or usr.username, cand.vaga.funcao, f"R$ {cand.vaga.valor_diaria}", chk, st_pix])

    t = Table(data_table, colWidths=[140, 100, 80, 90, 90])
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1'))]))
    elements.append(t)
    doc.build(elements)
    return response


@login_required
def exportar_pagamentos_evento_csv(request, evento_id):
    empresa = request.user.empresa or Empresa.objects.first()
    evento = get_object_or_404(Evento, id=evento_id, empresa=empresa)
    presencas = PresencaPagamento.objects.filter(candidatura__vaga__evento=evento, candidatura__status='APROVADO').select_related('candidatura__usuario', 'candidatura__vaga')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="pagamentos_{evento.id}.csv"'
    response.write('\ufeff'.encode('utf8'))

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Nome Completo', 'CPF', 'WhatsApp', 'Funcao', 'Valor Diaria', 'Tipo PIX', 'Chave PIX', 'Status'])

    for pres in presencas:
        usr = pres.candidatura.usuario
        writer.writerow([usr.get_full_name() or usr.username, usr.cpf or 'N/A', usr.whatsapp or 'N/A', pres.candidatura.vaga.funcao, f"{float(pres.candidatura.vaga.valor_diaria or 0):.2f}".replace('.', ','), usr.tipo_chave_pix or 'N/A', usr.chave_pix or 'N/A', pres.status_pagamento])

    return response


@login_required
def exportar_lote_pix_csv(request):
    empresa = request.user.empresa or Empresa.objects.first()
    financeiro = PresencaPagamento.objects.filter(candidatura__vaga__evento__empresa=empresa, candidatura__status='APROVADO', status_pagamento='PENDENTE').select_related('candidatura__usuario', 'candidatura__vaga__evento')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="lote_pix_{empresa.id}.csv"'
    response.write('\ufeff'.encode('utf8'))

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Beneficiario', 'CPF', 'Tipo PIX', 'Chave PIX', 'Valor', 'Evento', 'Funcao'])

    for p in financeiro:
        usr = p.candidatura.usuario
        writer.writerow([usr.get_full_name() or usr.username, usr.cpf or 'N/A', usr.tipo_chave_pix or 'CPF/CNPJ', usr.chave_pix or 'N/A', f"{float(p.candidatura.vaga.valor_diaria or 0):.2f}".replace('.', ','), p.candidatura.vaga.evento.nome, p.candidatura.vaga.funcao])

    return response


@login_required
def exportar_casting_cliente_pdf(request, evento_id):
    empresa = request.user.empresa or Empresa.objects.first()
    evento = get_object_or_404(Evento, id=evento_id, empresa=empresa)
    candidaturas = Candidatura.objects.filter(vaga__evento=evento, status='APROVADO').select_related('usuario', 'vaga')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="casting_{evento.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = [Paragraph(f"Casting Aprovado — {evento.nome}", getSampleStyleSheet()['Heading1'])]

    for cand in candidaturas:
        usr = cand.usuario
        elements.append(Paragraph(f"<b>Nome:</b> {usr.get_full_name() or usr.username} | <b>Função:</b> {cand.vaga.funcao}", getSampleStyleSheet()['Normal']))
        elements.append(Spacer(1, 8))

    doc.build(elements)
    return response


def criar_dados_demo_view(request):
    try:
        call_command('popular_dados')
        return HttpResponse("<h1>✅ BANCO DE DADOS POPULADO!</h1><p><a href='/dashboard/empresa/'>Ir ao Painel</a></p>")
    except Exception as e:
        return HttpResponse(f"<h1>❌ Erro ao povoar banco:</h1><p>{str(e)}</p>")


def status_db_view(request):
    return HttpResponse(f"BD Ativo com {Usuario.objects.count()} usuários.")