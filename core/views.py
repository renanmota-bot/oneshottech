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


# ==========================================
# FUNÇÕES AUXILIARES E VALIDAÇÕES
# ==========================================
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


def redirect_por_perfil(user):
    if user.perfil == 'SUPER_ADMIN' or user.is_superuser:
        return redirect('super_admin_dashboard')
    elif user.perfil == 'ADMIN':
        return redirect('admin_dashboard')
    else:
        return redirect('staff_dashboard')


# ==========================================
# AUTENTICAÇÃO E CADASTROS INICIAIS
# ==========================================
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


# ==========================================
# 1. SUPER ADMIN (DONO DA PLATAFORMA SAAS)
# ==========================================
@login_required
def super_admin_dashboard(request):
    if not (request.user.perfil == 'SUPER_ADMIN' or request.user.is_superuser):
        return redirect('login')
        
    if request.method == 'POST':
        acao = request.POST.get('acao')

        # CRIAR NOVA EMPRESA / PRODUTORA
        if acao == 'criar_empresa':
            nome_emp = request.POST.get('nome') or request.POST.get('nome_empresa')
            cnpj_emp = request.POST.get('cnpj')
            valor_p = request.POST.get('valor_plano', 150.00)
            plano_p = request.POST.get('plano') or request.POST.get('plano_empresa', 'BASICO')
            whatsapp_emp = request.POST.get('whatsapp')
            email_admin = request.POST.get('email_admin')
            senha_admin = request.POST.get('senha_admin')

            if Empresa.objects.filter(cnpj=cnpj_emp).exists():
                messages.error(request, 'CNPJ/CPF já existente!')
            else:
                emp = Empresa.objects.create(
                    nome=nome_emp, 
                    cnpj=cnpj_emp, 
                    valor_plano=valor_p, 
                    plano=plano_p, 
                    whatsapp=whatsapp_emp, 
                    status='ATIVO'
                )
                if email_admin and senha_admin:
                    Usuario.objects.create_user(
                        username=email_admin, 
                        email=email_admin, 
                        password=senha_admin, 
                        first_name=f'Admin {nome_emp}', 
                        empresa=emp, 
                        perfil='ADMIN', 
                        is_staff=True
                    )
                messages.success(request, f'Empresa #{emp.id} - {emp.nome} criada com sucesso!')
            return redirect('super_admin_dashboard')

        # ALTERAR PLANO / STATUS DA EMPRESA
        elif acao == 'alterar_status_empresa':
            emp = get_object_or_404(Empresa, id=request.POST.get('empresa_id'))
            emp.status = request.POST.get('status', emp.status)
            emp.plano = request.POST.get('plano', emp.plano)
            novo_val = request.POST.get('valor_plano')
            if novo_val: 
                emp.valor_plano = novo_val
            emp.save()
            messages.success(request, f'Empresa #{emp.id} atualizada com sucesso!')
            return redirect('super_admin_dashboard')

        # BLOQUEAR / DESBLOQUEAR EMPRESA
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

        # CRIAR USUÁRIO GLOBALMENTE
        elif acao == 'criar_usuario_global':
            nome_u = request.POST.get('nome')
            email_u = request.POST.get('email')
            senha_u = request.POST.get('senha')
            perfil_u = request.POST.get('perfil')
            emp_id_u = request.POST.get('empresa_id')
            emp_u = Empresa.objects.filter(id=emp_id_u).first() if emp_id_u else None

            if Usuario.objects.filter(username=email_u).exists():
                messages.error(request, 'E-mail já cadastrado no sistema!')
            else:
                Usuario.objects.create_user(username=email_u, email=email_u, password=senha_u, first_name=nome_u, perfil=perfil_u, empresa=emp_u)
                messages.success(request, f'Usuário {nome_u} criado com sucesso!')
            return redirect('super_admin_dashboard')

        # EDITAR USUÁRIO GLOBALMENTE
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
            messages.success(request, f'Usuário #{usr.id} - {usr.first_name} atualizado!')
            return redirect('super_admin_dashboard')

        # RESPONDER CHAMADO DE SUPORTE
        elif acao == 'responder_chamado':
            chamado = get_object_or_404(ChamadoSuporte, id=request.POST.get('chamado_id'))
            msg_texto = request.POST.get('mensagem')
            if msg_texto and msg_texto.strip():
                MensagemChamado.objects.create(chamado=chamado, remetente=request.user, mensagem=msg_texto.strip())
            chamado.status = request.POST.get('status', chamado.status)
            chamado.save()
            messages.success(request, f'Chamado #{chamado.id} atualizado!')
            return redirect('super_admin_dashboard')

    # QUERIES E FILTROS DO SUPER ADMIN
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

    total_mrr = sum([float(e.valor_plano) for e in empresas_ativas])
    total_arr = total_mrr * 12
    arpu = (total_mrr / len(empresas_ativas)) if empresas_ativas else 0.00

    context = {
        'empresas': empresas,
        'usuarios': usuarios_qs,
        'chamados': chamados_qs,
        'total_empresas': empresas.count(),
        'total_empresas_ativas': len(empresas_ativas),
        'total_empresas_bloqueadas': len(empresas_bloqueadas),
        'total_staffs': Usuario.objects.filter(perfil='STAFF').count(),
        'total_eventos': Evento.objects.count(),
        'chamados_abertos': ChamadoSuporte.objects.filter(status='ABERTO').count(),
        'total_mrr': total_mrr,
        'total_arr': total_arr,
        'arpu': arpu,
        'busca_usr': busca_usr,
        'filtro_perfil': filtro_perfil,
        'filtro_chamado': filtro_status_chamado,
    }
    return render(request, 'core/super_admin.html', context)


