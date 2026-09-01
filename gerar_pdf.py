from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm

def draw_cover(canvas, doc):
    """Desenha a capa com fundo escuro e cores neon, alinhado ao design do sistema."""
    canvas.saveState()
    
    # Fundo Escuro (Slate 950)
    canvas.setFillColor(colors.HexColor("#020617"))
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    
    # Detalhe Visual (Barra lateral neon)
    canvas.setFillColor(colors.HexColor("#0ea5e9"))
    canvas.rect(0, 0, 15, A4[1], fill=1, stroke=0)

    # Título Principal
    canvas.setFont('Helvetica-Bold', 42)
    canvas.setFillColor(colors.HexColor("#38bdf8"))
    canvas.drawString(3 * cm, A4[1] - 12 * cm, "ONE SHOT TECH")
    
    # Subtítulo
    canvas.setFont('Helvetica-Bold', 18)
    canvas.setFillColor(colors.white)
    canvas.drawString(3 * cm, A4[1] - 13.5 * cm, "Control Tower BTL & Live Marketing")

    # Linha divisória
    canvas.setStrokeColor(colors.HexColor("#334155"))
    canvas.setLineWidth(1)
    canvas.line(3 * cm, A4[1] - 14.5 * cm, A4[0] - 3 * cm, A4[1] - 14.5 * cm)
    
    # Descrição da Capa
    canvas.setFont('Helvetica', 12)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawString(3 * cm, A4[1] - 15.5 * cm, "Especificações Técnicas, Arquitetura e Viabilidade Comercial")

    # Rodapé da Capa
    canvas.setFont('Helvetica-Bold', 10)
    canvas.setFillColor(colors.HexColor("#475569"))
    canvas.drawString(3 * cm, 3 * cm, "CONFIDENCIAL E PROPRIETÁRIO — GERAÇÃO AUTOMATIZADA")
    
    canvas.restoreState()

def draw_normal_page(canvas, doc):
    """Desenha o cabeçalho e rodapé das páginas internas."""
    canvas.saveState()
    
    # Linha de Cabeçalho
    canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
    canvas.setLineWidth(1)
    canvas.line(2 * cm, A4[1] - 1.5 * cm, A4[0] - 2 * cm, A4[1] - 1.5 * cm)
    
    canvas.setFont('Helvetica-Bold', 9)
    canvas.setFillColor(colors.HexColor("#0ea5e9"))
    canvas.drawString(2 * cm, A4[1] - 1.2 * cm, "ONE SHOT TECH")
    
    # Rodapé
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawString(2 * cm, 1.5 * cm, f"Página {doc.page}")
    canvas.drawRightString(A4[0] - 2 * cm, 1.5 * cm, "Soluções para Produtoras BTL")
    
    canvas.restoreState()

