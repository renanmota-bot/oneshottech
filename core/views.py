from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from .models import Empresa, Usuario, ChamadoSuporte, MensagemChamado
from .forms import RegistroStaffForm
from eventos.models import Evento, Vaga, Candidatura, PresencaPagamento
from datetime import date
import math
import re
import urllib.parse
import json
import urllib.request

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def obter_presenca(candidatura):
    """Retorna o objeto PresencaPagamento de forma segura sem estourar exceções."""
    pres = getattr(candidatura, 'presenca_pagamento', None)
    if pres is None:
        return None
    if hasattr(pres, 'first'):
        return pres.first()
    return pres

def obter_lat_lng_endereco(endereco):
    try:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(endereco)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'OneShotTech/1.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if data and len(data) > 0:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        pass
    return None, None

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

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
            messages.error(request, 'Usuário ou senha inválidos.')

    return render(request, 'core/login.html')

def registro_staff_view(request):
    empresa_id = request.GET.get('empresa')
    empresa = Empresa.objects.filter(id=empresa_id).first() if empresa_id else None

    if request.method == 'POST':
        form = RegistroStaffForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['senha'])
            user.perfil = 'STAFF'
            if empresa:
                user.empresa = empresa
            user.save()
            
            login(request, user)
            messages.success(request, 'Cadastro realizado com sucesso!')
            return redirect('staff_dashboard')
        else:
            messages.error(request, 'Por favor, envie a foto de perfil obrigatória.')
    else:
        form = RegistroStaffForm()

    return render(request, 'core/registro_staff.html', {'form': form, 'empresa': empresa})

def logout_view(request):
    logout(request)
    return redirect('login')

def redirect_por_perfil(user):
    if user.perfil == 'SUPER_ADMIN' or user.is_superuser:
        return redirect('super_admin_dashboard')
    elif user.perfil == 'ADMIN':
        return redirect('admin_dashboard')
    else:
        return redirect('staff_dashboard')