# GHOST LOGIN
@login_required
def ghost_login_view(request, user_id):
    if not (request.user.perfil == 'SUPER_ADMIN' or request.user.is_superuser):
        return redirect('login')
        
    target_user = get_object_or_404(Usuario, id=user_id)
    login(request, target_user, backend='django.contrib.auth.backends.ModelBackend')
    messages.info(request, f'👁️ Acesso Ghost ativado: Você está logado como "{target_user.first_name or target_user.username}"')
    return redirect_por_perfil(target_user)


# ==========================================
# 2. ADMIN PRODUTORA (GESTOR DE EVENTOS)
# ==========================================
@login_required
def admin_dashboard(request):
    if not (request.user.perfil == 'ADMIN' or request.user.is_superuser):
        return redirect('login')

    empresa = request.user.empresa or Empresa.objects.first()

    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        if acao == 'criar_evento':
            endereco_local = request.POST.get('local')
            lat_auto, lng_auto = obter_lat_lng_endereco(endereco_local)

            Evento.objects.create(
                empresa=empresa,
                nome=request.POST.get('nome'),
                local=endereco_local,
                latitude=lat_auto,
                longitude=lng_auto,
                data_inicio=request.POST.get('data_inicio')
            )
            messages.success(request, 'Evento criado com sucesso!')
            return redirect('admin_dashboard')

        elif acao == 'criar_vaga':
            evento = get_object_or_404(Evento, id=request.POST.get('evento_id'), empresa=empresa)
            val_raw = str(request.POST.get('valor_diaria', '0')).replace(',', '.')
            Vaga.objects.create(
                evento=evento,
                funcao=request.POST.get('funcao'),
                valor_diaria=val_raw,
                quantidade=request.POST.get('quantidade', 1),
                prazo_pagamento_dias=request.POST.get('prazo_pagamento_dias', 0)
            )
            messages.success(request, 'Vaga criada com prazo de pagamento ajustado!')
            return redirect('admin_dashboard')

        elif acao == 'alterar_candidatura':
            cand = get_object_or_404(Candidatura, id=request.POST.get('candidatura_id'), vaga__evento__empresa=empresa)
            cand.status = request.POST.get('novo_status')
            cand.save()
            if cand.status == 'APROVADO':
                PresencaPagamento.objects.get_or_create(candidatura=cand)
            messages.success(request, f'Status atualizado para {cand.status}.')
            return redirect('admin_dashboard')

        elif acao == 'validar_checkin':
            pres = get_object_or_404(PresencaPagamento, id=request.POST.get('presenca_id'), candidatura__vaga__evento__empresa=empresa)
            pres.status_deslocamento = 'VALIDADO'
            pres.save()
            messages.success(request, 'Check-in validado! Staff enviado para Pagamentos.')
            return redirect('admin_dashboard')

        elif acao == 'marcar_falta':
            pres = get_object_or_404(PresencaPagamento, id=request.POST.get('presenca_id'), candidatura__vaga__evento__empresa=empresa)
            pres.status_deslocamento = 'FALTOU'
            pres.status_pagamento = 'CANCELADO'
            pres.save()
            messages.error(request, 'Falta registrada. Staff removido da operação.')
            return redirect('admin_dashboard')

        elif acao == 'marcar_pago':
            pres = get_object_or_404(PresencaPagamento, id=request.POST.get('presenca_id'), candidatura__vaga__evento__empresa=empresa)
            pres.status_pagamento = 'PAGO'
            dias = pres.dias_presentes if pres.dias_presentes > 0 else 1
            pres.valor_pago = dias * pres.candidatura.vaga.valor_diaria
            pres.save()
            messages.success(request, 'Pagamento baixado com sucesso!')
            return redirect('admin_dashboard')

    eventos = Evento.objects.filter(empresa=empresa).order_by('-id') if empresa else []
    vagas = Vaga.objects.filter(evento__empresa=empresa).order_by('-id') if empresa else []
    candidaturas_pendentes = Candidatura.objects.filter(vaga__evento__empresa=empresa, status='PENDENTE').order_by('-id') if empresa else []
    
    operacao = PresencaPagamento.objects.filter(
        candidatura__vaga__evento__empresa=empresa,
        candidatura__status='APROVADO'
    ).exclude(status_deslocamento__in=['VALIDADO', 'FALTOU']).order_by('-id') if empresa else []

    financeiro = PresencaPagamento.objects.filter(
        candidatura__vaga__evento__empresa=empresa,
        candidatura__status='APROVADO',
        status_deslocamento='VALIDADO'
    ).order_by('-id') if empresa else []

    total_eventos = eventos.count()
    total_staffs = operacao.count() + financeiro.count()
    total_caches_previstos = sum([f.candidatura.vaga.valor_diaria for f in financeiro if f.status_pagamento != 'PAGO'])
    total_caches_pagos = sum([f.candidatura.vaga.valor_diaria for f in financeiro if f.status_pagamento == 'PAGO'])

    link_convite = request.build_absolute_uri(f"/registro/staff/?empresa={empresa.id}") if empresa else ""

    context = {
        'empresa': empresa,
        'eventos': eventos,
        'vagas': vagas,
        'candidaturas': candidaturas_pendentes,
        'operacao': operacao,
        'financeiro': financeiro,
        'total_eventos': total_eventos,
        'total_staffs': total_staffs,
        'total_caches_previstos': total_caches_previstos,
        'total_caches_pagos': total_caches_pagos,
        'link_convite': link_convite,
    }
    return render(request, 'core/admin_dashboard.html', context)


