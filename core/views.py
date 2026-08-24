import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from eventos.models import Vaga, Candidatura, PresencaPagamento

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

@login_required
def staff_dashboard(request):
    if request.user.perfil not in ['STAFF', 'SUPER_ADMIN'] and not request.user.is_superuser:
        return redirect('login')

    empresa = request.user.empresa

    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        # 1. CANDIDATAR-SE À VAGA
        if acao == 'candidatar':
            vaga = get_object_or_404(Vaga, id=request.POST.get('vaga_id'))
            cand, created = Candidatura.objects.get_or_create(vaga=vaga, usuario=request.user)
            if created:
                messages.success(request, f'Inscrição efetuada com sucesso para {vaga.funcao}!')
            else:
                messages.warning(request, 'Você já se candidatou a esta vaga.')
            return redirect('staff_dashboard')

        # 2. BOTÃO A CAMINHO
        elif acao == 'a_caminho':
            cand_id = request.POST.get('candidatura_id')
            cand = get_object_or_404(Candidatura, id=cand_id, usuario=request.user, status='APROVADO')
            pres, _ = PresencaPagamento.objects.get_or_create(candidatura=cand)
            pres.status_deslocamento = 'A_CAMINHO'
            pres.save()
            messages.success(request, 'Aviso enviado! A produtora já sabe que você está a caminho 🚗')
            return redirect('staff_dashboard')

        # 3. CHECK-IN GPS
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

        # 4. FICHA CADASTRAL DO EVENTO (Unlocks Dress Code)
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

        # 5. ALTERAÇÃO DE PERFIL COM CONFIRMAÇÃO VIA E-MAIL
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
            user.tamanho_camiseta = request.POST.get('tamanho_camiseta', user.tamanho_camiseta)
            user.tamanho_calcado = request.POST.get('tamanho_calcado', user.tamanho_calcado)

            senha = request.POST.get('senha')
            if senha and senha.strip():
                user.set_password(senha.strip())

            if 'foto' in request.FILES:
                user.foto = request.FILES['foto']

            user.save()
            update_session_auth_hash(request, user)

            # DISPARO DE CONFIRMAÇÃO POR E-MAIL
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

    # CARREGAMENTO DOS DADOS PARA AS ABAS
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