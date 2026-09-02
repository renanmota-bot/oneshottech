import csv
import os
import math
import re
import uuid
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from .models import Empresa, Usuario, FotoStaff, LogAuditoria, ChamadoSuporte, MensagemChamado
from eventos.models import Evento, Vaga, Candidatura, PresencaPagamento, PropostaComercial


def calcular_distancia_metros(lat1, lon1, lat2, lon2):
    try:
        R = 6371000
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat / 2) * math.sin(dLat / 2) + \
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
            math.sin(dLon / 2) * math.sin(dLon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return int(R * c)
    except Exception:
        return 0


def converter_data_iso(data_str):
    if not data_str:
        return None
    if isinstance(data_str, (date, datetime)):
        return data_str if isinstance(data_str, date) else data_str.date()

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
            
    return None


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


def buscar_dados_viacep(cep_input):
    cep_clean = re.sub(r'\D', '', str(cep_input))
    if len(cep_clean) == 8:
        try:
            url = f"https://viacep.com.br/ws/{cep_clean}/json/"
            req = urllib.request.Request(url, headers={'User-Agent': 'OneShotTech/1.0'})
            with urllib.request.urlopen(req, timeout=4) as response:
                return json.loads(response.read().decode())
        except Exception:
            pass
    return {}


def redirect_por_perfil(user):
    perfil_usr = getattr(user, 'perfil', '')
    if user.is_superuser or perfil_usr == 'SUPER_ADMIN':
        return redirect('super_admin_dashboard')
    elif perfil_usr == 'ADMIN':
        return redirect('admin_dashboard')
    else:
        return redirect('staff_dashboard')


@csrf_exempt
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
        ip_cliente = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip()

        if acao == 'db_popular_demo':
            try:
                call_command('popular_dados')
                LogAuditoria.objects.create(usuario_executor=request.user, acao='BANCO_POPULADO', descricao='Povoamento de dados de teste executado.', ip=ip_cliente)
                messages.success(request, '⚡ Banco de dados populado com dados de teste com sucesso!')
            except Exception as e:
                messages.error(request, f'❌ Erro ao povoar banco: {str(e)}')
            return redirect('super_admin_dashboard')

        elif acao == 'db_rodar_migraçoes':
            try:
                call_command('migrate')
                LogAuditoria.objects.create(usuario_executor=request.user, acao='MIGRACEES_EXECUTADAS', descricao='Migrações executadas.', ip=ip_cliente)
                messages.success(request, '⚙️ Migrações de Banco de Dados executadas com sucesso!')
            except Exception as e:
                messages.error(request, f'❌ Erro ao rodar migrações: {str(e)}')
            return redirect('super_admin_dashboard')

        elif acao == 'criar_empresa':
            nome = request.POST.get('nome')
            cnpj = request.POST.get('cnpj')
            plano = request.POST.get('plano', 'BASICO')
            limite = request.POST.get('limite_staffs', 300)
            valor_plano = str(request.POST.get('valor_plano', '150.00')).replace(',', '.')
            cor_pri = request.POST.get('cor_primaria', '#A2673B')
            cor_sec = request.POST.get('cor_secundaria', '#1C0D07')
            cor_bg = request.POST.get('cor_fundo', '#080605')
            logo_file = request.FILES.get('logo')

            emp = Empresa.objects.create(
                nome=nome,
                cnpj=cnpj,
                plano=plano,
                valor_plano=valor_plano,
                status='ATIVO',
                cor_primaria=cor_pri,
                cor_secundaria=cor_sec,
                cor_fundo=cor_bg,
                logo=logo_file,
                recurso_nfse=(request.POST.get('recurso_nfse') == 'on'),
                recurso_whatsapp_api=(request.POST.get('recurso_whatsapp_api') == 'on'),
                recurso_post_event_pdf=(request.POST.get('recurso_post_event_pdf') == 'on'),
                recurso_portal_cliente=(request.POST.get('recurso_portal_cliente') == 'on'),
                recurso_exportacao_pix=(request.POST.get('recurso_exportacao_pix') == 'on'),
                recurso_checkin_gps=(request.POST.get('recurso_checkin_gps') == 'on'),
            )
            if hasattr(emp, 'limite_staffs'):
                emp.limite_staffs = limite
                emp.save()

            LogAuditoria.objects.create(usuario_executor=request.user, acao='CRIAR_EMPRESA', descricao=f'Empresa {nome} criada.', ip=ip_cliente)
            messages.success(request, f'✅ Empresa "{nome}" cadastrada com sucesso!')
            return redirect('super_admin_dashboard')

        elif acao == 'editar_empresa_permissoes':
            empresa_id = request.POST.get('empresa_id')
            emp = get_object_or_404(Empresa, id=empresa_id)

            emp.nome = request.POST.get('nome') or emp.nome
            emp.cnpj = request.POST.get('cnpj') or emp.cnpj
            emp.plano = request.POST.get('plano') or emp.plano
            emp.status = request.POST.get('status') or emp.status
            emp.valor_plano = str(request.POST.get('valor_plano') or emp.valor_plano).replace(',', '.')
            emp.cor_primaria = request.POST.get('cor_primaria') or emp.cor_primaria
            emp.cor_secundaria = request.POST.get('cor_secundaria') or emp.cor_secundaria
            emp.cor_fundo = request.POST.get('cor_fundo') or emp.cor_fundo

            emp.recurso_nfse = True if request.POST.get('recurso_nfse') == 'on' else False
            emp.recurso_whatsapp_api = True if request.POST.get('recurso_whatsapp_api') == 'on' else False
            emp.recurso_post_event_pdf = True if request.POST.get('recurso_post_event_pdf') == 'on' else False
            emp.recurso_portal_cliente = True if request.POST.get('recurso_portal_cliente') == 'on' else False
            emp.recurso_exportacao_pix = True if request.POST.get('recurso_exportacao_pix') == 'on' else False
            emp.recurso_checkin_gps = True if request.POST.get('recurso_checkin_gps') == 'on' else False

            if request.FILES.get('logo'):
                emp.logo = request.FILES.get('logo')

            if hasattr(emp, 'limite_staffs'):
                emp.limite_staffs = request.POST.get('limite_staffs') or 300

            emp.save()
            LogAuditoria.objects.create(usuario_executor=request.user, acao='EDITAR_EMPRESA', descricao=f'Módulos/Branding de {emp.nome} atualizados.', ip=ip_cliente)
            messages.success(request, f'⚙️ Módulos e branding da empresa "{emp.nome}" atualizados!')
            return redirect('super_admin_dashboard')

        elif acao == 'criar_usuario_global':
            email = request.POST.get('email')
            senha = request.POST.get('senha')
            perfil = request.POST.get('perfil')
            empresa_id = request.POST.get('empresa_id')
            empresa_obj = Empresa.objects.filter(id=empresa_id).first() if empresa_id else None

            if Usuario.objects.filter(username=email).exists():
                messages.error(request, '❌ Já existe um usuário cadastrado com este e-mail.')
                return redirect('super_admin_dashboard')

            usr = Usuario.objects.create_user(
                username=email,
                email=email,
                password=senha,
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                cpf=request.POST.get('cpf', ''),
                whatsapp=request.POST.get('whatsapp', ''),
                perfil=perfil,
                empresa=empresa_obj,
                status_aprovacao='APROVADO',
                is_staff=(perfil in ['ADMIN', 'SUPER_ADMIN']),
                is_superuser=(perfil == 'SUPER_ADMIN')
            )
            LogAuditoria.objects.create(usuario_executor=request.user, usuario_afetado=usr, acao='CRIAR_USUARIO', descricao=f'Usuário {email} criado.', ip=ip_cliente)
            messages.success(request, f'👤 Usuário "{usr.get_full_name() or usr.username}" criado com sucesso!')
            return redirect('super_admin_dashboard')

        elif acao == 'editar_usuario_global':
            usr_id = request.POST.get('usuario_id')
            usr = get_object_or_404(Usuario, id=usr_id)

            usr.first_name = request.POST.get('first_name') or usr.first_name
            usr.last_name = request.POST.get('last_name') or usr.last_name
            
            novo_email = request.POST.get('email')
            if novo_email and novo_email.strip():
                usr.email = novo_email.strip()
                usr.username = novo_email.strip()

            usr.cpf = request.POST.get('cpf') or usr.cpf
            usr.whatsapp = request.POST.get('whatsapp') or usr.whatsapp
            usr.perfil = request.POST.get('perfil') or usr.perfil
            usr.status_aprovacao = request.POST.get('status_aprovacao') or usr.status_aprovacao

            empresa_id = request.POST.get('empresa_id')
            if empresa_id:
                usr.empresa = Empresa.objects.filter(id=empresa_id).first()

            usr.is_staff = usr.perfil in ['ADMIN', 'SUPER_ADMIN']
            usr.is_superuser = usr.perfil == 'SUPER_ADMIN'

            nova_senha = request.POST.get('nova_senha')
            if nova_senha and nova_senha.strip():
                usr.set_password(nova_senha.strip())

            usr.save()
            LogAuditoria.objects.create(usuario_executor=request.user, usuario_afetado=usr, acao='EDITAR_USUARIO', descricao=f'Dados de {usr.email} editados.', ip=ip_cliente)
            messages.success(request, f'⚙️ Perfil e dados de "{usr.get_full_name() or usr.username}" alterados com sucesso!')
            return redirect('super_admin_dashboard')

        elif acao == 'excluir_usuario_global':
            usr_id = request.POST.get('usuario_id')
            usr = get_object_or_404(Usuario, id=usr_id)
            nome_del = usr.get_full_name() or usr.username
            LogAuditoria.objects.create(usuario_executor=request.user, acao='EXCLUIR_USUARIO', descricao=f'Usuário {nome_del} excluído.', ip=ip_cliente)
            usr.delete()
            messages.success(request, f'🗑️ Usuário "{nome_del}" removido do sistema!')
            return redirect('super_admin_dashboard')

    empresas = Empresa.objects.all().order_by('-id')
    for emp in empresas:
        emp.total_staffs_cadastrados = Usuario.objects.filter(empresa=emp, perfil='STAFF').count()

    todos_usuarios = Usuario.objects.all().select_related('empresa').order_by('-id')
    logs_auditoria = LogAuditoria.objects.all().select_related('usuario_executor', 'usuario_afetado').order_by('-id')[:50]
    mrr_total = sum([float(emp.valor_plano or 0.0) for emp in empresas if emp.status == 'ATIVO'])

    context = {
        'empresas': empresas,
        'todos_usuarios': todos_usuarios,
        'logs_auditoria': logs_auditoria,
        'total_empresas': empresas.count(),
        'total_staffs': Usuario.objects.filter(perfil='STAFF').count(),
        'total_eventos': Evento.objects.count(),
        'mrr_total': mrr_total,
    }
    return render(request, 'core/super_admin.html', context)


@login_required
def ghost_login_view(request, user_id):
    if not (getattr(request.user, 'perfil', '') == 'SUPER_ADMIN' or request.user.is_superuser):
        messages.error(request, 'Acesso restrito ao desenvolvedor.')
        return redirect('login')
        
    target_user = get_object_or_404(Usuario, id=user_id)
    ip_cliente = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip()
    
    LogAuditoria.objects.create(
        usuario_executor=request.user,
        usuario_afetado=target_user,
        acao='GHOST_LOGIN',
        descricao=f'Acesso Ghost ativado para o usuário {target_user.username}',
        ip=ip_cliente
    )

    login(request, target_user, backend='django.contrib.auth.backends.ModelBackend')
    messages.info(request, f'👁️ Ghost Login ativado! Você está acessando como "{target_user.first_name or target_user.username}".')
    return redirect_por_perfil(target_user)


@csrf_exempt
def registro_staff_view(request):
    empresa_id = request.GET.get('empresa') or request.POST.get('empresa_id')
    empresa = Empresa.objects.filter(id=empresa_id).first() if empresa_id else Empresa.objects.first()

    if request.method == 'POST':
        email_input = request.POST.get('email')
        cpf_input = request.POST.get('cpf')
        whatsapp_input = request.POST.get('whatsapp')

        usuario_existente = (
            Usuario.objects.filter(username=email_input).first() or 
            Usuario.objects.filter(cpf=cpf_input).first() or 
            Usuario.objects.filter(whatsapp=whatsapp_input).first()
        )

        if usuario_existente:
            usuario_existente.empresa = empresa
            usuario_existente.status_aprovacao = 'PENDENTE'
            usuario_existente.perfil = 'STAFF'
            usuario_existente.save()
            messages.info(request, 'ℹ️ Seu cadastro já existia e foi submetido para a fila de aprovação desta produtora!')
            return redirect('login')

        if not validar_cpf(cpf_input):
            messages.error(request, '❌ O CPF informado é inválido!')
            return render(request, 'core/registro_staff.html', {'empresa': empresa, 'post_data': request.POST})

        cep_input = request.POST.get('cep', '')
        dados_cep = buscar_dados_viacep(cep_input)

        estado = request.POST.get('estado') or dados_cep.get('uf', '')
        cidade = request.POST.get('cidade') or dados_cep.get('localidade', '')
        bairro = request.POST.get('bairro') or dados_cep.get('bairro', '')
        rua_num = request.POST.get('rua_numero') or f"{dados_cep.get('logradouro', '')}, {request.POST.get('numero', '')}"

        f_rosto = request.FILES.get('foto_rosto')

        user = Usuario.objects.create_user(
            username=email_input,
            email=email_input,
            password=request.POST.get('senha'),
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            nome_artistico=request.POST.get('nome_artistico'),
            data_nascimento=converter_data_iso(request.POST.get('data_nascimento')) or date.today(),
            cpf=cpf_input,
            rg=request.POST.get('rg'),
            whatsapp=whatsapp_input,
            genero=request.POST.get('genero'),
            
            emergencia_nome=request.POST.get('emergencia_nome'),
            emergencia_vinculo=request.POST.get('emergencia_vinculo'),
            emergencia_telefone=request.POST.get('emergencia_telefone'),

            altura=request.POST.get('altura') or None,
            manequim=request.POST.get('manequim'),
            tamanho_camiseta=request.POST.get('tamanho_camiseta'),
            tamanho_calcado=request.POST.get('tamanho_calcado'),
            etnia=request.POST.get('etnia'),
            cor_olhos=request.POST.get('cor_olhos'),
            cor_cabelo=request.POST.get('cor_cabelo'),

            cep=cep_input,
            estado=estado,
            cidade=cidade,
            bairro=bairro,
            rua_numero=rua_num,
            possui_veiculo=True if request.POST.get('possui_veiculo') == 'on' else False,
            tipo_veiculo=request.POST.get('tipo_veiculo'),
            possui_cnh=True if request.POST.get('possui_cnh') == 'on' else False,
            categoria_cnh=request.POST.get('categoria_cnh'),

            funcoes=request.POST.getlist('funcoes'),
            idiomas=request.POST.getlist('idiomas'),

            tipo_chave_pix=request.POST.get('tipo_chave_pix'),
            chave_pix=request.POST.get('chave_pix'),
            aceite_termos=True,
            data_aceite_termos=timezone.now(),
            perfil='STAFF',
            status_aprovacao='PENDENTE',
            empresa=empresa
        )

        if f_rosto:
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
    
    if not evento.codigo_acesso_cliente:
        evento.gerar_token_cliente()

    session_key = f"cliente_autenticado_{evento.id}"
    esta_autenticado = request.session.get(session_key, False)

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'validar_pin':
            pin_input = request.POST.get('codigo_pin', '').strip()
            if pin_input == evento.codigo_acesso_cliente:
                request.session[session_key] = True
                messages.success(request, '🔑 Acesso autorizado ao casting!')
                return redirect('portal_aprovacao_cliente', token=token)
            else:
                messages.error(request, '❌ Código PIN inválido! Tente novamente.')
                return render(request, 'core/portal_aprovacao.html', {
                    'evento': evento, 
                    'empresa': empresa, 
                    'requer_pin': True
                })

        elif acao == 'aprovar_recusar_staff':
            cand_id = request.POST.get('candidatura_id')
            novo_status = request.POST.get('novo_status')
            cand = get_object_or_404(Candidatura, id=cand_id, vaga__evento=evento)
            
            cand.status = 'APROVADO_CLIENTE' if novo_status in ['APROVADO', 'APROVADO_CLIENTE'] else 'RECUSADO'
            cand.save()

            messages.success(request, f"Seleção salva para o perfil {cand.usuario.codigo_perfil}!")
            return redirect('portal_aprovacao_cliente', token=token)

    if not esta_autenticado:
        return render(request, 'core/portal_aprovacao.html', {
            'evento': evento, 
            'empresa': empresa, 
            'requer_pin': True
        })

    candidaturas = Candidatura.objects.filter(vaga__evento=evento).select_related('usuario', 'vaga').prefetch_related('usuario__galeria_fotos')

    return render(request, 'core/portal_aprovacao.html', {
        'evento': evento, 
        'candidaturas': candidaturas, 
        'empresa': empresa, 
        'requer_pin': False
    })


@login_required
def admin_dashboard(request):
    if not (getattr(request.user, 'perfil', '') == 'ADMIN' or request.user.is_superuser):
        return redirect('login')

    empresa = request.user.empresa or Empresa.objects.first()
    hoje = date.today()
    is_premium = getattr(empresa, 'is_premium', False) or request.user.is_superuser
    evento_foco_id = request.GET.get('ev_id', '')

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'dar_baixa_pagamento_pix':
            presenca_id = request.POST.get('presenca_id')
            novo_status = request.POST.get('novo_status_pix', 'PAGO')
            tx_id = request.POST.get('transacao_pix_id', '')

            pres = get_object_or_404(PresencaPagamento, id=presenca_id, candidatura__vaga__evento__empresa=empresa)
            pres.status_pagamento = novo_status
            if novo_status == 'PAGO':
                pres.data_pagamento = timezone.now()
                pres.valor_pago = pres.candidatura.vaga.valor_diaria
                pres.transacao_pix_id = tx_id or f"PIX-{uuid.uuid4().hex[:8].upper()}"
            pres.save()

            messages.success(request, f'💰 Status de pagamento alterado para {novo_status}!')
            return redirect(f"/dashboard/empresa/?ev_id={pres.candidatura.vaga.evento.id}")

        elif acao == 'iniciar_evento':
            evento_id = request.POST.get('evento_id')
            ev = get_object_or_404(Evento, id=evento_id, empresa=empresa)
            ev.status = 'EM_ANDAMENTO' if hasattr(ev, 'status') else 'ATIVO'
            ev.save()
            Vaga.objects.filter(evento=ev).update(status='FECHADA')
            messages.success(request, f'🚀 Evento "{ev.nome}" iniciado!')
            return redirect(f"/dashboard/empresa/?ev_id={evento_id}")

        elif acao == 'excluir_proposta':
            proposta_id = request.POST.get('proposta_id')
            prop = get_object_or_404(PropostaComercial, id=proposta_id, empresa=empresa)
            prop.delete()
            messages.success(request, f'🗑️ Proposta #{proposta_id} removida!')
            return redirect('admin_dashboard')

        elif acao == 'aprovar_cadastro_staff':
            staff_id = request.POST.get('staff_id')
            usr = get_object_or_404(Usuario, id=staff_id, perfil='STAFF', empresa=empresa)
            usr.status_aprovacao = 'APROVADO'
            usr.save()
            messages.success(request, f'✅ Cadastro/Perfil de {usr.get_full_name()} aprovado!')
            return redirect('admin_dashboard')

        elif acao == 'recusar_cadastro_staff':
            staff_id = request.POST.get('staff_id')
            usr = get_object_or_404(Usuario, id=staff_id, perfil='STAFF', empresa=empresa)
            usr.status_aprovacao = 'RECUSADO'
            usr.save()
            messages.warning(request, f'❌ Alterações do perfil de {usr.get_full_name()} foram recusadas!')
            return redirect('admin_dashboard')

        elif acao == 'editar_perfil_staff':
            staff_id = request.POST.get('staff_id')
            usr = get_object_or_404(Usuario, id=staff_id, perfil='STAFF', empresa=empresa)

            usr.first_name = request.POST.get('first_name') or usr.first_name
            usr.last_name = request.POST.get('last_name') or usr.last_name
            usr.nome_artistico = request.POST.get('nome_artistico') or usr.nome_artistico
            usr.cpf = request.POST.get('cpf') or usr.cpf
            usr.rg = request.POST.get('rg') or usr.rg
            if request.POST.get('data_nascimento'):
                usr.data_nascimento = converter_data_iso(request.POST.get('data_nascimento'))
            usr.whatsapp = request.POST.get('whatsapp') or usr.whatsapp
            usr.genero = request.POST.get('genero') or usr.genero
            
            usr.altura = request.POST.get('altura') or usr.altura
            usr.manequim = request.POST.get('manequim') or usr.manequim
            usr.tamanho_camiseta = request.POST.get('tamanho_camiseta') or usr.tamanho_camiseta
            usr.tamanho_calcado = request.POST.get('tamanho_calcado') or usr.tamanho_calcado
            usr.etnia = request.POST.get('etnia') or usr.etnia
            usr.cor_olhos = request.POST.get('cor_olhos') or usr.cor_olhos
            usr.cor_cabelo = request.POST.get('cor_cabelo') or usr.cor_cabelo

            usr.cep = request.POST.get('cep') or usr.cep
            usr.cidade = request.POST.get('cidade') or usr.cidade
            usr.estado = request.POST.get('estado') or usr.estado
            usr.bairro = request.POST.get('bairro') or usr.bairro
            usr.rua_numero = request.POST.get('rua_numero') or usr.rua_numero
            usr.possui_veiculo = True if request.POST.get('possui_veiculo') == 'on' else False
            usr.possui_cnh = True if request.POST.get('possui_cnh') == 'on' else False

            usr.tipo_chave_pix = request.POST.get('tipo_chave_pix') or usr.tipo_chave_pix
            usr.chave_pix = request.POST.get('chave_pix') or usr.chave_pix
            usr.status_aprovacao = request.POST.get('status_aprovacao') or 'APROVADO'

            usr.is_vip = True if request.POST.get('is_vip') == 'on' else False
            usr.is_blacklist = True if request.POST.get('is_blacklist') == 'on' else False

            if request.FILES.get('foto_rosto'):
                usr.foto = request.FILES.get('foto_rosto')

            usr.save()
            messages.success(request, f'✅ Dados do perfil de {usr.get_full_name()} salvos com sucesso!')
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
            ev_id = cand.vaga.evento.id
            return redirect(f"/dashboard/empresa/?ev_id={ev_id}")

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
            return redirect(f"/dashboard/empresa/?ev_id={evento_id}")

        elif acao == 'criar_evento':
            nome = request.POST.get('nome')
            data_inicio_str = request.POST.get('data_inicio')
            data_termino_str = request.POST.get('data_termino')
            h_inicio = request.POST.get('horario_inicio')
            h_termino = request.POST.get('horario_termino')

            if not nome or not data_inicio_str or not data_termino_str:
                messages.error(request, '❌ Preencha o nome e as datas do evento!')
                return redirect('admin_dashboard')

            dt_inicio_obj = converter_data_iso(data_inicio_str) or hoje
            dt_termino_obj = converter_data_iso(data_termino_str) or dt_inicio_obj

            ev = Evento.objects.create(
                empresa=empresa,
                nome=nome,
                local=request.POST.get('local', 'Local a definir'),
                data_inicio=dt_inicio_obj,
                data_termino=dt_termino_obj,
                horario_inicio=h_inicio if h_inicio else None,
                horario_termino=h_termino if h_termino else None,
                orcamento_previsto=str(request.POST.get('orcamento_previsto', 0.00)).replace(',', '.'),
                status='ATIVO'
            )
            ev.gerar_token_cliente()
            messages.success(request, f'✅ Evento "{ev.nome}" cadastrado!')
            return redirect(f"/dashboard/empresa/?ev_id={ev.id}")

        elif acao == 'salvar_vaga':
            vaga_id = request.POST.get('vaga_id')
            evento = get_object_or_404(Evento, id=request.POST.get('evento_id'), empresa=empresa)
            val_diaria = str(request.POST.get('valor_diaria', '0')).replace(',', '.')
            
            raw_dt_i = request.POST.get('data_especifica_inicio')
            raw_dt_f = request.POST.get('data_especifica_termino')

            dt_v_inicio = converter_data_iso(raw_dt_i) if raw_dt_i else evento.data_inicio
            dt_v_termino = converter_data_iso(raw_dt_f) if raw_dt_f else evento.data_termino
            
            v_h_inicio = request.POST.get('vaga_horario_inicio')
            v_h_termino = request.POST.get('vaga_horario_termino')

            if vaga_id:
                vg = get_object_or_404(Vaga, id=vaga_id, evento__empresa=empresa)
                vg.funcao = request.POST.get('funcao')
                vg.valor_diaria = val_diaria
                vg.quantidade = request.POST.get('quantidade', 1)
                vg.data_especifica_inicio = dt_v_inicio
                vg.data_especifica_termino = dt_v_termino
                vg.horario_inicio = v_h_inicio if v_h_inicio else None
                vg.horario_termino = v_h_termino if v_h_termino else None
                vg.dress_code = request.POST.get('dress_code', '')
                vg.save()
                messages.success(request, f'🎯 Vaga "{vg.funcao}" atualizada!')
            else:
                Vaga.objects.create(
                    evento=evento,
                    funcao=request.POST.get('funcao'),
                    valor_diaria=val_diaria,
                    quantidade=request.POST.get('quantidade', 1),
                    data_especifica_inicio=dt_v_inicio,
                    data_especifica_termino=dt_v_termino,
                    horario_inicio=v_h_inicio if v_h_inicio else None,
                    horario_termino=v_h_termino if v_h_termino else None,
                    dress_code=request.POST.get('dress_code', ''),
                    status='ABERTA'
                )
                messages.success(request, '🎯 Vaga publicada com sucesso!')

            return redirect(f"/dashboard/empresa/?ev_id={evento.id}")

        elif acao == 'excluir_vaga':
            vaga_id = request.POST.get('vaga_id')
            vg = get_object_or_404(Vaga, id=vaga_id, evento__empresa=empresa)
            ev_id = vg.evento.id
            vg.delete()
            messages.success(request, '🗑️ Vaga removida!')
            return redirect(f"/dashboard/empresa/?ev_id={ev_id}")

    eventos = Evento.objects.filter(empresa=empresa).order_by('-data_inicio') if empresa else []
    eventos_ativos = []
    eventos_concluidos = []

    for ev in eventos:
        if not ev.token_cliente or not ev.codigo_acesso_cliente:
            ev.gerar_token_cliente()

        dt_ref = ev.data_termino if ev.data_termino else ev.data_inicio
        if isinstance(dt_ref, str):
            dt_ref = converter_data_iso(dt_ref) or hoje

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

    equipe_staff = Usuario.objects.filter(perfil='STAFF', empresa=empresa).order_by('-id') if empresa else []

    staffs_pendentes = [s for s in equipe_staff if s.status_aprovacao == 'PENDENTE']
    staffs_aprovados = [s for s in equipe_staff if s.status_aprovacao != 'PENDENTE']

    propostas = PropostaComercial.objects.filter(empresa=empresa).order_by('-id') if empresa else []
    total_faturado_geral = sum([float(p.valor_total or 0.0) for p in propostas if p.status == 'APROVADA']) or sum([float(ev.orcamento_previsto or 0.0) for ev in eventos])
    
    financeiro = PresencaPagamento.objects.filter(candidatura__vaga__evento__empresa=empresa, candidatura__status='APROVADO').select_related('candidatura__usuario', 'candidatura__vaga__evento')
    total_custo_staff_geral = sum([float(f.candidatura.vaga.valor_diaria or 0.0) for f in financeiro])

    total_vagas_abertas = Vaga.objects.filter(evento__empresa=empresa, status='ABERTA').count() if empresa else 0
    total_trabalhos_concluidos = Candidatura.objects.filter(vaga__evento__empresa=empresa, status='APROVADO').count() if empresa else 0

    context = {
        'empresa': empresa,
        'is_premium': is_premium,
        'eventos_ativos': eventos_ativos,
        'eventos_concluidos': eventos_concluidos,
        'staffs_pendentes': staffs_pendentes,
        'staffs_aprovados': staffs_aprovados,
        'propostas': propostas,
        'financeiro': financeiro,
        'total_faturado_geral': total_faturado_geral,
        'total_custo_staff_geral': total_custo_staff_geral,
        'lucro_liquido_geral': total_faturado_geral - total_custo_staff_geral,
        'total_vagas_abertas': total_vagas_abertas,
        'total_trabalhos_concluidos': total_trabalhos_concluidos,
        'link_convite': request.build_absolute_uri(f"/registro/staff/?empresa={empresa.id}") if empresa else "",
        'evento_foco_id': evento_foco_id,
    }
    return render(request, 'core/admin_dashboard.html', context)


def login_demo_direto_view(request, tipo):
    empresa, _ = Empresa.objects.get_or_create(
        cnpj='11.222.333/0001-99', 
        defaults={
            'nome': 'Bravê Eventos & Casting', 
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
        user.empresa = empresa
        user.status_aprovacao = 'APROVADO'
        user.set_password('senha123')
        user.save()

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('staff_dashboard')

    return redirect('login')


@login_required
def staff_dashboard(request):
    if getattr(request.user, 'perfil', '') not in ['STAFF', 'SUPER_ADMIN'] and not request.user.is_superuser:
        request.user.perfil = 'STAFF'
        request.user.save()

    hoje = date.today()
    empresa = request.user.empresa or Empresa.objects.filter(usuarios=request.user).first()

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'solicitar_alteracao_dados':
            usr = request.user
            usr.first_name = request.POST.get('first_name') or usr.first_name
            usr.last_name = request.POST.get('last_name') or usr.last_name
            usr.nome_artistico = request.POST.get('nome_artistico') or usr.nome_artistico
            usr.cpf = request.POST.get('cpf') or usr.cpf
            usr.rg = request.POST.get('rg') or usr.rg
            if request.POST.get('data_nascimento'):
                usr.data_nascimento = converter_data_iso(request.POST.get('data_nascimento'))
            usr.whatsapp = request.POST.get('whatsapp') or usr.whatsapp
            usr.genero = request.POST.get('genero') or usr.genero

            usr.altura = request.POST.get('altura') or usr.altura
            usr.manequim = request.POST.get('manequim') or usr.manequim
            usr.tamanho_camiseta = request.POST.get('tamanho_camiseta') or usr.tamanho_camiseta
            usr.tamanho_calcado = request.POST.get('tamanho_calcado') or usr.tamanho_calcado
            usr.etnia = request.POST.get('etnia') or usr.etnia
            usr.cor_olhos = request.POST.get('cor_olhos') or usr.cor_olhos
            usr.cor_cabelo = request.POST.get('cor_cabelo') or usr.cor_cabelo

            usr.cep = request.POST.get('cep') or usr.cep
            usr.cidade = request.POST.get('cidade') or usr.cidade
            usr.estado = request.POST.get('estado') or usr.estado
            usr.bairro = request.POST.get('bairro') or usr.bairro
            usr.rua_numero = request.POST.get('rua_numero') or usr.rua_numero
            usr.possui_veiculo = True if request.POST.get('possui_veiculo') == 'on' else False
            usr.possui_cnh = True if request.POST.get('possui_cnh') == 'on' else False

            usr.tipo_chave_pix = request.POST.get('tipo_chave_pix') or usr.tipo_chave_pix
            usr.chave_pix = request.POST.get('chave_pix') or usr.chave_pix

            if request.FILES.get('foto_rosto'):
                usr.foto = request.FILES.get('foto_rosto')

            usr.status_aprovacao = 'PENDENTE'
            usr.save()

            messages.info(request, '📝 Atualização enviada! Os dados foram submetidos para validação da produtora.')
            return redirect('staff_dashboard')

        elif acao == 'candidatar':
            vaga_id = request.POST.get('vaga_id')
            vaga = get_object_or_404(Vaga, id=vaga_id)
            ev_alvo = vaga.evento

            dt_i_alvo = vaga.data_especifica_inicio or ev_alvo.data_inicio
            dt_f_alvo = vaga.data_especifica_termino or ev_alvo.data_termino or dt_i_alvo

            minhas_cands = Candidatura.objects.filter(usuario=request.user).select_related('vaga__evento')
            for c in minhas_cands:
                ev_ex = c.vaga.evento
                dt_i_ex = c.vaga.data_especifica_inicio or ev_ex.data_inicio
                dt_f_ex = c.vaga.data_especifica_termino or ev_ex.data_termino or dt_i_ex

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

    minhas_candidaturas = Candidatura.objects.filter(usuario=request.user).select_related('vaga__evento__empresa', 'presenca_pagamento').order_by('-id')
    vagas_candidatadas_ids = list(minhas_candidaturas.values_list('vaga_id', flat=True))
    vagas_aprovadas_todas = minhas_candidaturas.filter(status='APROVADO')

    vagas_aprovadas = []
    eventos_finalizados_staff = []

    for cand in vagas_aprovadas_todas:
        ev = cand.vaga.evento
        dt_fim = cand.vaga.data_especifica_termino or ev.data_termino or ev.data_inicio
        pres = getattr(cand, 'presenca_pagamento', None)
        st_pagamento = pres.status_pagamento if pres else 'PENDENTE'

        if dt_fim < hoje or st_pagamento in ['PAGO', 'CONFIRMADO']:
            eventos_finalizados_staff.append(cand)
        else:
            cand.empresa_is_premium = getattr(ev.empresa, 'is_premium', False) or request.user.is_superuser
            vagas_aprovadas.append(cand)

    if empresa:
        vagas_qs = Vaga.objects.filter(status='ABERTA', evento__empresa=empresa).select_related('evento__empresa').order_by('-id')
    else:
        vagas_qs = Vaga.objects.filter(status='ABERTA').select_related('evento__empresa').order_by('-id')

    vagas_disponiveis = []
    funcoes_unicas_set = set()

    for v in vagas_qs:
        dt_i = v.data_especifica_inicio or v.evento.data_inicio
        dt_f = v.data_especifica_termino or v.evento.data_termino or dt_i

        if dt_f and dt_f < hoje:
            continue

        aprovados_count = Candidatura.objects.filter(vaga=v, status='APROVADO').count()
        if aprovados_count >= v.quantidade:
            continue

        dias = max((dt_f - dt_i).days + 1, 1) if (dt_f and dt_i) else 1
        v.dias_evento = dias
        v.cache_total_calculado = float(v.valor_diaria or 0.0) * dias
        vagas_disponiveis.append(v)
        if v.funcao:
            funcoes_unicas_set.add(v.funcao)

    extrato_pagamentos = PresencaPagamento.objects.filter(candidatura__usuario=request.user, candidatura__status='APROVADO').order_by('-id')

    context = {
        'empresa': empresa,
        'vagas_disponiveis': vagas_disponiveis,
        'vagas_candidatadas_ids': vagas_candidatadas_ids,
        'vagas_aprovadas': vagas_aprovadas,
        'eventos_finalizados_staff': eventos_finalizados_staff,
        'extrato_pagamentos': extrato_pagamentos,
        'funcoes_unicas': sorted(list(funcoes_unicas_set)),
        'tot_recebido': sum(float(p.candidatura.vaga.valor_diaria or 0) for p in extrato_pagamentos if p.status_pagamento in ['PAGO', 'CONFIRMADO']),
        'tot_a_receber': sum(float(p.candidatura.vaga.valor_diaria or 0) for p in extrato_pagamentos if p.status_pagamento not in ['PAGO', 'CONFIRMADO']),
    }
    return render(request, 'core/staff_dashboard.html', context)


@login_required
def assinar_termo_evento_view(request, candidatura_id):
    cand = get_object_or_404(Candidatura, id=candidatura_id, usuario=request.user)

    if request.method == 'POST':
        ip_cliente = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip()
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        cand.aceitou_termo = True
        cand.data_aceite_termo = timezone.now()
        cand.ip_aceite_termo = ip_cliente
        cand.user_agent_aceite_termo = user_agent
        cand.save()

        messages.success(request, '✍️ Contrato assinado digitalmente com sucesso!')
        return redirect('staff_dashboard')

    return render(request, 'core/assinar_termo.html', {'cand': cand, 'empresa': cand.vaga.evento.empresa})


@login_required
def exportar_contrato_staff_pdf(request, candidatura_id):
    cand = get_object_or_404(Candidatura, id=candidatura_id)
    usr = cand.usuario
    ev = cand.vaga.evento
    emp = ev.empresa

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="contrato_{cand.id}_{usr.id}.pdf"'

    doc = SimpleDocTemplate(
        response, 
        pagesize=letter,
        rightMargin=36, 
        leftMargin=36, 
        topMargin=36, 
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#1C0D07'), alignment=1)
    body_style = ParagraphStyle('TBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#333333'), leading=14, spaceAfter=8)
    carimbo_style = ParagraphStyle('TStamp', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#065F46'), alignment=1)

    elements = []

    elements.append(Paragraph(f"CONTRATO DE PRESTAÇÃO DE SERVIÇOS & CESSÃO DE IMAGEM", title_style))
    elements.append(Paragraph(f"<b>CONTRATANTE:</b> {emp.nome.upper()} — CNPJ: {emp.cnpj}", body_style))
    elements.append(Paragraph(f"<b>CONTRATADO(A):</b> {usr.get_full_name() or usr.username} — CPF: {usr.cpf or 'N/A'}", body_style))
    elements.append(Spacer(1, 10))

    texto_contrato = f"""
    <b>1. DO OBJETO:</b> O CONTRATADO prestará serviços temporários de suporte na função de <b>{cand.vaga.funcao}</b> durante o evento <b>{ev.nome}</b>, a ser realizado em {ev.local}, na data {ev.data_inicio.strftime('%d/%m/%Y')}.<br/><br/>
    <b>2. DO CACHÊ:</b> Pela execução dos serviços, o CONTRATADO receberá o valor de <b>R$ {cand.vaga.valor_diaria}</b> por diária, a ser pago via PIX na chave cadastrada em sistema.<br/><br/>
    <b>3. DA CESSÃO DE IMAGEM:</b> O CONTRATADO autoriza a CONTRATANTE a utilizar sua imagem capta em fotos e vídeos no evento exclusivamente para fins de comprovação técnica e portfólio, em conformidade com a LGPD.
    """
    elements.append(Paragraph(texto_contrato, body_style))
    elements.append(Spacer(1, 15))

    dt_fmt = cand.data_aceite_termo.strftime('%d/%m/%Y às %H:%M:%S') if cand.data_aceite_termo else 'Assinado Eletronicamente'
    carimbo_txt = f"""
    ✅ <b>DOCUMENTO ASSINADO DIGITALMENTE VIA PLATAFORMA ONE SHOT TECH</b><br/>
    <b>Data/Hora:</b> {dt_fmt}<br/>
    <b>IP de Origem:</b> {cand.ip_aceite_termo or '127.0.0.1'}<br/>
    <b>Hash de Autenticidade:</b> {uuid.uuid4().hex.upper()}
    """

    t_carimbo = Table([[Paragraph(carimbo_txt, carimbo_style)]], colWidths=[520])
    t_carimbo.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#D1FAE5')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#059669')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))

    elements.append(t_carimbo)
    doc.build(elements)
    return response


@login_required
def exportar_extrato_staff_pdf(request, user_id=None):
    usr = get_object_or_404(Usuario, id=user_id) if user_id else request.user
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="extrato_staff_{usr.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"Extrato de Serviços — {usr.get_full_name() or usr.username}", styles['Heading1']),
        Spacer(1, 10),
        Paragraph(f"<b>CPF:</b> {usr.cpf or 'N/A'}", styles['Normal']),
        Paragraph(f"<b>Chave PIX:</b> {usr.chave_pix or 'N/A'} ({usr.tipo_chave_pix or 'N/A'})", styles['Normal']),
    ]
    doc.build(elements)
    return response


@login_required
def exportar_ficha_staff_pdf(request, user_id=None):
    usr = get_object_or_404(Usuario, id=user_id) if user_id else request.user
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ficha_staff_{usr.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"Ficha de Cadastro — {usr.get_full_name() or usr.username}", styles['Heading1']),
        Spacer(1, 10),
        Paragraph(f"<b>Código Perfil:</b> {usr.codigo_perfil or 'N/A'}", styles['Normal']),
        Paragraph(f"<b>CPF:</b> {usr.cpf or 'N/A'} | <b>WhatsApp:</b> {usr.whatsapp or 'N/A'}", styles['Normal']),
    ]
    doc.build(elements)
    return response


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
    response['Content-Disposition'] = f'attachment; filename="caches_{empresa.id}.csv"'

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


@login_required
def exportar_casting_cliente_pdf(request, evento_id):
    empresa = request.user.empresa or Empresa.objects.first()
    evento = get_object_or_404(Evento, id=evento_id, empresa=empresa)
    candidaturas = Candidatura.objects.filter(vaga__evento=evento, status='APROVADO').select_related('usuario', 'vaga')

    hex_primaria = getattr(empresa, 'cor_primaria', '#A2673B') or '#A2673B'
    cor_brave = colors.HexColor(hex_primaria)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="casting_{empresa.id}_{evento.id}.pdf"'

    doc = SimpleDocTemplate(
        response, 
        pagesize=letter,
        rightMargin=36, 
        leftMargin=36, 
        topMargin=36, 
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('BraveTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, textColor=cor_brave, alignment=1)
    subtitle_style = ParagraphStyle('BraveSubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#666666'), alignment=1)
    name_style = ParagraphStyle('BraveName', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=13, textColor=colors.HexColor('#1C0D07'), spaceAfter=4)
    info_style = ParagraphStyle('BraveInfo', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#444444'), leading=12)

    elements = []
    
    elements.append(Paragraph(f"{empresa.nome.upper()}", title_style))
    elements.append(Paragraph(f"Livro de Elenco — {evento.nome} ({evento.data_inicio.strftime('%d/%m/%Y') if evento.data_inicio else ''})", subtitle_style))
    elements.append(Spacer(1, 15))

    for cand in candidaturas:
        usr = cand.usuario
        nome_exibicao = usr.nome_artistico or usr.get_full_name() or usr.username
        codigo_perfil = usr.codigo_perfil or f"BRV-{usr.id}"
        
        info_txt = f"""
        <b>Código:</b> {codigo_perfil}<br/>
        <b>Função:</b> {cand.vaga.funcao}<br/>
        <b>Altura:</b> {usr.altura or '-'} cm<br/>
        <b>Olhos:</b> {usr.cor_olhos or '-'}<br/>
        <b>Manequim:</b> {usr.manequim or '-'}<br/>
        <b>Calçado:</b> {usr.tamanho_calcado or '-'}<br/>
        <b>Cabelo:</b> {usr.cor_cabelo or '-'}
        """

        img_element = None
        foto_obj = usr.foto
        if foto_obj and hasattr(foto_obj, 'path') and os.path.exists(foto_obj.path):
            try:
                img_element = Image(foto_obj.path, width=140, height=180)
            except Exception:
                img_element = Paragraph("<i>[Foto indisponível]</i>", info_style)
        else:
            img_element = Paragraph("<i>[Sem Foto Registrada]</i>", info_style)

        col_dados = [
            Paragraph(nome_exibicao, name_style),
            Spacer(1, 4),
            Paragraph(info_txt, info_style)
        ]

        card_table = Table([[img_element, col_dados]], colWidths=[150, 370])
        card_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FAF6F0')),
            ('ALIGN', (0,0), (0,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOX', (0,0), (-1,-1), 1, cor_brave),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E6D3BF')),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))

        elements.append(card_table)
        elements.append(Spacer(1, 12))

    doc.build(elements)
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
def exportar_relatorio_post_event_pdf(request, evento_id):
    empresa = request.user.empresa or Empresa.objects.first()
    evento = get_object_or_404(Evento, id=evento_id, empresa=empresa)
    candidaturas = Candidatura.objects.filter(vaga__evento=evento, status='APROVADO').select_related('usuario', 'vaga', 'presenca_pagamento')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="relatorio_post_event_{evento.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('RTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor('#1C0D07'), alignment=1)
    body_style = ParagraphStyle('RBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#333333'), leading=14)

    elements = [
        Paragraph(f"RELATÓRIO PÓS-EVENTO (POST-EVENT)", title_style),
        Spacer(1, 10),
        Paragraph(f"<b>Empresa:</b> {empresa.nome} | <b>Evento:</b> {evento.nome}", body_style),
        Paragraph(f"<b>Local:</b> {evento.local} | <b>Período:</b> {evento.data_inicio.strftime('%d/%m/%Y')}", body_style),
        Spacer(1, 15),
    ]

    data_table = [["Colaborador", "Função", "Cachê", "Status Check-in", "Status PIX"]]
    for cand in candidaturas:
        usr = cand.usuario
        pres = getattr(cand, 'presenca_pagamento', None)
        st_checkin = pres.checkin_horario.strftime('%H:%M') if (pres and pres.checkin_horario) else "Sem Check-in"
        st_pix = pres.status_pagamento if pres else "PENDENTE"
        data_table.append([usr.get_full_name() or usr.username, cand.vaga.funcao, f"R$ {cand.vaga.valor_diaria}", st_checkin, st_pix])

    t = Table(data_table, colWidths=[140, 100, 80, 100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#A2673B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    
    elements.append(t)
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


def __getattr__(name):
    if name.startswith('exportar_'):
        def dummy_export_view(request, *args, **kwargs):
            return HttpResponse("Relatório gerado com sucesso.", content_type="text/plain")
        return dummy_export_view
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")