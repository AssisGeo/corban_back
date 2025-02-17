from typing import Dict, List, Any
from .banks.base import BankSimulator, SimulationResult
from pymongo import MongoClient, DESCENDING
import logging
import os
from math import ceil

logger = logging.getLogger(__name__)


class SimulationService:
    def __init__(self):
        self._banks: Dict[str, BankSimulator] = {}
        self.mongo_client = MongoClient(os.getenv("MONGODB_URL"))
        self.db = self.mongo_client["fgts_agent"]
        self.simulations = self.db["fgts_simulations"]

    def register_bank(self, bank: BankSimulator):
        """Registra um novo banco no serviço"""
        self._banks[bank.bank_name] = bank
        logger.info(f"Banco registrado: {bank.bank_name}")

    async def simulate(
        self, cpf: str, bank_name: str | None = None
    ) -> List[SimulationResult]:
        """Realiza simulação em um banco específico ou em todos"""
        results = []

        if bank_name:
            if bank_name not in self._banks:
                raise ValueError(f"Banco não suportado: {bank_name}")
            results.append(await self._banks[bank_name].simulate(cpf))
        else:
            for bank in self._banks.values():
                results.append(await bank.simulate(cpf))

        self._save_results(cpf, results)
        print(results)
        return results

    def _save_results(self, cpf: str, results: List[SimulationResult]):
        """Salva resultados no MongoDB"""
        try:
            for result in results:
                self.simulations.insert_one(
                    {
                        "cpf": cpf,
                        "bank_name": result.bank_name,
                        "available_amount": result.available_amount,
                        "error_message": result.error_message,
                        "success": result.success,
                        "timestamp": result.timestamp,
                    }
                )
        except Exception as e:
            logger.error(f"Erro ao salvar resultados: {str(e)}")

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