@login_required
def super_admin_dashboard(request):
    if not (request.user.perfil == 'SUPER_ADMIN' or request.user.is_superuser):
        return redirect('login')
        
    if request.method == 'POST':
        acao = request.POST.get('acao')
        if acao == 'criar_empresa':
            nome_emp = request.POST.get('nome_empresa')
            cnpj_emp = request.POST.get('cnpj')
            valor_p = request.POST.get('valor_plano', 150.00)
            plano_p = request.POST.get('plano_empresa', 'BASICO')
            email_admin = request.POST.get('email_admin')
            senha_admin = request.POST.get('senha_admin')
            nome_admin = request.POST.get('nome_admin', f'Admin {nome_emp}')

            if Empresa.objects.filter(cnpj=cnpj_emp).exists():
                messages.error(request, 'CNPJ/CPF já existente!')
            elif Usuario.objects.filter(email=email_admin).exists():
                messages.error(request, 'E-mail de admin já existente!')
            else:
                emp = Empresa.objects.create(
                    nome=nome_emp, 
                    cnpj=cnpj_emp, 
                    valor_plano=valor_p, 
                    plano=plano_p, 
                    status='ATIVO'
                )
                Usuario.objects.create_user(
                    username=email_admin, 
                    email=email_admin, 
                    password=senha_admin, 
                    first_name=nome_admin, 
                    empresa=emp, 
                    perfil='ADMIN', 
                    is_staff=True
                )
                messages.success(request, f'Empresa #{emp.id} criada com sucesso!')
            return redirect('super_admin_dashboard')

        elif acao == 'alterar_status_empresa':
            emp = get_object_or_404(Empresa, id=request.POST.get('empresa_id'))
            emp.status = request.POST.get('status')
            emp.plano = request.POST.get('plano')
            novo_val = request.POST.get('valor_plano')
            if novo_val: 
                emp.valor_plano = novo_val
            emp.save()
            messages.success(request, f'Empresa #{emp.id} atualizada com sucesso!')
            return redirect('super_admin_dashboard')

        elif acao == 'alternar_bloqueio':
            emp = get_object_or_404(Empresa, id=request.POST.get('empresa_id'))
            if emp.status == 'BLOQUEADO':
                emp.status = 'ATIVO'
                messages.success(request, f'Empresa #{emp.id} DESBLOQUEADA!')
            else:
                emp.status = 'BLOQUEADO'
                messages.warning(request, f'Empresa #{emp.id} BLOQUEADA com sucesso!')
            emp.save()
            return redirect('super_admin_dashboard')

        elif acao == 'criar_usuario_global':
            nome_u = request.POST.get('nome')
            email_u = request.POST.get('email')
            senha_u = request.POST.get('senha')
            perfil_u = request.POST.get('perfil')
            emp_id_u = request.POST.get('empresa_id')
            emp_u = Empresa.objects.filter(id=emp_id_u).first() if emp_id_u else None

            if Usuario.objects.filter(username=email_u).exists():
                messages.error(request, 'E-mail já cadastrado!')
            else:
                Usuario.objects.create_user(username=email_u, email=email_u, password=senha_u, first_name=nome_u, perfil=perfil_u, empresa=emp_u)
                messages.success(request, f'Usuário {nome_u} criado!')
            return redirect('super_admin_dashboard')

        elif acao == 'editar_usuario_global':
            usr = get_object_or_404(Usuario, id=request.POST.get('usuario_id'))
            usr.first_name = request.POST.get('nome', usr.first_name)
            usr.email = request.POST.get('email', usr.email)
            usr.username = request.POST.get('email', usr.username)
            usr.perfil = request.POST.get('perfil', usr.perfil)
            
            emp_id_u = request.POST.get('empresa_id')
            usr.empresa = Empresa.objects.filter(id=emp_id_u).first() if emp_id_u else None

            senha_u = request.POST.get('senha')
            if senha_u and senha_u.strip():
                usr.set_password(senha_u.strip())

            usr.save()
            messages.success(request, f'Usuário #{usr.id} - {usr.first_name} atualizado com sucesso!')
            return redirect('super_admin_dashboard')

        elif acao == 'responder_chamado':
            chamado = get_object_or_404(ChamadoSuporte, id=request.POST.get('chamado_id'))
            msg_texto = request.POST.get('mensagem')
            if msg_texto and msg_texto.strip():
                MensagemChamado.objects.create(chamado=chamado, remetente=request.user, mensagem=msg_texto.strip())
            chamado.status = request.POST.get('status')
            chamado.save()
            messages.success(request, f'Chamado #{chamado.id} atualizado!')
            return redirect('super_admin_dashboard')

    empresas = Empresa.objects.all().order_by('-id')
    usuarios_qs = Usuario.objects.all().select_related('empresa').order_by('-id')
    chamados_qs = ChamadoSuporte.objects.all().prefetch_related('mensagens', 'empresa').order_by('-id')

    busca_usr = request.GET.get('busca_usuario', '').strip()
    filtro_perfil = request.GET.get('filtro_perfil', '').strip()

    if busca_usr:
        usuarios_qs = usuarios_qs.filter(first_name__icontains=busca_usr) | usuarios_qs.filter(email__icontains=busca_usr)
    if filtro_perfil:
        usuarios_qs = usuarios_qs.filter(perfil=filtro_perfil)

    filtro_status_chamado = request.GET.get('filtro_chamado', '').strip()
    if filtro_status_chamado:
        chamados_qs = chamados_qs.filter(status=filtro_status_chamado)

    empresas_ativas = [e for e in empresas if e.status == 'ATIVO']
    empresas_bloqueadas = [e for e in empresas if e.status == 'BLOQUEADO']
    empresas_inadimplentes = [e for e in empresas if e.status == 'INADIMPLENTE']

    total_mrr = sum([e.valor_plano for e in empresas_ativas])
    total_arr = total_mrr * 12
    arpu = (total_mrr / len(empresas_ativas)) if empresas_ativas else 0.00

    total_eventos_globais = Evento.objects.count()
    total_vagas_globais = Vaga.objects.count()
    chamados_abertos = ChamadoSuporte.objects.filter(status='ABERTO').count()

    context = {
        'empresas': empresas,
        'usuarios': usuarios_qs,
        'chamados': chamados_qs,
        'total_empresas': empresas.count(),
        'total_empresas_ativas': len(empresas_ativas),
        'total_empresas_bloqueadas': len(empresas_bloqueadas),
        'total_empresas_inadimplentes': len(empresas_inadimplentes),
        'total_usuarios': Usuario.objects.count(),
        'total_mrr': total_mrr,
        'total_arr': total_arr,
        'arpu': arpu,
        'total_eventos_globais': total_eventos_globais,
        'total_vagas_globais': total_vagas_globais,
        'chamados_abertos': chamados_abertos,
        'busca_usr': busca_usr,
        'filtro_perfil': filtro_perfil,
        'filtro_chamado': filtro_status_chamado,
    }
    return render(request, 'core/super_admin.html', context)

