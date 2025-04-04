from .base import BankProposal, ProposalResult
from models.vctex.models import SendProposalInput
from typing import Dict, Any
import logging
from apis.vctex_api_client import VCTEXAPIClient
import time

logger = logging.getLogger(__name__)


class VCTEXBankProposal(BankProposal):
    def __init__(self):
        self.client = VCTEXAPIClient()

    @property
    def bank_name(self) -> str:
        return "VCTEX"

    async def submit_proposal(self, proposal_data: SendProposalInput) -> ProposalResult:
        try:
            # print(proposal_data)
            if hasattr(proposal_data, "model_dump"):
                proposal_dict = proposal_data.model_dump()
            else:
                proposal_dict = proposal_data
            print(proposal_data["borrower"])
            if "borrower" in proposal_dict and "cpf" in proposal_dict["borrower"]:
                normalized_cpf = (
                    proposal_dict["borrower"]["cpf"].replace(".", "").replace("-", "")
                )
                proposal_dict["borrower"]["cpf"] = normalized_cpf
                proposal_dict["borrower"]["nationality"] = "brazilian"

            proposal_dict["feeScheduleId"] = 0
            proposal_dict["borrower"]["maritalStatus"] = "single"
            proposal_dict["borrower"]["pep"] = False

            result = await self.client.create_proposal(proposal_dict)

            if isinstance(result, dict) and result.get("statusCode", 0) >= 400:
                return ProposalResult(
                    bank_name=self.bank_name,
                    error_message=result.get("message", "Erro ao criar proposta"),
                    success=False,
                    raw_response=result,
                )

            contract_number = result.get("contract_number", "")
            status_result = await self.check_status(contract_number)

            return ProposalResult(
                bank_name=self.bank_name,
                contract_number=contract_number,
                formalization_link=status_result.get("formalization_link"),
                success=True,
                raw_response=result,
            )

        except Exception as e:
            logger.error(f"Erro na proposta VCTEX: {str(e)}")
            # Adicione mais detalhes de depuração
            logger.error(f"Dados da proposta: {proposal_data}")
            return ProposalResult(
                bank_name=self.bank_name,
                error_message=str(e),
                success=False,
                raw_response={"error": str(e)},
            )

    async def check_status(self, contract_number: str) -> Dict[str, Any]:
        try:
            formatted_contract_number = contract_number.replace("/", "-")
            time.sleep(10)
            status_response = await self.client.proposal_status(
                formatted_contract_number
            )
            if isinstance(status_response, dict) and "status" in status_response:
                return {
                    "success": True,
                    "formalization_link": status_response.get("status", ""),
                    "status": (
                        "pending" if status_response.get("status") else "not_found"
                    ),
                }

            return {
                "success": False,
                "error": status_response.get("error", "Status não disponível"),
                "status": "error",
            }

        except Exception as e:
            logger.error(f"Erro ao verificar status VCTEX: {str(e)}")
            return {"success": False, "error": str(e), "status": "error"}
