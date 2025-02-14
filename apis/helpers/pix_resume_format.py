from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DisbursementBankAccount(BaseModel):
    bankName: str = Field(
        ...,
        description="Nome do banco onde o cliente possui conta",
    )
    accountType: str = Field(
        ...,
        description="Tipo de conta bancária. Deve ser 'corrente' para conta corrente ou 'poupanca' para conta poupança",
    )
    accountNumber: str = Field(
        ..., description="Número da conta bancária do cliente, sem o dígito verificador"
    )
    accountDigit: str = Field(
        ..., description="Dígito verificador da conta bancária do cliente"
    )
    branchNumber: str = Field(
        ...,
        description="Número da agência bancária, sem o dígito verificador (se houver)",
    )


def format_prata_response(
    pix_data: Dict[str, Any]
) -> Optional[DisbursementBankAccount]:
    """
    Formata a resposta da API do Banco Prata para a estrutura DisbursementBankAccount.
    :param pix_data: Dicionário contendo a resposta da API do Banco Prata
    :return: Objeto DisbursementBankAccount ou None se os dados forem inválidos
    """
    if "data" in pix_data:
        data = pix_data["data"]
    else:
        data = pix_data
    if not data:
        logger.warning("Dados vazios recebidos para formatação")
        return None
    account_type_map = {"checking": "corrente", "savings": "poupanca"}
    full_account_number = data.get("accountNumber", "")
    account_number = full_account_number[:-1]
    account_digit = full_account_number[-1] if full_account_number else ""
    try:
        formatted_account = DisbursementBankAccount(
            bankName=str(data.get("bankName", "")),
            accountType=account_type_map.get(data.get("accountType", ""), "corrente"),
            accountNumber=account_number,
            accountDigit=account_digit,
            branchNumber=data.get("branchCode", ""),
        )
        return formatted_account
    except ValueError as e:
        logger.error(f"Erro ao formatar dados: {e}")
        return None
