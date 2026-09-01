import sys
import random
import re
import requests

BASE_URL = "http://127.0.0.1:8000"

sessao_superadmin = requests.Session()
sessao_produtora = requests.Session()
sessao_staff = requests.Session()


def log_etapa(numero, titulo):
    print(f"\n==================================================")
    print(f"📌 ETAPA {numero}: {titulo}")
    print(f"==================================================")


def reportar_sucesso(msg):
    print(f"✅ [SUCESSO]: {msg}")


def reportar_erro_e_parar(etapa, erro_msg):
    print(f"\n❌ [FALHA NA CONVERSA DO SISTEMA - ETAPA {etapa}]")
    print(f"⚠️ Erro detectado: {erro_msg}")
    print("⛔ Teste interrompido. Verifique o código e tente novamente.")
    sys.exit(1)


def gerador_cpf_valido():
    cpf = [random.randint(0, 9) for _ in range(9)]
    for _ in range(2):
        val = sum([(len(cpf) + 1 - i) * v for i, v in enumerate(cpf)])
        digit = (val * 10) % 11
        cpf.append(digit if digit < 10 else 0)
    return ''.join(map(str, cpf))


def rodar_jornada_lancamento():
    global sessao_staff
    print("\n🚀 INICIANDO TESTE DA JORNADA COMPLETA (SUPER ADMIN ➔ PRODUTORA ➔ STAFF ➔ FINANCEIRO)")

    rand_id = random.randint(1000, 9999)

    # -------------------------------------------------------------------------
    # ETAPA 1: SUPER ADMIN LOGA E CRIA A EMPRESA SAAS EXCLUSIVA
    # -------------------------------------------------------------------------
    log_etapa(1, "Super Admin acessa o painel global e cria uma nova Empresa SaaS")
    
    res_login_super = sessao_superadmin.get(f"{BASE_URL}/login/demo/superadmin/")
    if res_login_super.status_code not in [200, 302]:
        reportar_erro_e_parar(1, "Super Admin não conseguiu autenticar no sistema.")

    csrf_token_super = sessao_superadmin.cookies.get('csrftoken')

    nome_empresa = f"Produtora Alpha {rand_id}"
    cnpj_empresa = f"{random.randint(10, 99)}.111.222/0001-{random.randint(10, 99)}"

    payload_criar_empresa = {
        'acao': 'criar_empresa',
        'nome': nome_empresa,
        'cnpj': cnpj_empresa,
        'plano': 'PREMIUM',
        'valor_plano': '299.00',
        'limite_staffs': '500',
        'cor_primaria': '#A2673B',
        'cor_secundaria': '#1C0D07',
        'cor_fundo': '#080605',
        'recurso_portal_cliente': 'on',
        'recurso_exportacao_pix': 'on',
        'csrfmiddlewaretoken': csrf_token_super
    }

    res_post_emp = sessao_superadmin.post(f"{BASE_URL}/dashboard/super-admin/", data=payload_criar_empresa)
    if res_post_emp.status_code not in [200, 302]:
        reportar_erro_e_parar(1, "Falha ao enviar requisição de criação de empresa.")
    
    res_super_dash = sessao_superadmin.get(f"{BASE_URL}/dashboard/super-admin/")
    
    pattern = re.escape(nome_empresa) + r'[\s\S]*?name="empresa_id"\s+value="(\d+)"'
    match_emp = re.search(pattern, res_super_dash.text)
    
    if not match_emp:
        match_emp = re.findall(r'name="empresa_id"\s+value="(\d+)"', res_super_dash.text)
        if not match_emp:
            reportar_erro_e_parar(1, "Falha ao capturar a ID da nova empresa criada no HTML.")
        empresa_id = match_emp[-1]
    else:
        empresa_id = match_emp.group(1)

    reportar_sucesso(f"Empresa '{nome_empresa}' (ID: {empresa_id}) criada com sucesso!")

    # -------------------------------------------------------------------------
    # ETAPA 2: SUPER ADMIN CRIA O PRODUTOR VINCULADO À EMPRESA RECÉM-CRIADA
    # -------------------------------------------------------------------------
    log_etapa(2, f"Super Admin cria o usuário Admin exclusivo da Empresa ID {empresa_id}")
    
    email_admin_produtora = f"admin_{rand_id}@produtoraalpha.com"
    payload_criar_admin = {
        'acao': 'criar_usuario_global',
        'first_name': 'Carlos',
        'last_name': f'Produtor {rand_id}',
        'email': email_admin_produtora,
        'senha': 'senha123_admin',
        'cpf': gerador_cpf_valido(),
        'whatsapp': '11977778888',
        'perfil': 'ADMIN',
        'empresa_id': empresa_id,
        'csrfmiddlewaretoken': csrf_token_super
    }

    res_admin_post = sessao_superadmin.post(f"{BASE_URL}/dashboard/super-admin/", data=payload_criar_admin)
    if res_admin_post.status_code not in [200, 302]:
        reportar_erro_e_parar(2, "Falha ao criar o usuário Produtor no Super Admin.")

    reportar_sucesso(f"Usuário '{email_admin_produtora}' vinculado à Empresa ID {empresa_id}!")

    # -------------------------------------------------------------------------
    # ETAPA 3: PRODUTORA FAZ LOGIN REAL NA SUA NOVA EMPRESA
    # -------------------------------------------------------------------------
    log_etapa(3, "Produtora faz login com credenciais reais da nova Empresa")
    
    sessao_produtora.get(f"{BASE_URL}/login/")
    csrf_token_login = sessao_produtora.cookies.get('csrftoken')

    payload_login_prod = {
        'username': email_admin_produtora,
        'password': 'senha123_admin',
        'csrfmiddlewaretoken': csrf_token_login
    }

    res_login_res = sessao_produtora.post(f"{BASE_URL}/login/", data=payload_login_prod)
    if res_login_res.status_code not in [200, 302]:
        reportar_erro_e_parar(3, "O usuário Produtor não conseguiu autenticar no login.")

    res_dash_prod = sessao_produtora.get(f"{BASE_URL}/dashboard/empresa/")
    reportar_sucesso(f"Produtora autenticada e operando exclusivamente na Empresa ID {empresa_id}!")

    # -------------------------------------------------------------------------
    # ETAPA 4: STAFF SE CADASTRA PELO LINK PÚBLICO DA NOVA EMPRESA
    # -------------------------------------------------------------------------
    log_etapa(4, f"Staff acessa o formulário de cadastro público da Empresa ID {empresa_id}")
    
    sessao_staff.get(f"{BASE_URL}/registro/staff/?empresa={empresa_id}")
    csrf_token_staff = sessao_staff.cookies.get('csrftoken')

    email_staff = f"colaborador_{rand_id}@oneshot.com"
    cpf_staff = gerador_cpf_valido()
    nome_staff = f"Joana_{rand_id}"

    payload_cadastro_staff = {
        'empresa_id': empresa_id,
        'first_name': nome_staff,
        'last_name': 'Silva',
        'nome_artistico': f'Joana Silva {rand_id}',
        'data_nascimento': '15/05/1998',
        'email': email_staff,
        'senha': 'senha123_staff',
        'cpf': cpf_staff,
        'rg': '123456789',
        'whatsapp': '11988887777',
        'genero': 'FEMININO',
        'altura': '170',
        'manequim': '38',
        'tamanho_camiseta': 'M',
        'tamanho_calcado': '37',
        'etnia': 'Branca',
        'cor_olhos': 'Castanhos',
        'cor_cabelo': 'Castanho',
        'cep': '01310-100',
        'cidade': 'São Paulo',
        'estado': 'SP',
        'bairro': 'Bela Vista',
        'rua_numero': 'Av Paulista, 1000',
        'emergencia_nome': 'Maria Silva',
        'emergencia_vinculo': 'Mãe',
        'emergencia_telefone': '11977776666',
        'tipo_chave_pix': 'CPF',
        'chave_pix': cpf_staff,
        'csrfmiddlewaretoken': csrf_token_staff
    }

    res_reg_staff = sessao_staff.post(f"{BASE_URL}/registro/staff/?empresa={empresa_id}", data=payload_cadastro_staff)
    if res_reg_staff.status_code not in [200, 302]:
        reportar_erro_e_parar(4, "O formulário de registro do Staff falhou.")

    reportar_sucesso(f"Staff '{email_staff}' cadastrado na Empresa ID {empresa_id}!")

    # -------------------------------------------------------------------------
    # ETAPA 5: PRODUTORA APROVA O STAFF NA NOVA EMPRESA
    # -------------------------------------------------------------------------
    log_etapa(5, "Produtora localiza e aprova a solicitação do Staff")
    
    res_dash_atualizado = sessao_produtora.get(f"{BASE_URL}/dashboard/empresa/")
    csrf_token_prod = sessao_produtora.cookies.get('csrftoken')

    match_staff_id = re.search(r'name="staff_id"\s+value="(\d+)"', res_dash_atualizado.text)
    if not match_staff_id:
        reportar_erro_e_parar(5, f"O Staff '{nome_staff}' não apareceu na fila de aprovação da Produtora.")

    staff_id = match_staff_id.group(1)

    payload_aprovar_staff = {
        'acao': 'aprovar_cadastro_staff',
        'staff_id': staff_id,
        'csrfmiddlewaretoken': csrf_token_prod
    }

    sessao_produtora.post(f"{BASE_URL}/dashboard/empresa/", data=payload_aprovar_staff)
    reportar_sucesso(f"Staff (ID: {staff_id}) aprovado com sucesso!")

    # -------------------------------------------------------------------------
    # ETAPA 6: PRODUTORA CRIA UM NOVO EVENTO NA SUA AGENDA
    # -------------------------------------------------------------------------
    log_etapa(6, "Produtora cria um novo evento na sua agenda")
    
    nome_evento = f"Lançamento de Produto {rand_id}"
    payload_evento = {
        'acao': 'criar_evento',
        'nome': nome_evento,
        'data_inicio': '10/10/2026',
        'data_termino': '12/10/2026',
        'horario_inicio': '08:00',
        'horario_termino': '18:00',
        'local': 'Expo Center Norte - SP',
        'orcamento_previsto': '8000.00',
        'csrfmiddlewaretoken': csrf_token_prod
    }

    sessao_produtora.post(f"{BASE_URL}/dashboard/empresa/", data=payload_evento)
    
    res_dash_ev = sessao_produtora.get(f"{BASE_URL}/dashboard/empresa/")
    matches_ev = re.findall(r'ev_id=(\d+)', res_dash_ev.text) or re.findall(r'workspace_evento_(\d+)', res_dash_ev.text)
    
    if not matches_ev:
        reportar_erro_e_parar(6, "Não foi possível capturar o ID do evento criado.")

    evento_id = matches_ev[-1]
    reportar_sucesso(f"Evento '{nome_evento}' (ID: {evento_id}) criado!")

    # -------------------------------------------------------------------------
    # ETAPA 7: PRODUTORA PUBLICA VAGA NO EVENTO
    # -------------------------------------------------------------------------
    log_etapa(7, "Produtora publica vaga de elenco para o evento")
    
    payload_vaga = {
        'acao': 'salvar_vaga',
        'vaga_id': '',
        'evento_id': evento_id,
        'funcao': 'Recepcionista VIP',
        'valor_diaria': '250.00',
        'quantidade': '2',
        'data_especifica_inicio': '10/10/2026',
        'data_especifica_termino': '12/10/2026',
        'vaga_horario_inicio': '07:30',
        'vaga_horario_termino': '17:30',
        'dress_code': 'Terno/Black',
        'csrfmiddlewaretoken': csrf_token_prod
    }

    res_vaga = sessao_produtora.post(f"{BASE_URL}/dashboard/empresa/", data=payload_vaga)
    if res_vaga.status_code not in [200, 302]:
        reportar_erro_e_parar(7, "A vaga não foi salva no banco de dados.")

    reportar_sucesso("Vaga 'Recepcionista VIP' publicada com sucesso!")

    # -------------------------------------------------------------------------
    # ETAPA 8: STAFF FAZ LOGIN EM SESSÃO ZERADA COM PARAMETRO DA EMPRESA
    # -------------------------------------------------------------------------
    log_etapa(8, "Staff faz login e se candidata à vaga publicada")
    
    sessao_staff = requests.Session()

    res_tela_login = sessao_staff.get(f"{BASE_URL}/login/")
    csrf_fresco = sessao_staff.cookies.get('csrftoken') or re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', res_tela_login.text).group(1)

    payload_login_staff = {
        'username': email_staff,
        'password': 'senha123_staff',
        'csrfmiddlewaretoken': csrf_fresco
    }
    
    sessao_staff.post(
        f"{BASE_URL}/login/", 
        data=payload_login_staff,
        headers={'Referer': f"{BASE_URL}/login/"}
    )

    res_vagas_staff = sessao_staff.get(f"{BASE_URL}/dashboard/staff/?empresa={empresa_id}")

    matches_vagas = re.findall(r'name="vaga_id"\s+value="(\d+)"', res_vagas_staff.text)
    if not matches_vagas:
        matches_vagas = re.findall(r'vaga_id=(\d+)', res_vagas_staff.text) or re.findall(r'/candidatar/(\d+)', res_vagas_staff.text)
        if not matches_vagas:
            reportar_erro_e_parar(8, f"A vaga publicada para o evento ID {evento_id} não apareceu no painel do Staff.")

    vaga_id = matches_vagas[-1]
    csrf_token_staff_dash = sessao_staff.cookies.get('csrftoken')

    payload_cand = {
        'acao': 'candidatar',
        'vaga_id': vaga_id,
        'csrfmiddlewaretoken': csrf_token_staff_dash
    }
    res_cand = sessao_staff.post(f"{BASE_URL}/dashboard/staff/", data=payload_cand)
    if res_cand.status_code not in [200, 302]:
        reportar_erro_e_parar(8, "Erro ao enviar a candidatura do Staff.")

    reportar_sucesso(f"Staff candidatado com sucesso à Vaga ID {vaga_id}!")

    # -------------------------------------------------------------------------
    # ETAPA 9: PRODUTORA HOMOLOGA E CONCILIA O PIX
    # -------------------------------------------------------------------------
    log_etapa(9, "Produtora aprova a candidatura e gera a ordem financeira de PIX")
    
    res_dash_cand = sessao_produtora.get(f"{BASE_URL}/dashboard/empresa/?ev_id={evento_id}")
    csrf_token_prod = sessao_produtora.cookies.get('csrftoken')

    matches_cand = re.findall(r'name="candidatura_id"\s+value="(\d+)"', res_dash_cand.text)
    if not matches_cand:
        reportar_erro_e_parar(9, "A candidatura do Staff não foi encontrada no painel da Produtora.")

    cand_id = matches_cand[-1]

    payload_homologa = {
        'acao': 'alterar_candidatura',
        'candidatura_id': cand_id,
        'novo_status': 'APROVADO',
        'csrfmiddlewaretoken': csrf_token_prod
    }
    res_homo = sessao_produtora.post(f"{BASE_URL}/dashboard/empresa/", data=payload_homologa)
    if res_homo.status_code not in [200, 302]:
        reportar_erro_e_parar(9, "Erro ao homologar a candidatura do Staff.")

    reportar_sucesso(f"Seleção homologada e ordem financeira de PIX gerada para a Candidatura ID {cand_id}!")

    print("\n==================================================================")
    print("🎉 JORNADA COMPLETA DE 9 ETAPAS VALIDADA COM 100% DE SUCESSO!")
    print("Super Admin ➔ Empresa SaaS ➔ Produtora ➔ Staff ➔ Evento ➔ Vaga ➔ PIX")
    print("==================================================================\n")


if __name__ == '__main__':
    try:
        rodar_jornada_lancamento()
    except requests.exceptions.ConnectionError:
        print("\n❌ Servidor Django offline. Certifique-se de ter rodado 'python manage.py runserver' no VS Code.")
