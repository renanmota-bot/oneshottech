from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from core.models import Empresa, Usuario
from eventos.models import Evento, Vaga, Candidatura, PresencaPagamento, AvisoEvento, PropostaComercial


class Command(BaseCommand):
    help = 'Popula o banco de dados com dados de demonstração completos.'

    def handle(self, *args, **kwargs):
        self.stdout.write('🚀 Iniciando geração de dados de teste...')

        # ==========================================
        # 1. PRODUTORAS (EMPRESAS)
        # ==========================================
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

        emp_bloqueada, _ = Empresa.objects.get_or_create(
            cnpj='77.888.999/0001-77',
            defaults={
                'nome': 'Live Marketing Suspensa LTDA',
                'status': 'BLOQUEADO',
                'plano': 'BASICO',
                'valor_plano': 150.00,
                'whatsapp': '11977773333'
            }
        )

        # ==========================================
        # 2. USUÁRIOS ADMINS & SUPER ADMIN
        # ==========================================
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
            username='admin_oneshot',
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
            username='admin_vibe',
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

        # ==========================================
        # 3. BASE DE STAFFS
        # ==========================================
        staffs_dados = [
            ('lucas.silva@email.com', 'Lucas', 'Silva', '111.222.333-44', '12.345.678-9', '11911112222', 'CPF/CNPJ', '11122233344', 4.9),
            ('mariana.costa@email.com', 'Mariana', 'Costa', '222.333.444-55', '23.456.789-0', '11922223333', 'E-mail', 'mariana.costa@email.com', 5.0),
            ('bruno.oliveira@email.com', 'Bruno', 'Oliveira', '333.444.555-66', '34.567.890-1', '11933334444', 'Celular', '11933334444', 4.7),
            ('camila.santos@email.com', 'Camila', 'Santos', '444.555.666-77', '45.678.901-2', '11944445555', 'Chave Aleatória', 'pix-camila-key-99', 4.8),
            ('rodrigo.lima@email.com', 'Rodrigo', 'Lima', '555.666.777-88', '56.789.012-3', '11955556666', 'CPF/CNPJ', '55566677788', 4.5),
        ]

        staff_objs = []
        for email, nome, sobrenome, cpf, rg, whats, t_pix, c_pix, nota in staffs_dados:
            u, created = Usuario.objects.get_or_create(
                username=email,
                defaults={
                    'email': email,
                    'first_name': nome,
                    'last_name': sobrenome,
                    'cpf': cpf,
                    'rg': rg,
                    'whatsapp': whats,
                    'tipo_chave_pix': t_pix,
                    'chave_pix': c_pix,
                    'nota_media': nota,
                    'perfil': 'STAFF',
                    'empresa': emp_oneshot
                }
            )
            u.set_password('senha123')
            u.save()
            staff_objs.append(u)

        # ==========================================
        # 4. EVENTOS & VAGAS
        # ==========================================
        hoje = date.today()

        # EVENTO 1 (PREMIUM - ATIVO)
        ev1, _ = Evento.objects.get_or_create(
            nome='Tech Innovation Summit 2026',
            empresa=emp_oneshot,
            defaults={
                'local': 'Avenida das Nações Unidas, 12551 - Brooklin, São Paulo - SP',
                'latitude': -23.6091,
                'longitude': -46.6968,
                'data_inicio': hoje + timedelta(days=2),
                'data_termino': hoje + timedelta(days=4),
                'dress_code': 'Camiseta preta oficial da marca, calça jeans escura e tênis preto.',
                'orcamento_previsto': 12500.00
            }
        )

        vaga1_1, _ = Vaga.objects.get_or_create(
            evento=ev1, funcao='Recepcionista Credenciamento',
            defaults={'valor_diaria': 250.00, 'quantidade': 3, 'prazo_pagamento_dias': 5, 'status': 'ABERTA'}
        )
        vaga1_2, _ = Vaga.objects.get_or_create(
            evento=ev1, funcao='Promotor de Estande',
            defaults={'valor_diaria': 200.00, 'quantidade': 2, 'prazo_pagamento_dias': 5, 'status': 'PREENCHIDA'}
        )

        # MURAL DE AVISOS NO EVENTO 1
        AvisoEvento.objects.get_or_create(
            evento=ev1, titulo='Ponto de Encontro e Credenciamento',
            defaults={'mensagem': 'Chegar com 20 minutos de antecedência no Portão 3 para alinhamento e entrega dos crachás.'}
        )
        AvisoEvento.objects.get_or_create(
            evento=ev1, titulo='Almoço e Intervalo',
            defaults={'mensagem': 'O buffet de alimentação estará liberado no piso superior das 12h às 14h.'}
        )

        # EVENTO 2 (BÁSICO - ATIVO)
        ev2, _ = Evento.objects.get_or_create(
            nome='Convenção Nacional de Vendas Retail',
            empresa=emp_vibe,
            defaults={
                'local': 'Rua General Sócrates, 55 - Penha de França, São Paulo - SP',
                'latitude': -23.5230,
                'longitude': -46.5490,
                'data_inicio': hoje + timedelta(days=1),
                'data_termino': hoje + timedelta(days=1),
                'dress_code': 'Camisa polo branca, calça jeans e tênis confortável.',
                'orcamento_previsto': 3000.00
            }
        )

        vaga2_1, _ = Vaga.objects.get_or_create(
            evento=ev2, funcao='Apoio de Produção',
            defaults={'valor_diaria': 180.00, 'quantidade': 2, 'prazo_pagamento_dias': 0, 'status': 'ABERTA'}
        )

        # ==========================================
        # 5. CANDIDATURAS, CHECK-INS & AVALIAÇÕES
        # ==========================================
        # Mariana Aprovada na Vaga 1.1
        c1, _ = Candidatura.objects.get_or_create(
            vaga=vaga1_1, usuario=staff_objs[1],
            defaults={'status': 'APROVADO', 'aceitou_termo': True, 'data_aceite_termo': timezone.now()}
        )
        p1, _ = PresencaPagamento.objects.get_or_create(candidatura=c1)
        p1.status_deslocamento = 'CHECKIN_REALIZADO'
        p1.nota_desempenho = 5
        p1.comentario_desempenho = 'Pontualíssima e excelente atendimento no credenciamento VIP.'
        p1.save()

        # Lucas Aprovado na Vaga 1.2
        c2, _ = Candidatura.objects.get_or_create(
            vaga=vaga1_2, usuario=staff_objs[0],
            defaults={'status': 'APROVADO', 'aceitou_termo': True, 'data_aceite_termo': timezone.now()}
        )
        p2, _ = PresencaPagamento.objects.get_or_create(candidatura=c2)
        p2.status_deslocamento = 'VALIDADO'
        p2.status_pagamento = 'PAGO'
        p2.valor_pago = 200.00
        p2.save()

        # Camila Inscrita Pendente
        Candidatura.objects.get_or_create(
            vaga=vaga1_1, usuario=staff_objs[3],
            defaults={'status': 'PENDENTE', 'aceitou_termo': True, 'data_aceite_termo': timezone.now()}
        )

        # ==========================================
        # 6. PROPOSTAS COMERCIAIS (PREMIUM)
        # ==========================================
        PropostaComercial.objects.get_or_create(
            empresa=emp_oneshot,
            cliente_nome='Samsung Eletrônicos da Amazônia LTDA',
            defaults={
                'evento': ev1,
                'cliente_cnpj_cpf': '00.280.273/0001-37',
                'cliente_email': 'eventos@samsung.com.br',
                'cliente_endereco': 'Avenida Chucri Zaidan, 1500 - São Paulo/SP',
                'valor_total': 38500.00,
                'descricao_servicos': 'Fornecimento e gestão de 15 recepcionistas bilingual e apoio de produção para o lançamento da linha S26.',
                'status': 'APROVADA',
                'nfse_status': 'EMITIDA',
                'nfse_numero': 'NFS-000189'
            }
        )

        PropostaComercial.objects.get_or_create(
            empresa=emp_oneshot,
            cliente_nome='Nivea Brasil Cosméticos',
            defaults={
                'cliente_cnpj_cpf': '60.803.111/0001-02',
                'cliente_email': 'compras@nivea.com.br',
                'valor_total': 18200.00,
                'descricao_servicos': 'Ação de ativação de marca em praias e festivais do litoral paulista.',
                'status': 'ENVIADA',
                'nfse_status': 'NAO_EMITIDA'
            }
        )

        self.stdout.write(self.style.SUCCESS('✅ Banco de dados populado com sucesso com dados de demonstração!'))