@login_required
def ghost_login_view(request, user_id):
    if not (request.user.perfil == 'SUPER_ADMIN' or request.user.is_superuser):
        return redirect('login')
        
    target_user = get_object_or_404(Usuario, id=user_id)
    login(request, target_user, backend='django.contrib.auth.backends.ModelBackend')
    messages.info(request, f'👁️ Acesso Ghost ativado: Você está como "{target_user.first_name or target_user.username}"')
    return redirect_por_perfil(target_user)

@login_required
def admin_dashboard(request):
    if not (request.user.perfil == 'ADMIN' or request.user.is_superuser):
        return redirect('login')

    empresa = request.user.empresa or Empresa.objects.first()

    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        if acao == 'atualizar_empresa':
            if empresa:
                empresa.whatsapp = request.POST.get('whatsapp', empresa.whatsapp)
                empresa.inscricao_estadual = request.POST.get('inscricao_estadual', empresa.inscricao_estadual)
                empresa.save()
                messages.success(request, 'Dados cadastrais da empresa atualizados!')
            return redirect('admin_dashboard')

        elif acao == 'emitir_nota_fiscal':
            if not empresa or empresa.plano not in ['PRO', 'PREMIUM']:
                messages.error(request, '🔒 Recurso Bloqueado: A emissão de Nota Fiscal está disponível apenas nos planos PRO e PREMIUM.')
                return redirect('admin_dashboard')
            
            val_nf = request.POST.get('valor_nf')
            tomador = request.POST.get('tomador_nome')
            messages.success(request, f'📄 Solicitação de Nota Fiscal Eletrônica no valor de R$ {val_nf} para "{tomador}" enviada com sucesso ao lote de processamento!')
            return redirect('admin_dashboard')

        elif acao == 'criar_evento':
            endereco_local = request.POST.get('local')
            lat_auto, lng_auto = obter_lat_lng_endereco(endereco_local)

            Evento.objects.create(
                empresa=empresa,
                nome=request.POST.get('nome'),
                local=endereco_local,
                latitude=lat_auto,
                longitude=lng_auto,
                dress_code=request.POST.get('dress_code'),
                data_inicio=request.POST.get('data_inicio'),
                data_fim=request.POST.get('data_fim'),
                hora_inicio=request.POST.get('hora_inicio') or None,
                hora_fim=request.POST.get('hora_fim') or None
            )
            messages.success(request, 'Evento criado com Dress Code e coordenadas GPS!')
            return redirect('admin_dashboard')

        elif acao == 'criar_vaga':
            evento = get_object_or_404(Evento, id=request.POST.get('evento_id'), empresa=empresa)
            Vaga.objects.create(
                evento=evento,
                funcao=request.POST.get('funcao'),
                valor_diaria=request.POST.get('valor_diaria'),
                quantidade=request.POST.get('quantidade')
            )
            messages.success(request, 'Vaga vinculada com sucesso!')
            return redirect('admin_dashboard')

        elif acao == 'alterar_candidatura':
            cand = get_object_or_404(Candidatura, id=request.POST.get('candidatura_id'), vaga__evento__empresa=empresa)
            cand.status = request.POST.get('novo_status')
            cand.save()
            if cand.status == 'APROVADO':
                PresencaPagamento.objects.get_or_create(candidatura=cand)
            messages.success(request, f'Status atualizado para {cand.status}.')
            return redirect('admin_dashboard')

        elif acao == 'confirmar_checkin_admin':
            cand_id = request.POST.get('candidatura_id')
            cand = get_object_or_404(Candidatura, id=cand_id, vaga__evento__empresa=empresa, status='APROVADO')
            pres, _ = PresencaPagamento.objects.get_or_create(candidatura=cand)
            
            hoje = date.today()
            if pres.ultima_data_checkin == hoje:
                messages.warning(request, f'O check-in de {cand.usuario.first_name or cand.usuario.username} já foi registrado hoje!')
            else:
                pres.dias_presentes += 1
                pres.ultima_data_checkin = hoje
                pres.status_deslocamento = 'NO_LOCAL'
                pres.save()
                messages.success(request, f'✅ Check-in confirmado para {cand.usuario.first_name or cand.usuario.username}!')
            return redirect('admin_dashboard')

        elif acao == 'abrir_chamado':
            assunto = request.POST.get('assunto')
            mensagem = request.POST.get('mensagem')
            ch = ChamadoSuporte.objects.create(empresa=empresa, usuario=request.user, assunto=assunto)
            MensagemChamado.objects.create(chamado=ch, remetente=request.user, mensagem=mensagem)
            messages.success(request, 'Chamado de suporte aberto com sucesso!')
            return redirect('admin_dashboard')

        elif acao == 'salvar_pagamento':
            cand = get_object_or_404(Candidatura, id=request.POST.get('candidatura_id'), vaga__evento__empresa=empresa)
            pres, _ = PresencaPagamento.objects.get_or_create(candidatura=cand)
            dias = int(request.POST.get('dias_presentes', 0))
            novo_st = request.POST.get('status_pagamento')
            
            pres.dias_presentes = dias
            pres.status_pagamento = novo_st
            if novo_st == 'PAGO':
                pres.valor_pago = dias * cand.vaga.valor_diaria
            elif novo_st == 'PARCIAL':
                pres.valor_pago = (dias * cand.vaga.valor_diaria) / 2
            else:
                pres.valor_pago = 0.00
            pres.save()
            messages.success(request, 'Pagamento atualizado!')
            return redirect('admin_dashboard')

        elif acao == 'baixa_lote':
            texto_lote = request.POST.get('dados_lote', '')
            linhas = texto_lote.strip().split('\n')
            count = 0
            for row in linhas:
                parts = row.split(';') if ';' in row else row.split(',')
                if len(parts) >= 2:
                    cpf_pix = parts[0].strip()
                    val_pago = float(parts[1].replace(',', '.').strip())
                    
                    presencas = PresencaPagamento.objects.filter(
                        candidatura__usuario__cpf=cpf_pix,
                        candidatura__vaga__evento__empresa=empresa
                    )
                    for p in presencas:
                        p.status_pagamento = 'PAGO'
                        p.valor_pago = val_pago
                        p.save()
                        count += 1
            messages.success(request, f'Baixa em lote processada para {count} registro(s)!')
            return redirect('admin_dashboard')

    if empresa:
        eventos = Evento.objects.filter(empresa=empresa).order_by('-id')
        vagas = Vaga.objects.filter(evento__empresa=empresa).order_by('-id')
        candidaturas = Candidatura.objects.filter(vaga__evento__empresa=empresa).order_by('-id')
        chamados = ChamadoSuporte.objects.filter(empresa=empresa).prefetch_related('mensagens').order_by('-id')
        pagamentos = Candidatura.objects.filter(vaga__evento__empresa=empresa, status='APROVADO').order_by('-id')
        equipe_staff = Usuario.objects.filter(empresa=empresa, perfil='STAFF').order_by('-id')
    else:
        eventos = Evento.objects.none()
        vagas = Vaga.objects.none()
        candidaturas = Candidatura.objects.none()
        chamados = ChamadoSuporte.objects.none()
        pagamentos = Candidatura.objects.none()
        equipe_staff = Usuario.objects.none()

    candidaturas_aprovadas = candidaturas.filter(status='APROVADO').select_related('usuario', 'vaga__evento')

    total_eventos = eventos.count()
    total_staffs = equipe_staff.count()
    total_caches_previstos = sum([v.valor_diaria * v.quantidade for v in vagas])
    
    total_caches_pagos = 0.00
    for p in pagamentos:
        pres = obter_presenca(p)
        if pres and pres.valor_pago:
            total_caches_pagos += float(pres.valor_pago)

    total_caches_pendentes = float(total_caches_previstos) - total_caches_pagos

    link_convite = request.build_absolute_uri(f"/registro/staff/?empresa={empresa.id}") if empresa else ""

    context = {
        'empresa': empresa,
        'eventos': eventos,
        'vagas': vagas,
        'candidaturas': candidaturas,
        'candidaturas_aprovadas': candidaturas_aprovadas,
        'pagamentos': pagamentos,
        'chamados': chamados,
        'equipe_staff': equipe_staff,
        'total_eventos': total_eventos,
        'total_staffs': total_staffs,
        'total_caches_previstos': total_caches_previstos,
        'total_caches_pagos': total_caches_pagos,
        'total_caches_pendentes': total_caches_pendentes if total_caches_pendentes > 0 else 0,
        'link_convite': link_convite,
    }
    return render(request, 'core/admin_dashboard.html', context)