# ==========================================
# 3. STAFF (COLABORADOR)
# ==========================================
@login_required
def staff_dashboard(request):
    if request.user.perfil not in ['STAFF', 'SUPER_ADMIN'] and not request.user.is_superuser:
        return redirect('login')

    empresa = request.user.empresa

    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        if acao == 'candidatar':
            vaga = get_object_or_404(Vaga, id=request.POST.get('vaga_id'))
            cand, created = Candidatura.objects.get_or_create(vaga=vaga, usuario=request.user)
            if created:
                messages.success(request, f'Inscrição efetuada com sucesso para {vaga.funcao}!')
            else:
                messages.warning(request, 'Você já se candidatou a esta vaga.')
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
            
            pres, _ = PresencaPagamento.objects.get_or_create(candidatura=cand)
            pres.status_deslocamento = 'CHECKIN_REALIZADO'
            pres.lat_checkin = lat_user
            pres.lng_checkin = lng_user
            pres.save()
            messages.success(request, '📍 Check-in realizado com sucesso! Aguarde validação da produtora.')
            return redirect('staff_dashboard')

        elif acao == 'preencher_ficha':
            nome = request.POST.get('first_name')
            cpf = request.POST.get('cpf')
            rg = request.POST.get('rg')

            if not validar_cpf(cpf):
                messages.error(request, '❌ CPF Inválido! Verifique os números e tente novamente.')
                return redirect('staff_dashboard')

            if not rg or len(rg.strip()) < 5:
                messages.error(request, '❌ Documento RG Inválido!')
                return redirect('staff_dashboard')

            user = request.user
            user.first_name = nome
            user.cpf = cpf
            user.rg = rg
            user.save()
            
            messages.success(request, '📋 Ficha Cadastral confirmada! Liberando acesso ao Dress Code.')
            return redirect('staff_dashboard')

        elif acao == 'atualizar_perfil':
            user = request.user
            novo_cpf = request.POST.get('cpf', user.cpf)
            novo_rg = request.POST.get('rg', user.rg)

            if novo_cpf and not validar_cpf(novo_cpf):
                messages.error(request, '❌ Erro ao salvar: O CPF informado é inválido!')
                return redirect('staff_dashboard')

            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.email = request.POST.get('email', user.email)
            user.whatsapp = request.POST.get('whatsapp', user.whatsapp)
            user.cpf = novo_cpf
            user.rg = novo_rg
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
                    'One Shot Tech — Alteração de Dados Confirmada',
                    f'Olá {user.first_name}!\n\nSeus dados cadastrais e de recebimento Pix foram alterados com sucesso na plataforma.',
                    settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@oneshottech.com',
                    [user.email],
                    fail_silently=True,
                )
            except Exception:
                pass

            messages.success(request, '✅ Perfil atualizado! Enviamos uma confirmação para seu e-mail.')
            return redirect('staff_dashboard')

    minhas_candidaturas = Candidatura.objects.filter(usuario=request.user).select_related('vaga__evento', 'presenca_pagamento').order_by('-id')
    vagas_aprovadas = minhas_candidaturas.filter(status='APROVADO')
    vagas_aprovadas_ids = vagas_aprovadas.values_list('vaga_id', flat=True)

    vagas_disponiveis = Vaga.objects.filter(status='ABERTA').exclude(id__in=vagas_aprovadas_ids).select_related('evento').order_by('-id')
    if empresa:
        vagas_disponiveis = vagas_disponiveis.filter(evento__empresa=empresa)

    extrato_pagamentos = PresencaPagamento.objects.filter(
        candidatura__usuario=request.user,
        candidatura__status='APROVADO'
    ).select_related('candidatura__vaga__evento')

    tot_recebido = sum(p.candidatura.vaga.valor_diaria for p in extrato_pagamentos if p.status_pagamento == 'PAGO')
    tot_a_receber = sum(p.candidatura.vaga.valor_diaria for p in extrato_pagamentos if p.status_pagamento != 'PAGO')

    context = {
        'vagas_disponiveis': vagas_disponiveis,
        'vagas_aprovadas': vagas_aprovadas,
        'extrato_pagamentos': extrato_pagamentos,
        'tot_recebido': tot_recebido,
        'tot_a_receber': tot_a_receber,
    }
    return render(request, 'core/staff_dashboard.html', context)


