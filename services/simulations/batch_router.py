from fastapi import APIRouter, Depends, Query
from typing import Dict, Any, Optional
from .batch_service import BatchSimulationService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/simulations/batch", tags=["batch-simulation"])


def get_batch_service():
    return BatchSimulationService()


@router.post("/run", response_model=Dict[str, Any])
async def run_batch_simulations(
    bank_name: Optional[str] = Query(
        None, description="Nome do banco específico ou todos"
    ),
    service: BatchSimulationService = Depends(get_batch_service),
):
    """
    Executa simulações em lote para propostas da esteira e armazena os resultados
    em uma tabela auxiliar específica de forma simplificada
    """
    try:
        result = await service.process_batch_simulations(bank_name)
        return {
            "success": True,
            "processed_count": result["processed_count"],
            "success_count": result["success_count"],
            "error_count": result["error_count"],
            "results": result["results"],
        }
    except Exception as e:
        logger.error(f"Erro ao processar simulações em lote: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/results", response_model=Dict[str, Any])
async def get_batch_simulation_results(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Itens por página"),
    cpf: Optional[str] = Query(None, description="Filtrar por CPF"),
    bank_name: Optional[str] = Query(None, description="Filtrar por banco"),
    service: BatchSimulationService = Depends(get_batch_service),
):
    """
    Retorna resultados das simulações em lote com paginação e filtros
    """
    try:
        results = await service.get_batch_results(page, per_page, cpf, bank_name)
        return results
    except Exception as e:
        logger.error(f"Erro ao buscar resultados de simulações em lote: {str(e)}")
        return {"success": False, "error": str(e)}