@login_required
def staff_dashboard(request):
    if request.user.perfil not in ['STAFF', 'SUPER_ADMIN'] and not request.user.is_superuser:
        return redirect('login')

    empresa = request.user.empresa

    whats_produtora = None
    if empresa:
        num_raw = empresa.whatsapp
        if not num_raw:
            admin_user = Usuario.objects.filter(empresa=empresa, perfil='ADMIN').first()
            if admin_user:
                num_raw = admin_user.whatsapp
        
        if num_raw:
            num_clean = re.sub(r'\D', '', num_raw)
            if not num_clean.startswith('55'):
                num_clean = '55' + num_clean
            whats_produtora = num_clean

    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        if acao == 'candidatar':
            vaga = get_object_or_404(Vaga, id=request.POST.get('vaga_id'))
            cand, created = Candidatura.objects.get_or_create(vaga=vaga, usuario=request.user)
            if created:
                messages.success(request, f'Inscrição realizada para {vaga.funcao}!')
            else:
                messages.warning(request, 'Você já está inscrito para esta vaga.')
            return redirect('staff_dashboard')

        elif acao == 'a_caminho':
            cand_id = request.POST.get('candidatura_id')
            cand = get_object_or_404(Candidatura, id=cand_id, usuario=request.user, status='APROVADO')
            pres, _ = PresencaPagamento.objects.get_or_create(candidatura=cand)
            pres.status_deslocamento = 'A_CAMINHO'
            pres.save()
            messages.success(request, 'Aviso enviado! A produtora já sabe que você está a caminho 🚗')
            return redirect('staff_dashboard')

        elif acao == 'checkin_gps':
            cand_id = request.POST.get('candidatura_id')
            lat_user = float(request.POST.get('lat_user', 0))
            lng_user = float(request.POST.get('lng_user', 0))
            
            cand = get_object_or_404(Candidatura, id=cand_id, usuario=request.user, status='APROVADO')
            evento = cand.vaga.evento
            
            if not evento.latitude or not evento.longitude:
                evento.latitude, evento.longitude = obter_lat_lng_endereco(evento.local)
                evento.save()

            if evento.latitude and evento.longitude:
                distancia = haversine_distance(lat_user, lng_user, evento.latitude, evento.longitude)
                if distancia > 100:
                    messages.error(request, f'❌ Check-in negado! Você está a {int(distancia)}m do evento. É necessário estar a menos de 100 metros.')
                    return redirect('staff_dashboard')

            pres, _ = PresencaPagamento.objects.get_or_create(candidatura=cand)
            
            hoje = date.today()
            if pres.ultima_data_checkin == hoje:
                messages.warning(request, f'Seu check-in de hoje ({hoje.strftime("%d/%m/%Y")}) já foi registrado!')
                return redirect('staff_dashboard')

            pres.status_deslocamento = 'NO_LOCAL'
            pres.lat_checkin = lat_user
            pres.lng_checkin = lng_user
            pres.dias_presentes += 1
            pres.ultima_data_checkin = hoje
            pres.save()
            messages.success(request, '✅ Check-in realizado com sucesso via GPS! Presença confirmada.')
            return redirect('staff_dashboard')

        elif acao == 'cancelar_candidatura':
            cand = get_object_or_404(Candidatura, id=request.POST.get('candidatura_id'), usuario=request.user)
            cand.delete()
            messages.success(request, 'Inscrição cancelada com sucesso.')
            return redirect('staff_dashboard')

        elif acao == 'atualizar_perfil':
            user = request.user
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.email = request.POST.get('email', user.email)
            user.whatsapp = request.POST.get('whatsapp', user.whatsapp)
            user.genero = request.POST.get('genero', user.genero)
            user.tamanho_camiseta = request.POST.get('tamanho_camiseta', user.tamanho_camiseta)
            user.tamanho_calcado = request.POST.get('tamanho_calcado', user.tamanho_calcado)
            user.tipo_chave_pix = request.POST.get('tipo_chave_pix', user.tipo_chave_pix)
            user.chave_pix = request.POST.get('chave_pix', user.chave_pix)
            
            senha = request.POST.get('senha')
            if senha and senha.strip():
                user.set_password(senha.strip())
                
            if 'foto' in request.FILES:
                user.foto = request.FILES['foto']

            user.save()
            update_session_auth_hash(request, user)

            try:
                send_mail(
                    'One Shot Tech — Alteração de Perfil Confirmada',
                    f'Olá, {user.first_name or user.username}!\n\nSeus dados de perfil no sistema One Shot Tech foram atualizados com sucesso.',
                    settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@oneshottech.com',
                    [user.email],
                    fail_silently=True,
                )
            except Exception:
                pass

            messages.success(request, 'Perfil atualizado e e-mail de confirmação enviado!')
            return redirect('staff_dashboard')

    minhas_candidaturas = Candidatura.objects.filter(usuario=request.user).select_related('vaga__evento').order_by('-id')
    minhas_vagas_ids = minhas_candidaturas.values_list('vaga_id', flat=True)

    vagas_aprovadas_ids = minhas_candidaturas.filter(status='APROVADO').values_list('vaga_id', flat=True)
    
    vagas_disponiveis = Vaga.objects.filter(status='ABERTA').exclude(id__in=vagas_aprovadas_ids).order_by('-id')
    if empresa:
        vagas_disponiveis = vagas_disponiveis.filter(evento__empresa=empresa)

    eventos_ativos = minhas_candidaturas.filter(status='APROVADO')

    tot_a_receber = 0.00
    tot_recebido = 0.00
    total_eventos_trabalhados = 0
    extrato_detalhado = []

    for c in minhas_candidaturas:
        if c.status == 'APROVADO':
            total_eventos_trabalhados += 1
            pres = obter_presenca(c)
            dias = pres.dias_presentes if pres else 0
            st_p = pres.status_pagamento if pres else 'PENDENTE'
            val_p = float(pres.valor_pago) if (pres and pres.valor_pago) else 0.00
            
            val_total = float(c.vaga.valor_diaria) * dias
            if st_p == 'PAGO':
                tot_recebido += val_p
            else:
                tot_a_receber += val_total

            extrato_detalhado.append({
                'evento': c.vaga.evento.nome,
                'funcao': c.vaga.funcao,
                'diaria': c.vaga.valor_diaria,
                'dias': dias,
                'total_calculado': val_total,
                'valor_pago': val_p,
                'status': st_p
            })

    context = {
        'vagas_disponiveis': vagas_disponiveis,
        'minhas_candidaturas': minhas_candidaturas,
        'minhas_vagas_ids': minhas_vagas_ids,
        'eventos_ativos': eventos_ativos,
        'extrato_detalhado': extrato_detalhado,
        'tot_a_receber': tot_a_receber,
        'tot_recebido': tot_recebido,
        'total_eventos_trabalhados': total_eventos_trabalhados,
        'whats_produtora': whats_produtora,
    }
    return render(request, 'core/staff_dashboard.html', context)

