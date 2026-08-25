from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from core.models import Empresa, Usuario
from eventos.models import Evento, Vaga, Candidatura, PresencaPagamento, AvisoEvento, PropostaComercial


class Command(BaseCommand):
    help = 'Popula o banco de dados com dados de demonstração completos.'

    def handle(self, *args, **kwargs):
        # 1. PRODUTORAS
        emp_oneshot, _ = Empresa.objects.get_or_create(
            cnpj='11.222.333/0001-99',
            defaults={
                'nome': 'One Shot Eventos & BTL',
                'status': 'ATIVO',
                'plano': 'PREMIUM',
                'valor_plano': 299.00,
                'whatsapp': '11999991111',
                'inscricao_municipal': '123456-SP',
                'nfse_api_key': 'KEY_TESTE_ONESHOT_2026',
                'whatsapp_api_instancia': 'INSTANCE_ONESHOT',
                'whatsapp_api_token': 'TOKEN_ZAPI_123'
            }
        )

        emp_vibe, _ = Empresa.objects.get_or_create(
            cnpj='44.555.666/0001-88',
            defaults={
                'nome': 'Vibe Agência & Casting',
                'status': 'ATIVO',
                'plano': 'BASICO',
                'valor_plano': 150.00,
                'whatsapp': '11988882222'
            }
        )

        # 2. USUÁRIOS
        if not Usuario.objects.filter(username='admin_master').exists():
            Usuario.objects.create_superuser(
                username='admin_master',
                email='master@oneshottech.com.br',
                password='senha123',
                first_name='Super Admin',
                last_name='Master',
                perfil='SUPER_ADMIN'
            )

        adm_oneshot, _ = Usuario.objects.get_or_create(
            username='admin@oneshot.com.br',
            defaults={
                'email': 'admin@oneshot.com.br',
                'first_name': 'Carlos',
                'last_name': 'Mendoza',
                'perfil': 'ADMIN',
                'empresa': emp_oneshot,
                'is_staff': True
            }
        )
        adm_oneshot.set_password('senha123')
        adm_oneshot.save()

        adm_vibe, _ = Usuario.objects.get_or_create(
            username='contato@vibe.com.br',
            defaults={
                'email': 'contato@vibe.com.br',
                'first_name': 'Fernanda',
                'last_name': 'Lima',
                'perfil': 'ADMIN',
                'empresa': emp_vibe,
                'is_staff': True
            }
        )
        adm_vibe.set_password('senha123')
        adm_vibe.save()

        # 3. STAFFS
        staffs_dados = [
            ('lucas.silva@email.com', 'Lucas', 'Silva', '111.222.333-44', '12.345.678-9', '11911112222', 'CPF/CNPJ', '11122233344', 4.9),
            ('mariana.costa@email.com', 'Mariana', 'Costa', '222.333.444-55', '23.456.789-0', '11922223333', 'E-mail', 'mariana.costa@email.com', 5.0),
            ('bruno.oliveira@email.com', 'Bruno', 'Oliveira', '333.444.555-66', '34.567.890-1', '11933334444', 'Celular', '11933334444', 4.7),
            ('camila.santos@email.com', 'Camila', 'Santos', '444.555.666-77', '45.678.901-2', '11944445555', 'Chave Aleatória', 'pix-camila-key-99', 4.8),
        ]

        staff_objs = []
        for email, nome, sobrenome, cpf, rg, whats, t_pix, c_pix, nota in staffs_dados:
            u, _ = Usuario.objects.get_or_create(
                username=email,
                defaults={
                    'email': email, 'first_name': nome, 'last_name': sobrenome,
                    'cpf': cpf, 'rg': rg, 'whatsapp': whats,
                    'tipo_chave_pix': t_pix, 'chave_pix': c_pix,
                    'nota_media': nota, 'perfil': 'STAFF', 'empresa': emp_oneshot
                }
            )
            u.set_password('senha123')
            u.save()
            staff_objs.append(u)

        # 4. EVENTOS
        hoje = date.today()
        ev1, _ = Evento.objects.get_or_create(
            nome='Tech Innovation Summit 2026',
            empresa=emp_oneshot,
            defaults={
                'local': 'Avenida das Nações Unidas, 12551 - Brooklin, São Paulo - SP',
                'latitude': -23.6091, 'longitude': -46.6968,
                'data_inicio': hoje + timedelta(days=2), 'data_termino': hoje + timedelta(days=4),
                'dress_code': 'Camiseta preta oficial, calça jeans e tênis preto.',
                'orcamento_previsto': 12500.00
            }
        )

        vaga1_1, _ = Vaga.objects.get_or_create(
            evento=ev1, funcao='Recepcionista Credenciamento',
            defaults={'valor_diaria': 250.00, 'quantidade': 3, 'prazo_pagamento_dias': 5, 'status': 'ABERTA'}
        )

        # 5. CANDIDATURAS
        c1, _ = Candidatura.objects.get_or_create(
            vaga=vaga1_1, usuario=staff_objs[1],
            defaults={'status': 'APROVADO', 'aceitou_termo': True, 'data_aceite_termo': timezone.now()}
        )
        p1, _ = PresencaPagamento.objects.get_or_create(candidatura=c1)
        p1.status_deslocamento = 'CHECKIN_REALIZADO'
        p1.save()