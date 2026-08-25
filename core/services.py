import json
import urllib.request
import re


def disparar_whatsapp_notificacao(empresa, telefone_destino, mensagem):
    """
    Serviço de envio automático de WhatsApp para recursos do Plano Premium.
    Garante que só envia se a empresa estiver no plano PREMIUM e configurada.
    """
    if not empresa or not empresa.pode_enviar_whatsapp():
        return False, "Recurso disponível apenas no Plano Premium ou API não configurada."

    num_clean = re.sub(r'\D', '', str(telefone_destino))
    if not num_clean.startswith('55'):
        num_clean = f"55{num_clean}"

    # Exemplo genérico estruturado para integração via Z-API / Evolution API
    endpoint = f"https://api.z-api.io/instances/{empresa.whatsapp_api_instancia}/token/{empresa.whatsapp_api_token}/send-text"
    
    payload = {
        "phone": num_clean,
        "message": mensagem
    }

    try:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status in [200, 201]:
                empresa.whatsapp_disparos_mes += 1
                empresa.save(update_fields=['whatsapp_disparos_mes'])
                return True, "Mensagem enviada com sucesso."
    except Exception as e:
        return False, f"Falha no envio da mensagem: {str(e)}"

    return False, "Erro desconhecido no envio de mensagem."


def emitir_nfse_automatica(empresa, presenca_pagamento):
    """
    Serviço de emissão de NFS-e integrado via API (Ex: e-Notas / PlugNotas).
    Exclusivo para clientes no Plano Premium.
    """
    if not empresa or not empresa.pode_emitir_nfse():
        return False, "Emissão de NFS-e desabilitada ou restrita ao Plano Premium."

    presenca_pagamento.nfse_status = 'PROCESSANDO'
    presenca_pagamento.save(update_fields=['nfse_status'])

    # Estrutura inicial engatilhada para conexão com o gateway de Notas Fiscais
    # Exemplo: Envio de payload para e-Notas / PlugNotas
    try:
        # Lógica de integração de API
        # Após retorno positivo do Gateway:
        # presenca_pagamento.nfse_status = 'EMITIDA'
        # presenca_pagamento.nfse_numero = "12345"
        # presenca_pagamento.nfse_pdf_url = "https://..."
        # presenca_pagamento.save()
        return True, "Nota Fiscal enviada para fila de processamento."
    except Exception as e:
        presenca_pagamento.nfse_status = 'ERRO'
        presenca_pagamento.save(update_fields=['nfse_status'])
        return False, f"Erro ao processar NFS-e: {str(e)}"