@login_required
def exportar_caches_excel(request):
    if not (request.user.perfil in ['ADMIN', 'SUPER_ADMIN'] or request.user.is_superuser):
        return redirect('login')

    empresa = request.user.empresa or Empresa.objects.first()
    pagamentos = Candidatura.objects.filter(vaga__evento__empresa=empresa, status='APROVADO').select_related('usuario', 'vaga__evento').order_by('-id') if empresa else Candidatura.objects.none()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Aprovados - Relatorio Caches"

    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    align_center = Alignment(horizontal="center", vertical="center")

    headers = ["ID Staff", "Nome", "Sobrenome", "CPF", "RG", "WhatsApp", "Gênero", "Camiseta", "Calçado", "Tipo Pix", "Chave Pix", "Evento", "Função", "Valor Diária (R$)", "Dias Presentes", "Valor Total (R$)", "Status Pagamento"]
    ws.append(headers)

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = align_center

    for item in pagamentos:
        u = item.usuario
        pres = obter_presenca(item)
        dias = pres.dias_presentes if pres else 0
        st_p = pres.status_pagamento if pres else 'PENDENTE'
        v_diaria = float(item.vaga.valor_diaria)
        v_total = v_diaria * dias

        row = [u.id, u.first_name or u.username, u.last_name or "", u.cpf or "N/A", u.rg or "N/A", u.whatsapp or "N/A", u.get_genero_display() if u.genero else "N/A", u.tamanho_camiseta or "N/A", u.tamanho_calcado or "N/A", u.tipo_chave_pix or "N/A", u.chave_pix or "N/A", item.vaga.evento.nome, item.vaga.funcao, v_diaria, dias, v_total, st_p]
        ws.append(row)

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="relatorio_aprovados_{empresa.id if empresa else 1}.xlsx"'
    wb.save(response)
    return response

