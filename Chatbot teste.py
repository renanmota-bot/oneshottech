import streamlit as st

st.set_page_config(
    page_title="One Shot Tech — Checklist Executivo",
    page_icon="⚡",
    layout="wide"
)

# Estilização em Dark Mode / Glassmorphism
st.markdown("""
    <style>
    .stApp {
        background-color: #020617;
        color: #f8fafc;
    }
    .stCheckbox > label {
        font-size: 0.95rem;
        color: #cbd5e1;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 800;
        color: #38bdf8;
    }
    </style>
""", unsafe_allow_html=True)

# Estrutura do Checklist
checklist_data = {
    "📅 Hub & Arquitetura Event-First": [
        "Visão Cronológica de Eventos: Organização por data (Ativos, Próximos e Concluídos).",
        "Workspace Dedicado: Painel operacional exclusivo para cada evento.",
        "Resumo de Métricas no Card: Exibição de vagas, faturamento e margem DRE estimada."
    ],
    "🎭 Casting & Seleção de Elenco": [
        "Publicação de Vagas: Cadastro com função, valor da diária, vagas, prazo e dress code.",
        "Visual Casting: Fichas técnicas completas com fotos do book, medidas e nota média.",
        "Dupla Validação de Seleção: Status dinâmicos (Aprovado pelo Cliente ➔ Validado pela Agência).",
        "Exportação de Casting em PDF: Geração de documento formatado para envio ao cliente."
    ],
    "🌐 Portal de Seleção do Cliente (Externo)": [
        "Acesso Tokenizado sem Login: Link público exclusivo por evento para aprovação via celular.",
        "Aprovação/Recusa em 1 Clique: Interface intuitiva para o cliente pré-selecionar o elenco.",
        "Galeria do Elenco: Visualização do book de fotos e especificações de cada colaborador."
    ],
    "🚗 QG Operacional & Presença via GPS": [
        "Check-in Antifraude por Geolocalização: Validação de presença por raio de distância (Haversine).",
        "Validação por Selfie: Foto em tempo real enviada pelo colaborador na chegada.",
        "Painel de Validação em Tempo Real: Alerta de check-ins pendentes para o produtor."
    ],
    "📦 Logística & Controle de Materiais": [
        "Checklist de Equipamentos: Registro de entrega/devolução de uniformes, credenciais e rádios.",
        "Rastreamento Operacional: Controle dos itens sob responsabilidade de cada colaborador."
    ],
    "💰 Financeiro, Propostas & NFS-e": [
        "DRE em Tempo Real por Evento: Cálculo automático de lucratividade (Faturado - Custos).",
        "Gestão Comercial: Cadastro e acompanhamento de Propostas Comerciais.",
        "Emissão de NFS-e: Controle e registro do número de confirmação de Notas Fiscais.",
        "Pagamento PIX em Lote: Baixa individual ou em massa das diárias da equipe.",
        "Exportação Bancária (CSV): Arquivo CSV formatado com dados bancários/PIX para o banco."
    ],
    "👥 Banco de Elenco Geral, VIP & Blacklist": [
        "Selo Elenco VIP: Destaque visual para profissionais de alta performance.",
        "Bloqueio por Blacklist: Trava interna para impedir candidaturas indesejadas.",
        "Filtro de Busca Rápida: Pesquisa por nome, CPF ou especificações da ficha técnica."
    ],
    "🏁 Eventos Concluídos & Relatórios": [
        "Histórico de Ações Encerradas: Consulta de relatórios de eventos finalizados.",
        "Exportação de Pagamentos por Evento: Download em CSV dos colaboradores e diárias do evento."
    ]
}

# Título do App
st.title("⚡ One Shot Tech — Control Tower BTL")
st.caption("Painel Interativo de Acompanhamento das Funcionalidades da Plataforma")

# Cálculo de progresso em tempo real
total_items = sum(len(items) for items in checklist_data.values())
completed_items = 0

for category, items in checklist_data.items():
    for idx in range(len(items)):
        key = f"{category}_{idx}"
        if st.session_state.get(key, False):
            completed_items += 1

progress_pct = completed_items / total_items if total_items > 0 else 0.0

# Cards de Métricas (KPIs)
col1, col2, col3 = st.columns(3)
col1.metric("Total de Funcionalidades", total_items)
col2.metric("Validadas / Ativas", completed_items)
col3.metric("Prontidão do Sistema", f"{int(progress_pct * 100)}%")

st.progress(progress_pct)
st.divider()

# Exibição dos módulos e itens marcáveis
for category, items in checklist_data.items():
    st.subheader(category)
    for idx, item in enumerate(items):
        key = f"{category}_{idx}"
        st.checkbox(item, key=key)
    st.write("")