def gerar_apresentacao_premium():
    pdf_filename = "Apresentacao_OneShot_Tech_Premium.pdf"
    doc = SimpleDocTemplate(
        pdf_filename, 
        pagesize=A4, 
        rightMargin=2*cm, 
        leftMargin=2*cm, 
        topMargin=2.5*cm, 
        bottomMargin=2.5*cm
    )
    
    styles = getSampleStyleSheet()
    elements = []

    # ==========================================
    # ESTILOS DE TEXTO
    # ==========================================
    h1 = ParagraphStyle('H1', fontName='Helvetica-Bold', fontSize=22, textColor=colors.HexColor("#0f172a"), spaceAfter=15, spaceBefore=20)
    h2 = ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor("#0284c7"), spaceAfter=10, spaceBefore=15)
    body = ParagraphStyle('Body', fontName='Helvetica', fontSize=11, leading=16, textColor=colors.HexColor("#334155"), spaceAfter=10, alignment=4) # alignment=4 é justificado
    highlight = ParagraphStyle('Highlight', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor("#0f172a"), spaceBefore=10, spaceAfter=10, leftIndent=10, borderPadding=10, backColor=colors.HexColor("#f1f5f9"))

    # ==========================================
    # PÁGINA DE ROSTO E INTRODUÇÃO
    # ==========================================
    elements.append(PageBreak()) # Quebra a capa
    
    elements.append(Paragraph("1. O Desafio da Gestão BTL", h1))
    elements.append(Paragraph("A gestão de eventos de Live Marketing (BTL) sofre com processos manuais fragmentados. O uso de PDFs montados à mão para aprovação de casting, planilhas descentralizadas para controle financeiro e a falta de rastreabilidade física dos colaboradores geram perdas de margem e atritos com o cliente final.", body))
    
    elements.append(Paragraph("2. A Solução: Control Tower BTL", h1))
    elements.append(Paragraph("O <b>One Shot Tech</b> é a plataforma definitiva para produtoras modernas. Ele unifica o <i>Atendimento, a Produção e o Financeiro</i> em um único ecossistema focado no evento, eliminando gargalos operacionais e blindando a rentabilidade da agência.", body))

    elements.append(Paragraph("Vantagens Competitivas Imediatas:", highlight))
    vantagens = [
        ["🚀 Aceleração de Vendas", "O Portal Interativo do Cliente permite aprovação de casting via celular."],
        ["📍 Operação Antifraude", "Check-in via GPS (Cálculo de Haversine) e selfie obrigatória no local do evento."],
        ["💰 Blindagem Financeira", "DRE gerado em tempo real, travando o orçamento e calculando a margem líquida."],
        ["⚡ Liquidação PIX Automática", "Exportação em lote de arquivo CSV para pagamentos de diárias em segundos."]
    ]
    
    t_vantagens = Table(vantagens, colWidths=[4.5*cm, 11.5*cm])
    t_vantagens.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor("#0ea5e9")),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('TEXTCOLOR', (1,0), (1,-1), colors.HexColor("#475569")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(t_vantagens)
    elements.append(Spacer(1, 10))

    # ==========================================
    # TABELA DE ESPECIFICAÇÕES TÉCNICAS
    # ==========================================
    elements.append(Paragraph("3. Especificações Técnicas e Módulos", h1))
    
    modulos_data = [
        ["Módulo", "Especificação Funcional", "Impacto no Negócio"],
        
        ["Gestão de Casting\n& Banco VIP", 
         "Fichas técnicas inteligentes, book de fotos integrado, marcação de talentos VIP e bloqueio de inadimplentes via Blacklist interna.", 
         "Garante a alocação dos melhores profissionais e evita recontratação de staffs problemáticos."],
         
        ["Aprovação Externa\n(Portal do Cliente)", 
         "Link de acesso web seguro via Token. O cliente visualiza a equipe proposta e aprova/recusa candidatos instantaneamente.", 
         "Corta o tempo de aprovação pela metade, eliminando a dependência de WhatsApp e PDFs pesados."],
         
        ["Tracking & GPS\n(QG Operacional)", 
         "Sistema de check-in integrado. O colaborador registra chegada anexando selfie e coordenadas geográficas reais.", 
         "Reduz a zero os atrasos mascarados e faltas não reportadas."],
         
        ["Logística de Campo\n(Equipamentos)", 
         "Checklist individual digital para marcação de entrega e devolução de rádios comunicadores, credenciais e uniformes.", 
         "Elimina o prejuízo da produtora com perda ou roubo de equipamentos caros."],
         
        ["DRE & Controladoria\n(Financeiro)", 
         "Consolidação de Propostas Comerciais, cálculo do Custo de Staff e apuração instantânea do Lucro Líquido. Emissão de NFS-e e arquivo de lote PIX.", 
         "Fornece previsibilidade de caixa total à diretoria e simplifica o faturamento."],
    ]

    t_modulos = Table(modulos_data, colWidths=[3.5*cm, 8.5*cm, 4*cm], repeatRows=1)
    t_modulos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")), # Cabeçalho escuro
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,1), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,1), (0,-1), colors.HexColor("#0f172a")),
        ('FONTNAME', (1,1), (-1,-1), 'Helvetica'),
        ('TEXTCOLOR', (1,1), (-1,-1), colors.HexColor("#334155")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]), # Linhas zebradas
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(t_modulos)

    # Gera o PDF aplicando os templates de Capa e Páginas Normais
    doc.build(elements, onFirstPage=draw_cover, onLaterPages=draw_normal_page)
    print(f"✅ Documento Premium gerado com sucesso: {pdf_filename}")

if __name__ == "__main__":
    gerar_apresentacao_premium()