@login_required
def exportar_caches_pdf(request):
    if not (request.user.perfil in ['ADMIN', 'SUPER_ADMIN'] or request.user.is_superuser):
        return redirect('login')

    empresa = request.user.empresa or Empresa.objects.first()
    pagamentos = Candidatura.objects.filter(vaga__evento__empresa=empresa, status='APROVADO').select_related('usuario', 'vaga__evento').order_by('-id') if empresa else Candidatura.objects.none()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="folha_caches_{empresa.id if empresa else 1}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor('#0F172A'), spaceAfter=6)
    subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#64748B'), spaceAfter=15)

    elements.append(Paragraph(f"One Shot Tech — Folha de Pagamento de Cachês", title_style))
    elements.append(Paragraph(f"Produtora: {empresa.nome if empresa else 'Global'} | Emitido para o Financeiro", subtitle_style))

    data = [["Staff", "CPF", "Pix", "Evento / Função", "Diária", "Dias", "Total (R$)", "Status"]]

    for item in pagamentos:
        pres = obter_presenca(item)
        dias = pres.dias_presentes if pres else 0
        st_p = pres.status_pagamento if pres else 'PENDENTE'
        v_diaria = float(item.vaga.valor_diaria)
        v_total = v_diaria * dias

        data.append([
            item.usuario.get_full_name() or item.usuario.username,
            item.usuario.cpf or "N/A",
            item.usuario.chave_pix or "N/A",
            f"{item.vaga.evento.nome}\n({item.vaga.funcao})",
            f"R$ {v_diaria:.2f}",
            str(dias),
            f"R$ {v_total:.2f}",
            st_p
        ])

    table = Table(data, colWidths=[100, 75, 80, 130, 50, 35, 55, 50])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))

    elements.append(table)
    doc.build(elements)
    return response

