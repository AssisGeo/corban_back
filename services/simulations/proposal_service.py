from typing import Dict, List, Any, Optional, Union
from .banks.base import BankProposal, ProposalResult
from pymongo import MongoClient, DESCENDING
from .adapters.base import BankAdapter
import logging
import os
from math import ceil
from datetime import datetime
from memory import MongoDBMemoryManager
from models.normalized.proposal import NormalizedProposalRequest

logger = logging.getLogger(__name__)


class ProposalService:
    def __init__(self):
        self._proposal_providers: Dict[str, BankProposal] = {}
        self._adapters: Dict[str, BankAdapter] = {}
        self.mongo_client = MongoClient(os.getenv("MONGODB_URL"))
        self.db = self.mongo_client["fgts_agent"]
        self.proposals = self.db["fgts_proposals"]
        self.simulations = self.db["fgts_simulations"]
        self.memory_manager = MongoDBMemoryManager()

    def register_provider(self, provider: BankProposal):
        """Registra um novo provedor de proposta no serviço"""
        self._proposal_providers[provider.bank_name] = provider
        logger.info(f"Provedor de proposta registrado: {provider.bank_name}")

    def register_adapter(self, adapter: BankAdapter):
        """Registra um adaptador de banco"""
        self._adapters[adapter.bank_name] = adapter
        logger.info(f"Adaptador registrado: {adapter.bank_name}")

    async def submit_proposal(
        self,
        proposal_data: Union[NormalizedProposalRequest, Dict[str, Any]],
        bank_name: Optional[str] = None,
    ) -> ProposalResult:
        try:
            # 1. Determinar o banco para envio da proposta
            target_bank = bank_name

            # Extrair o financial_id independentemente do tipo de entrada
            if isinstance(proposal_data, dict):
                financial_id = proposal_data.get("financial_id", "")
            else:
                financial_id = proposal_data.financial_id

            if not target_bank:
                # Se não foi especificado, consulta pelo financialId
                target_bank = self._get_bank_for_financial_id(financial_id)

                if not target_bank:
                    # Padrão para VCTEX se não encontrar
                    target_bank = "VCTEX"
                    logger.warning(
                        f"Banco não identificado para o ID {financial_id}, usando padrão: {target_bank}"
                    )

            # 2. Verificar se o provedor está registrado
            if target_bank not in self._proposal_providers:
                error_msg = f"Provedor não registrado: {target_bank}"
                logger.error(error_msg)
                return ProposalResult(
                    bank_name=target_bank,
                    error_message=error_msg,
                    success=False,
                    raw_response={"error": error_msg},
                )

            # 3. Verificar se existe adaptador para o banco
            if target_bank not in self._adapters:
                error_msg = f"Adaptador não encontrado para banco: {target_bank}"
                logger.error(error_msg)
                return ProposalResult(
                    bank_name=target_bank,
                    error_message=error_msg,
                    success=False,
                    raw_response={"error": error_msg},
                )

            if isinstance(proposal_data, dict):
                try:
                    from models.normalized.proposal import NormalizedProposalRequest

                    normalized_data = NormalizedProposalRequest(**proposal_data)
                except Exception as e:
                    error_msg = (
                        f"Erro ao converter dados para formato normalizado: {str(e)}"
                    )
                    logger.error(error_msg)
                    return ProposalResult(
                        bank_name=target_bank,
                        error_message=error_msg,
                        success=False,
                        raw_response={
                            "error": error_msg,
                            "original_data": proposal_data,
                        },
                    )
            else:
                normalized_data = proposal_data

            # 5. Usar o adaptador para converter para o formato específico do banco
            adapter = self._adapters[target_bank]
            try:
                bank_specific_data = adapter.prepare_proposal_request(normalized_data)
                logger.info(
                    f"Dados convertidos para formato específico do banco {target_bank}"
                )
            except Exception as e:
                error_msg = (
                    f"Erro ao adaptar dados para o banco {target_bank}: {str(e)}"
                )
                logger.error(error_msg)
                return ProposalResult(
                    bank_name=target_bank,
                    error_message=error_msg,
                    success=False,
                    raw_response={"error": error_msg},
                )

            # 6. Enviar a proposta usando o provedor específico
            provider = self._proposal_providers[target_bank]
            result = await provider.submit_proposal(bank_specific_data)

            # 7. Salvar o resultado
            self._save_proposal_result(financial_id, result)

            # 8. Se for bem-sucedido, atualizar a sessão com o número do contrato
            if result.success and result.contract_number:
                # Atualiza por financial_id
                self.memory_manager.set_session_data(
                    financial_id, "contract_number", result.contract_number
                )

                # Salva também os metadados
                metadata = {
                    "proposal_created_at": datetime.utcnow(),
                    "proposal_bank": target_bank,
                    "proposal_sent": True,
                }

                for key, value in metadata.items():
                    self.memory_manager.set_session_data(financial_id, key, value)

                # Define os dados na collection customer_data
                self.memory_manager.set_session_data(
                    financial_id, "customer_data.proposal_sent", True
                )

                self.memory_manager.set_session_data(
                    financial_id,
                    "customer_data.proposal_created_at",
                    datetime.utcnow(),
                )

            return result

        except Exception as e:
            logger.error(f"Erro ao enviar proposta: {str(e)}")
            return ProposalResult(
                bank_name=bank_name or "DESCONHECIDO",
                error_message=str(e),
                success=False,
                raw_response={"error": str(e)},
            )

    async def check_proposal_status(
        self, contract_number: str, bank_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verifica o status de uma proposta existente.

        Args:
            contract_number: Número do contrato
            bank_name: Nome do banco (opcional, se não fornecido tenta descobrir)

        Returns:
            Dict com informações de status
        """
        if not bank_name:
            bank_name = self._get_bank_for_contract(contract_number)

            if not bank_name:
                return {
                    "success": False,
                    "error": f"Banco não encontrado para o contrato {contract_number}",
                    "status": "unknown",
                }

        if bank_name not in self._proposal_providers:
            return {
                "success": False,
                "error": f"Provedor não registrado: {bank_name}",
                "status": "provider_not_found",
            }

        provider = self._proposal_providers[bank_name]
        return await provider.check_status(contract_number)

    def _get_bank_for_financial_id(self, financial_id: str) -> Optional[str]:
        """
        Determina qual banco usar baseado no financial_id.

        Regras:
        - Se começar com "facta_", usa Facta
        - Se começar com "bmg_", usa BMG
        - Caso contrário, consulta no histórico de simulações
        """
        if financial_id.startswith("facta_"):
            return "FACTA"

        if financial_id.startswith("bmg_"):
            return "BMG"

        # Consulta na collection de simulações
        simulation = self.db["fgts_simulations"].find_one(
            {"financial_id": financial_id}
        )

        if simulation:
            return simulation.get("bank_provider") or simulation.get("bank_name")

        # Consulta na memória da sessão
        from memory import MongoDBMemoryManager

        memory_manager = MongoDBMemoryManager()
        bank_provider = memory_manager.get_session_data(financial_id, "bank_provider")

        return bank_provider

    def _get_bank_for_contract(self, contract_number: str) -> Optional[str]:
        """Determina o banco para um número de contrato"""
        proposal = self.proposals.find_one({"contract_number": contract_number})

        if proposal:
            return proposal.get("bank_name")

        return None

    def _save_proposal_result(self, financial_id: str, result: ProposalResult):
        """Salva o resultado da proposta no MongoDB"""
        try:
            proposal_doc = {
                "financial_id": financial_id,
                "bank_name": result.bank_name,
                "contract_number": result.contract_number,
                "formalization_link": result.formalization_link,
                "error_message": result.error_message,
                "success": result.success,
                "timestamp": result.timestamp,
                "raw_response": result.raw_response,
            }

            # Insere ou atualiza o documento
            self.proposals.update_one(
                {"financial_id": financial_id}, {"$set": proposal_doc}, upsert=True
            )

            logger.info(
                f"Proposta salva para {financial_id} com banco {result.bank_name}"
            )

        except Exception as e:
            logger.error(f"Erro ao salvar proposta: {str(e)}")

    def get_proposal_history(
        self, financial_id: Optional[str] = None, contract_number: Optional[str] = None
    ) -> List[Dict]:
        """
        Recupera histórico de propostas por financial_id ou contract_number.
        Pelo menos um dos parâmetros deve ser fornecido.
        """
        if not financial_id and not contract_number:
            return []

        query = {}
        if financial_id:
            query["financial_id"] = financial_id
        if contract_number:
            query["contract_number"] = contract_number

        return list(
            self.proposals.find(
                query,
                {
                    "_id": 0,
                    "financial_id": 1,
                    "bank_name": 1,
                    "contract_number": 1,
                    "formalization_link": 1,
                    "success": 1,
                    "error_message": 1,
                    "timestamp": 1,
                },
            ).sort("timestamp", DESCENDING)
        )

    def get_all_proposals(
        self,
        page: int = 1,
        per_page: int = 10,
        bank_name: Optional[str] = None,
        success: Optional[bool] = None,
    ) -> Dict:
        """Recupera todas as propostas com paginação e filtros"""
        query = {}
        if bank_name:
            query["bank_name"] = bank_name
        if success is not None:
            query["success"] = success

        # Calcula o total de documentos e páginas
        total_docs = self.proposals.count_documents(query)
        total_pages = ceil(total_docs / per_page)

        # Aplica paginação
        skip = (page - 1) * per_page
        cursor = (
            self.proposals.find(
                query,
                {
                    "_id": 0,
                    "financial_id": 1,
                    "bank_name": 1,
                    "contract_number": 1,
                    "formalization_link": 1,
                    "success": 1,
                    "error_message": 1,
                    "timestamp": 1,
                },
            )
            .sort("timestamp", DESCENDING)
            .skip(skip)
            .limit(per_page)
        )

        return {
            "items": list(cursor),
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_items": total_docs,
        }

    def list_providers(self) -> List[str]:
        """Lista todos os provedores de proposta disponíveis"""
        return list(self._proposal_providers.keys())
