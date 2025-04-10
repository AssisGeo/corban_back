from typing import Dict, List, Any, Optional
from pymongo import MongoClient, DESCENDING
from datetime import datetime
import logging
import os
import math
from .services import SimulationService
from .banks.vctex_bank import VCTEXBankSimulator
from .banks.facta_bank import FactaBankSimulator

logger = logging.getLogger(__name__)


class BatchSimulationService:
    def __init__(self):
        self.mongo_url = os.getenv("MONGODB_URL")
        self.client = MongoClient(self.mongo_url)
        self.db = self.client["fgts_agent"]
        self.batch_results = self.db["batch_simulations"]

        self.simulation_service = SimulationService()
        self.simulation_service.register_bank(VCTEXBankSimulator())
        self.simulation_service.register_bank(FactaBankSimulator())

    def list_collections(self) -> List[str]:
        """Lista todas as coleções disponíveis no banco de dados"""
        return self.db.list_collection_names()

    async def process_batch_simulations(
        self,
        bank_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Processa simulações em lote para propostas na esteira

        Args:
            bank_name: Nome do banco específico para simulação ou None para todos
            collection_name: Nome da coleção a consultar

        Returns:
            Dict com resultados do processamento
        """
        try:
            collection = self.db["sessions"]

            query = {
                "$or": [
                    {"customer_data.customer_info.cpf": {"$exists": True, "$ne": None}},
                    {"customer_data.borrower.cpf": {"$exists": True, "$ne": None}},
                    {"cpf": {"$exists": True, "$ne": None}},
                    {"customer_data.cpf": {"$exists": True, "$ne": None}},
                    {"personal_info.cpf": {"$exists": True, "$ne": None}},
                    {"document.cpf": {"$exists": True, "$ne": None}},
                    {"user.cpf": {"$exists": True, "$ne": None}},
                ]
            }

            total_propostas = collection.count_documents(query)
            logger.info(
                f"Total de propostas encontradas com CPF na coleção {"sessions"}: {total_propostas}"
            )

            pipeline_items = list(collection.find(query))

            logger.info(f"Quantidade de propostas a processar: {len(pipeline_items)}")

            results = []
            success_count = 0
            error_count = 0
            processed_cpfs = set()

            for item in pipeline_items:
                try:
                    cpf = None

                    possible_paths = [
                        item.get("customer_data", {})
                        .get("customer_info", {})
                        .get("cpf"),
                        item.get("customer_data", {}).get("borrower", {}).get("cpf"),
                        item.get("cpf"),
                        item.get("customer_data", {}).get("cpf"),
                        item.get("personal_info", {}).get("cpf"),
                        item.get("document", {}).get("cpf"),
                        item.get("user", {}).get("cpf"),
                    ]

                    for path in possible_paths:
                        if path and isinstance(path, str) and len(path) >= 11:
                            cpf = path
                            break

                    session_id = item.get("session_id", str(item.get("_id")))

                    if not cpf:
                        logger.warning(f"Proposta sem CPF válido: {session_id}")
                        error_count += 1
                        results.append(
                            {
                                "session_id": session_id,
                                "cpf": None,
                                "success": False,
                                "error": "CPF não encontrado na proposta",
                            }
                        )
                        continue

                    normalized_cpf = cpf.replace(".", "").replace("-", "")

                    if normalized_cpf in processed_cpfs:
                        logger.info(
                            f"CPF {normalized_cpf} já processado neste batch, pulando..."
                        )
                        continue

                    processed_cpfs.add(normalized_cpf)

                    logger.info(
                        f"Processando simulação para CPF: {normalized_cpf}, Sessão: {session_id}"
                    )

                    simulation_results = await self.simulation_service.simulate(
                        normalized_cpf, bank_name
                    )

                    logger.info(
                        f"Resultado da simulação para CPF {normalized_cpf}: {len(simulation_results)} bancos processados"
                    )

                    bank_results = []
                    has_success = False

                    for result in simulation_results:
                        result_success = (
                            result.available_amount > 0
                            and result.financial_id is not None
                            and result.financial_id != ""
                        )

                        bank_result = {
                            "bank": result.bank_name,
                            "financial_id": result.financial_id or "",
                            "amount": result.available_amount or 0,
                            "success": result_success,
                        }

                        if not result_success:
                            if isinstance(result.raw_response, dict):
                                if "message" in result.raw_response:
                                    bank_result["error"] = result.raw_response.get(
                                        "message"
                                    )
                                elif "error" in result.raw_response:
                                    bank_result["error"] = result.raw_response.get(
                                        "error"
                                    )
                                elif "mensagem" in result.raw_response:
                                    bank_result["error"] = result.raw_response.get(
                                        "mensagem"
                                    )

                        if result_success:
                            has_success = True

                        bank_results.append(bank_result)

                    simulation_record = {
                        "cpf": normalized_cpf,
                        "session_id": session_id,
                        "timestamp": datetime.utcnow(),
                        "results": bank_results,
                        "any_success": has_success,
                    }

                    existing_record = self.batch_results.find_one(
                        {"cpf": normalized_cpf}
                    )

                    if existing_record:
                        self.batch_results.update_one(
                            {"cpf": normalized_cpf},
                            {
                                "$set": {
                                    "last_updated": datetime.utcnow(),
                                    "results": bank_results,
                                    "any_success": has_success,
                                },
                                "$push": {
                                    "simulations": {
                                        "timestamp": datetime.utcnow(),
                                        "results": bank_results,
                                        "any_success": has_success,
                                    }
                                },
                            },
                        )
                        logger.info(
                            f"Atualizado registro existente para CPF {normalized_cpf}"
                        )
                    else:
                        self.batch_results.insert_one(
                            {
                                "cpf": normalized_cpf,
                                "session_id": session_id,
                                "created_at": datetime.utcnow(),
                                "last_updated": datetime.utcnow(),
                                "results": bank_results,
                                "any_success": has_success,
                            }
                        )
                        logger.info(f"Criado novo registro para CPF {normalized_cpf}")

                    if has_success:
                        success_count += 1
                    else:
                        error_count += 1

                    results.append(
                        {
                            "cpf": normalized_cpf,
                            "session_id": session_id,
                            "success": has_success,
                            "banks": [r["bank"] for r in bank_results],
                            "success_banks": [
                                r["bank"] for r in bank_results if r["success"]
                            ],
                        }
                    )

                except Exception as e:
                    logger.error(f"Erro ao processar proposta: {str(e)}")
                    error_count += 1
                    results.append(
                        {
                            "session_id": item.get("session_id", str(item.get("_id"))),
                            "cpf": cpf if "cpf" in locals() else None,
                            "success": False,
                            "error": str(e),
                        }
                    )

            return {
                "processed_count": len(processed_cpfs),
                "success_count": success_count,
                "error_count": error_count,
                "results": results,
            }

        except Exception as e:
            logger.error(f"Erro geral no processamento em lote: {str(e)}")
            raise

    async def get_batch_results(
        self,
        page: int = 1,
        per_page: int = 20,
        cpf: Optional[str] = None,
        bank_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retorna os resultados das simulações em lote com paginação e filtros
        """
        try:
            query = {}

            if cpf:
                normalized_cpf = cpf.replace(".", "").replace("-", "")
                query["cpf"] = normalized_cpf

            if bank_name:
                query["results.bank"] = bank_name

            total = self.batch_results.count_documents(query)
            total_pages = math.ceil(total / per_page) if total > 0 else 1

            skip = (page - 1) * per_page
            cursor = (
                self.batch_results.find(
                    query,
                    {
                        "_id": 0,
                        "cpf": 1,
                        "customer_name": 1,
                        "session_id": 1,
                        "last_updated": 1,
                        "results": 1,
                        "any_success": 1,
                        "simulations": {"$slice": -1},
                    },
                )
                .sort("last_updated", DESCENDING)
                .skip(skip)
                .limit(per_page)
            )

            return {
                "items": list(cursor),
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "total_items": total,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            }

        except Exception as e:
            logger.error(f"Erro ao obter resultados de simulações em lote: {str(e)}")
            raise