@login_required
def exportar_ficha_staff_pdf(request, user_id):
    if not (request.user.perfil in ['ADMIN', 'SUPER_ADMIN'] or request.user.is_superuser):
        return redirect('login')

    staff_user = get_object_or_404(Usuario, id=user_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ficha_staff_{staff_user.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor('#0F172A'), spaceAfter=4)
    subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#64748B'), spaceAfter=20)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#0284C7'), spaceBefore=10, spaceAfter=8)

    elements.append(Paragraph(f"Ficha Cadastral do Colaborador", title_style))
    elements.append(Paragraph(f"One Shot Tech | Plataforma de Casting & Eventos", subtitle_style))

    dados_pessoais = [
        ["Nome Completo:", staff_user.get_full_name() or staff_user.username],
        ["CPF:", staff_user.cpf or "Não informado"],
        ["RG:", staff_user.rg or "Não informado"],
        ["Gênero:", staff_user.get_genero_display() if staff_user.genero else "Não informado"],
        ["WhatsApp / Contato:", staff_user.whatsapp or "Não informado"],
        ["E-mail:", staff_user.email],
        ["Produtora Vinculada:", staff_user.empresa.nome if staff_user.empresa else "Global"],
    ]

    t_pessoais = Table(dados_pessoais, colWidths=[140, 380])
    t_pessoais.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#0F172A')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))

    elements.append(Paragraph("1. Dados Pessoais & Contatos", section_style))
    elements.append(t_pessoais)
    elements.append(Spacer(1, 15))

    dados_operacionais = [
        ["Tamanho de Camiseta:", staff_user.tamanho_camiseta or "Não informado"],
        ["Número de Calçado:", staff_user.tamanho_calcado or "Não informado"],
        ["Tipo de Chave Pix:", staff_user.tipo_chave_pix or "Não informado"],
        ["Chave Pix:", staff_user.chave_pix or "Não informado"],
        ["Nota Média de Avaliação:", f"⭐ {staff_user.nota_media} / 5.0"],
    ]

    t_operacionais = Table(dados_operacionais, colWidths=[140, 380])
    t_operacionais.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#0F172A')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))

    elements.append(Paragraph("2. Dress Code & Dados Financeiros", section_style))
    elements.append(t_operacionais)

    doc.build(elements)
    return response

@login_required
def exportar_extrato_staff_pdf(request):
    if request.user.perfil not in ['STAFF', 'SUPER_ADMIN'] and not request.user.is_superuser:
        return redirect('login')

    user = request.user
    candidaturas = Candidatura.objects.filter(usuario=user, status='APROVADO').select_related('vaga__evento').order_by('-id')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="extrato_caches_{user.username}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor('#0F172A'), spaceAfter=4)
    subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#64748B'), spaceAfter=15)

    elements.append(Paragraph(f"Extrato Financeiro de Cachês", title_style))
    elements.append(Paragraph(f"Colaborador: {user.get_full_name() or user.username} | CPF: {user.cpf or 'N/A'}", subtitle_style))

    data = [["Evento", "Função", "Diária (R$)", "Dias Presentes", "Total Calculado (R$)", "Status Pagamento"]]

    tot_geral = 0.0
    for c in candidaturas:
        pres = obter_presenca(c)
        dias = pres.dias_presentes if pres else 0
        st_p = pres.status_pagamento if pres else 'PENDENTE'
        v_diaria = float(c.vaga.valor_diaria)
        v_total = v_diaria * dias
        tot_geral += v_total

        data.append([
            c.vaga.evento.nome,
            c.vaga.funcao,
            f"R$ {v_diaria:.2f}",
            str(dias),
            f"R$ {v_total:.2f}",
            st_p
        ])

    data.append(["TOTAL GERAL", "", "", "", f"R$ {tot_geral:.2f}", ""])

    table = Table(data, colWidths=[130, 100, 70, 75, 95, 70])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9')),
    ]))

    elements.append(table)
    doc.build(elements)
    return response