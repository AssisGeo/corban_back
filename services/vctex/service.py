from typing import Dict, Any
import logging
from apis.vctex_api_client import VCTEXAPIClient
from apis.cep_api_client import CepAPIClient
from apis.prata_apli_client import PrataApi
from memory import MongoDBMemoryManager
from .schemas import SimulationRequest, ProposalRequest

logger = logging.getLogger(__name__)


class VCTEXService:

    def __init__(self):
        self.vctex_client = VCTEXAPIClient()
        self.cep_client = CepAPIClient()
        self.prata_client = PrataApi()
        self.memory_manager = MongoDBMemoryManager()

    async def simulate_credit(
        self, simulation_data: SimulationRequest
    ) -> Dict[str, Any]:
        try:
            payload = {
                "clientCpf": simulation_data.cpf.replace(".", "").replace("-", ""),
                "feeScheduleId": simulation_data.fee_schedule_id,
            }

            result = await self.vctex_client.simulate_credit(payload)

            if isinstance(result, dict) and result.get("statusCode", 0) >= 400:
                raise ValueError(result.get("message", "Erro na simulação"))

            if financial_id := result.get("financialId"):
                self.memory_manager.store_simulation_data(financial_id, result)
                self.memory_manager.set_session_data(
                    financial_id, "financial_id", financial_id
                )

            return result

        except Exception as e:
            logger.error(f"Erro ao simular crédito: {str(e)}")
            raise

    async def create_proposal(self, proposal_data: ProposalRequest) -> Dict[str, Any]:
        """
        Cria proposta de crédito FGTS com os dados fornecidos e salva no banco de dados.
        Se a sessão não existir, cria uma nova.
        """
        try:
            session_id = proposal_data.financialId

            borrower = proposal_data.borrower

            customer_data = {
                "customer_info": {
                    "name": borrower.name,
                    "cpf": borrower.cpf,
                    "mother_name": borrower.motherName,
                    "gender": borrower.gender,
                    "birth_date": borrower.birthdate,
                    "address_number": proposal_data.address.number,
                    "zip_code": proposal_data.address.zipCode,
                    "phone": {
                        "ddd": str(borrower.phoneNumber)[:2],
                        "number": str(borrower.phoneNumber)[2:],
                    },
                    "email": borrower.email,
                }
            }

            # Armazenar os dados do cliente na sessão
            self.memory_manager.set_session_data(
                session_id, "customer_data", customer_data
            )

            payload = {
                "feeScheduleId": 0,
                "financialId": proposal_data.financialId,
                "borrower": {
                    **borrower.__dict__,
                    "nationality": "brasileiro",
                    "pep": False,
                },
                "document": proposal_data.document.dict(),
                "address": proposal_data.address.dict(),
                "disbursementBankAccount": (
                    proposal_data.disbursementBankAccount.dict()
                    if proposal_data.disbursementBankAccount
                    else None
                ),
            }

            result = await self.vctex_client.create_proposal(payload)

            if isinstance(result, dict) and result.get("statusCode", 0) >= 400:
                raise ValueError(result.get("message", "Erro ao criar proposta"))

            if result.get("contract_number"):
                self.memory_manager.set_session_data(
                    session_id, "contract_number", result["contract_number"]
                )

            return result

        except Exception as e:
            logger.error("Erro ao criar proposta: {}".format(str(e)))
            raise

    async def get_proposal_status(self, contract_number: str) -> Dict[str, Any]:
        """
        Consulta status atual da proposta
        """
        try:
            return await self.vctex_client.proposal_status(contract_number)
        except Exception as e:
            logger.error("Erro ao consultar status: {}".format(str(e)))
            raise
