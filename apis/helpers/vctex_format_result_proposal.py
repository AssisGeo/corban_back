from typing import Dict, Any


def format_proposal_response(proposal_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formata a resposta da criação de proposta para uma versão mais amigável ao usuário.

    Args:
        proposal_data (Dict[str, Any]): Dados da resposta da API de criação de proposta.

    Returns:
        Dict[str, Any]: Resposta formatada com mensagens amigáveis ao usuário.
    """
    data = proposal_data["data"]
    contract_number = data["proposalcontractNumber"]

    formatted_response = {
        "detalhes": {
            "numero_contrato": f"{contract_number}",
        },
        "contract_number": contract_number,
    }

    return formatted_response
