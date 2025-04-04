from typing import Dict, Any
import logging
from apis.cep_api_client import CepAPIClient
from apis.prata_apli_client import PrataApi
from memory import MongoDBMemoryManager
from .schemas import SimulationRequest
from services.simulations.proposal_service import ProposalService
from services.simulations.banks.vctex_proposal import VCTEXBankProposal
from services.simulations.banks.facta_proposal import FactaBankProposal
from models.vctex.models import SendProposalInput

logger = logging.getLogger(__name__)


class VCTEXService:

    def __init__(self):
        self.cep_client = CepAPIClient()
        self.prata_client = PrataApi()
        self.memory_manager = MongoDBMemoryManager()

        # Inicializa o serviço de propostas
        self.proposal_service = ProposalService()
        self.proposal_service.register_provider(VCTEXBankProposal())
        self.proposal_service.register_provider(FactaBankProposal())

    async def simulate_credit(
        self, simulation_data: SimulationRequest
    ) -> Dict[str, Any]:
        # Código existente para simulação
        pass

    async def create_proposal(self, proposal_data: SendProposalInput) -> Dict[str, Any]:
        """
        Cria proposta usando o novo serviço de propostas.
        """
        try:
            # 1. Identificar o banco baseado no financialId
            financial_id = proposal_data.financialId

            # 2. Chamada ao novo serviço centralizado de propostas
            result = await self.proposal_service.submit_proposal(proposal_data)

            # 3. Retornar resultado formatado
            if not result.success:
                return {"message": result.error_message, "statusCode": 400}

            # 4. Armazenar dados da proposta
            self.memory_manager.store_proposal_data(
                financial_id,
                {
                    "contract_number": result.contract_number,
                    "bank_provider": result.bank_name,
                    "proposal_success": True,
                    "proposal_timestamp": result.timestamp.isoformat(),
                },
            )

            return {
                "contract_number": result.contract_number,
                "status": "success",
                "bank": result.bank_name,
            }

        except Exception as e:
            logger.error("Erro ao criar proposta: {}".format(str(e)))
            return {"message": str(e), "statusCode": 500}

    async def get_proposal_status(self, contract_number: str) -> Dict[str, Any]:
        """
        Consulta status atual da proposta usando o novo serviço
        """
        try:
            # Usa o novo serviço que escolherá o provedor certo automaticamente
            return await self.proposal_service.check_proposal_status(contract_number)
        except Exception as e:
            logger.error("Erro ao consultar status: {}".format(str(e)))
            return {"error": str(e)}
