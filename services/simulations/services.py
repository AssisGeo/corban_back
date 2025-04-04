from typing import Dict, List, Any
from .banks.base import BankSimulator, SimulationResult
from .adapters.base import BankAdapter
from .adapters.qi_adapter import QIBankAdapter
from .adapters.vctex_adapter import VCTEXBankAdapter
from .adapters.facta_adapter import FactaBankAdapter
from models.normalized.simulation import NormalizedSimulationResponse
from models.normalized.proposal import NormalizedProposalRequest
from pymongo import MongoClient, DESCENDING
import logging
import os
from math import ceil

logger = logging.getLogger(__name__)


class SimulationService:
    def __init__(self):
        self._banks: Dict[str, BankSimulator] = {}
        self._adapters: Dict[str, BankAdapter] = {}
        self.mongo_client = MongoClient(os.getenv("MONGODB_URL"))
        self.db = self.mongo_client["fgts_agent"]
        self.simulations = self.db["fgts_simulations"]

        # Adaptadores
        self.register_adapter(QIBankAdapter())
        self.register_adapter(VCTEXBankAdapter())
        self.register_adapter(FactaBankAdapter())

    def register_bank(self, bank: BankSimulator):
        """Registra um novo banco no serviço"""
        self._banks[bank.bank_name] = bank
        logger.info(f"Banco registrado: {bank.bank_name}")

    def register_adapter(self, adapter: BankAdapter):
        """Registra um adaptador para um banco"""
        self._adapters[adapter.bank_name] = adapter
        logger.info(f"Adaptador registrado: {adapter.bank_name}")

    async def simulate(
        self, cpf: str, bank_name: str | None = None
    ) -> List[NormalizedSimulationResponse]:
        """Realiza simulação em um banco específico ou em todos e retorna resultados normalizados"""
        raw_results = []
        normalized_results = []

        if bank_name:
            if bank_name not in self._banks:
                raise ValueError(f"Banco não suportado: {bank_name}")
            raw_results.append(await self._banks[bank_name].simulate(cpf))
        else:
            for bank in self._banks.values():
                raw_results.append(await bank.simulate(cpf))

        # Normaliza os resultados usando os adaptadores
        for result in raw_results:
            if result.bank_name in self._adapters and result.success:
                adapter = self._adapters[result.bank_name]
                normalized = adapter.normalize_simulation_response(result.raw_response)
                normalized_results.append(normalized)

                # Salva os resultados normalizados
                self._save_normalized_result(cpf, normalized)
            else:
                # Se não tiver adaptador ou falhar, manter um formato mínimo
                logger.warning(
                    f"Sem adaptador para {result.bank_name} ou simulação falhou"
                )
                normalized_results.append(
                    NormalizedSimulationResponse(
                        bank_name=result.bank_name,
                        financial_id="",
                        available_amount=0,
                        total_amount=0,
                        interest_rate=0,
                        iof_amount=0,
                        error_message=result.error_message,
                        success=result.success,
                        raw_response=result.raw_response,
                    )
                )

        return normalized_results

    def _save_results(self, cpf: str, results: List[SimulationResult]):
        """Salva resultados no MongoDB com informações adicionais"""
        try:
            for result in results:
                print(result)
                simulation_doc = {
                    "cpf": cpf,
                    "bank_name": result.bank_name,
                    "available_amount": result.available_amount,
                    "error_message": result.error_message,
                    "success": result.success,
                    "timestamp": result.timestamp,
                    "financial_id": (
                        result.raw_response.get("financialId")  # VCTEX
                        or result.raw_response.get("data", {}).get("financialId")  # QI
                        or result.raw_response.get("simulacao_fgts")  # FACTA
                        or result.raw_response.get("financial_id")
                    ),
                    "bank_provider": result.bank_name,
                }

                # Insere o documento
                self.simulations.insert_one(simulation_doc)

                if result.raw_response.get("financialId"):
                    self._update_session_with_bank_provider(
                        result.raw_response["financialId"], result.bank_name
                    )

        except Exception as e:
            logger.error(f"Erro ao salvar resultados: {str(e)}")

    def _update_session_with_bank_provider(self, financial_id: str, bank_name: str):
        """
        Atualiza a sessão com o provedor do banco
        """
        from memory import MongoDBMemoryManager

        memory_manager = MongoDBMemoryManager()
        memory_manager.set_session_data(financial_id, "bank_provider", bank_name)
        logger.info(f"Provedor {bank_name} salvo para sessão {financial_id}")

    def get_bank_provider_for_financial_id(self, financial_id: str) -> str:
        """
        Recupera o provedor do banco para um financial_id específico
        """
        simulation = self.simulations.find_one({"financial_id": financial_id})
        if simulation:
            return simulation.get("bank_provider")
        return None

    def get_simulation_history(
        self, cpf: str, bank_name: str | None = None
    ) -> List[Dict]:
        """Recupera histórico de simulações para um CPF"""
        query = {"cpf": cpf}
        if bank_name:
            query["bank_name"] = bank_name
        return list(
            self.simulations.find(
                query,
                {
                    "_id": 0,
                    "cpf": 1,
                    "bank_name": 1,
                    "available_amount": 1,
                    "error_message": 1,
                    "success": 1,
                    "timestamp": 1,
                },
            ).sort("timestamp", DESCENDING)
        )

    def get_all_simulations(
        self,
        page: int = 1,
        per_page: int = 10,
        bank_name: str | None = None,
        cpf: str | None = None,
    ) -> Dict:
        """Recupera todas as simulações com paginação"""
        query = {}
        if bank_name:
            query["bank_name"] = bank_name
        if cpf:
            query["cpf"] = cpf

        # Calcula o total de documentos e páginas
        total_docs = self.simulations.count_documents(query)
        total_pages = ceil(total_docs / per_page)

        # Aplica paginação
        skip = (page - 1) * per_page
        cursor = (
            self.simulations.find(
                query,
                {
                    "_id": 0,
                    "cpf": 1,
                    "bank_name": 1,
                    "available_amount": 1,
                    "error_message": 1,
                    "success": 1,
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

    def list_banks(self) -> Dict[str, Any]:
        """Lista todos os bancos disponíveis"""
        bank_infos = [bank.bank_info for bank in self._banks.values()]
        active_banks = [info for info in bank_infos if info.active]
        inactive_banks = [info for info in bank_infos if not info.active]

        return {
            "active_banks": [bank.dict() for bank in active_banks],
            "inactive_banks": [bank.dict() for bank in inactive_banks],
            "total_active": len(active_banks),
            "system_status": {
                "operational": len(active_banks) > 0,
                "message": (
                    "Sistema operacional"
                    if active_banks
                    else "Nenhum banco disponível no momento"
                ),
            },
        }

    def get_unique_cpfs(self) -> List[str]:
        """Retorna lista de CPFs únicos que têm simulações"""
        return list(self.simulations.distinct("cpf"))

    def _save_normalized_result(self, cpf: str, result: NormalizedSimulationResponse):
        """Salva resultados normalizados no MongoDB"""
        try:
            simulation_doc = {
                "cpf": cpf,
                "bank_name": result.bank_name,
                "available_amount": result.available_amount,
                "total_amount": result.total_amount,
                "interest_rate": result.interest_rate,
                "iof_amount": result.iof_amount,
                "financial_id": result.financial_id,
                "timestamp": result.timestamp,
                "normalized": True,
                "raw_response": result.raw_response,
            }

            self.simulations.insert_one(simulation_doc)

            if result.financial_id:
                self._update_session_with_bank_provider(
                    result.financial_id, result.bank_name
                )

        except Exception as e:
            logger.error(f"Erro ao salvar resultados normalizados: {str(e)}")

    def prepare_proposal_request(
        self, financial_id: str, request_data: NormalizedProposalRequest
    ) -> dict:
        """Prepara o pedido de proposta específico para o banco associado ao financial_id"""
        bank_name = self.get_bank_provider_for_financial_id(financial_id)

        if not bank_name:
            raise ValueError(f"Banco não encontrado para financial_id: {financial_id}")

        if bank_name not in self._adapters:
            raise ValueError(f"Adaptador não encontrado para banco: {bank_name}")

        adapter = self._adapters[bank_name]
        return adapter.prepare_proposal_request(request_data)