# ==========================================
# EXPORTAÇÕES (EXCEL E PDF)
# ==========================================
@login_required
def exportar_caches_excel(request):
    if not (request.user.perfil in ['ADMIN', 'SUPER_ADMIN'] or request.user.is_superuser):
        return redirect('login')

    empresa = request.user.empresa or Empresa.objects.first()
    pagamentos = Candidatura.objects.filter(vaga__evento__empresa=empresa, status='APROVADO').select_related('presenca_pagamento', 'usuario', 'vaga__evento').order_by('-id')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Aprovados - Relatorio Caches"

    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    align_center = Alignment(horizontal="center", vertical="center")

    headers = ["ID Staff", "Nome", "Sobrenome", "CPF", "RG", "WhatsApp", "Gênero", "Camiseta", "Calçado", "Tipo Pix", "Chave Pix", "Evento", "Função", "Valor Diária (R$)", "Prazo Pagamento (Dias)", "Status Pagamento"]
    ws.append(headers)

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = align_center

    for item in pagamentos:
        u = item.usuario
        pres = getattr(item, 'presenca_pagamento', None)
        st_p = pres.status_pagamento if pres else 'PENDENTE'
        v_diaria = float(item.vaga.valor_diaria)

        row = [u.id, u.first_name or u.username, u.last_name or "", u.cpf or "N/A", u.rg or "N/A", u.whatsapp or "N/A", u.get_genero_display() if u.genero else "N/A", u.tamanho_camiseta or "N/A", u.tamanho_calcado or "N/A", u.tipo_chave_pix or "N/A", u.chave_pix or "N/A", item.vaga.evento.nome, item.vaga.funcao, v_diaria, item.vaga.prazo_pagamento_dias, st_p]
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
    pagamentos = Candidatura.objects.filter(vaga__evento__empresa=empresa, status='APROVADO').select_related('presenca_pagamento', 'usuario', 'vaga__evento').order_by('-id')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="folha_caches_{empresa.id if empresa else 1}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor('#0F172A'), spaceAfter=6)
    subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#64748B'), spaceAfter=15)

    elements.append(Paragraph(f"One Shot Tech — Folha de Pagamento de Cachês", title_style))
    elements.append(Paragraph(f"Produtora: {empresa.nome if empresa else 'Global'} | Emitido para o Financeiro", subtitle_style))

    data = [["Staff", "CPF", "Pix", "Evento / Função", "Diária", "Prazo", "Status"]]

    for item in pagamentos:
        pres = getattr(item, 'presenca_pagamento', None)
        st_p = pres.status_pagamento if pres else 'PENDENTE'
        v_diaria = float(item.vaga.valor_diaria)

        data.append([
            item.usuario.get_full_name() or item.usuario.username,
            item.usuario.cpf or "N/A",
            item.usuario.chave_pix or "N/A",
            f"{item.vaga.evento.nome}\n({item.vaga.funcao})",
            f"R$ {v_diaria:.2f}",
            f"{item.vaga.prazo_pagamento_dias} dias",
            st_p
        ])

    table = Table(data, colWidths=[110, 80, 85, 140, 55, 45, 55])
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
    candidaturas = Candidatura.objects.filter(usuario=user, status='APROVADO').select_related('vaga__evento', 'presenca_pagamento').order_by('-id')

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
        pres = getattr(c, 'presenca_pagamento', None)
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