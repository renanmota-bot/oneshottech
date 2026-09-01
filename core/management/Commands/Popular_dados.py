from django.core.management.base import BaseCommand
from core.models import Empresa, Usuario, FotoStaff
from eventos.models import Evento, Vaga, Candidatura, PresencaPagamento, PropostaComercial, AvisoEvento
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Povoa o banco de dados local com dados completos de teste para visualização perfeita dos painéis.'

    def handle(self, *args, **kwargs):
        self.stdout.write("⏳ Povoando banco de dados com dados completos...")

        # 1. EMPRESA DEMO
        empresa, _ = Empresa.objects.get_or_create(
            cnpj='11.222.333/0001-99',
            defaults={
                'nome': 'One Shot Eventos & BTL',
                'status': 'ATIVO',
                'plano': 'PREMIUM',
                'valor_plano': 299.00
            }
        )

        # 2. USUÁRIO PRODUTORA (ADMIN)
        admin_user, _ = Usuario.objects.get_or_create(
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
        admin_user.set_password('senha123')
        admin_user.save()

        # 3. ELENCO STAFF DIVERSO
        staffs_dados = [
            {
                'username': 'mariana.costa@email.com',
                'first_name': 'Mariana',
                'last_name': 'Costa',
                'cpf': '222.333.444-55',
                'rg': '23.456.789-0',
                'data_nascimento': '1998-05-14',
                'whatsapp': '11988887777',
                'tamanho_camiseta': 'M',
                'tamanho_calcado': '37',
                'chave_pix': 'mariana.costa@email.com',
                'tipo_chave_pix': 'E-mail',
                'status_aprovacao': 'APROVADO'
            },
            {
                'username': 'lucas.silva@email.com',
                'first_name': 'Lucas',
                'last_name': 'Silva',
                'cpf': '333.444.555-66',
                'rg': '12.345.678-9',
                'data_nascimento': '1995-11-20',
                'whatsapp': '11977776666',
                'tamanho_camiseta': 'G',
                'tamanho_calcado': '42',
                'chave_pix': '33344455566',
                'tipo_chave_pix': 'CPF/CNPJ',
                'status_aprovacao': 'APROVADO'
            },
            {
                'username': 'camila.rodrigues@email.com',
                'first_name': 'Camila',
                'last_name': 'Rodrigues',
                'cpf': '444.555.666-77',
                'rg': '34.567.890-1',
                'data_nascimento': '2001-02-08',
                'whatsapp': '11966665555',
                'tamanho_camiseta': 'P',
                'tamanho_calcado': '36',
                'chave_pix': 'camila.rodrigues@email.com',
                'tipo_chave_pix': 'E-mail',
                'status_aprovacao': 'PENDENTE'
            }
        ]

        staff_objs = []
        for sd in staffs_dados:
            st, _ = Usuario.objects.get_or_create(
                username=sd['username'],
                defaults={
                    'email': sd['username'],
                    'first_name': sd['first_name'],
                    'last_name': sd['last_name'],
                    'perfil': 'STAFF',
                    'empresa': empresa,
                    'cpf': sd['cpf'],
                    'rg': sd['rg'],
                    'data_nascimento': sd['data_nascimento'],
                    'whatsapp': sd['whatsapp'],
                    'tamanho_camiseta': sd['tamanho_camiseta'],
                    'tamanho_calcado': sd['tamanho_calcado'],
                    'chave_pix': sd['chave_pix'],
                    'tipo_chave_pix': sd['tipo_chave_pix'],
                    'status_aprovacao': sd['status_aprovacao']
                }
            )
            st.set_password('senha123')
            st.save()
            staff_objs.append(st)

        # 4. EVENTO ATIVO DEMO
        hoje = date.today()
        evento, _ = Evento.objects.get_or_create(
            nome='Convenção de Vendas BTL 2026',
            empresa=empresa,
            defaults={
                'data_inicio': hoje,
                'data_termino': hoje + timedelta(days=2),
                'local': 'Av. das Nações Unidas, Nº 12551 - do Sul, São Paulo - SP',
                'orcamento_previsto': 12000.00
            }
        )

        # 5. VAGAS
        vaga1, _ = Vaga.objects.get_or_create(
            evento=evento,
            funcao='Recepcionista BTL',
            defaults={'valor_diaria': 250.00, 'quantidade': 5, 'dress_code': 'Blazer preto, calça jeans e tênis branco'}
        )

        vaga2, _ = Vaga.objects.get_or_create(
            evento=evento,
            funcao='Supervisor de Operação',
            defaults={'valor_diaria': 400.00, 'quantidade': 2, 'dress_code': 'Camiseta polo preta da agência'}
        )

        # 6. CANDIDATURAS E INSCRITOS
        cand1, _ = Candidatura.objects.get_or_create(vaga=vaga1, usuario=staff_objs[0], defaults={'status': 'APROVADO'})
        cand2, _ = Candidatura.objects.get_or_create(vaga=vaga2, usuario=staff_objs[1], defaults={'status': 'APROVADO'})
        Candidatura.objects.get_or_create(vaga=vaga1, usuario=staff_objs[2], defaults={'status': 'PENDENTE'})

        # 7. PRESENÇAS E CHECK-INS GPS
        PresencaPagamento.objects.get_or_create(candidatura=cand1, defaults={'status_deslocamento': 'CHECKIN_REALIZADO'})
        PresencaPagamento.objects.get_or_create(candidatura=cand2, defaults={'status_deslocamento': 'A_CAMINHO'})

        # 8. AVISOS E PROPOSTAS
        AvisoEvento.objects.get_or_create(
            evento=evento,
            titulo='Ponto de Encontro & Briefing',
            defaults={'mensagem': 'Estar no portão 3 às 07:30 para o café e retirada dos crachás.'}
        )

        PropostaComercial.objects.get_or_create(
            empresa=empresa,
            cliente_nome='Multinacional BTL Ltda',
            defaults={
                'cliente_cnpj_cpf': '12.345.678/0001-90',
                'valor_total': 28500.00,
                'descricao_servicos': 'Fornecimento de equipe completa de casting, recepção e supervisão BTL para evento corporativo.',
                'status': 'APROVADA'
            }
        )

        self.stdout.write(self.style.SUCCESS("✅ BANCO DE DADOS LOCAL TOTALMENTE POVOADO!"))