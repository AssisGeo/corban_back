from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict
from .services import SimulationService
from .banks.qi_bank import QIBankSimulator
from .banks.vctex_bank import VCTEXBankSimulator
from .banks.facta_bank import FactaBankSimulator
from pydantic import BaseModel
from datetime import datetime
from models.normalized.simulation import NormalizedSimulationResponse
import logging

logger = logging.getLogger(__name__)


class SimulationHistoryItem(BaseModel):
    cpf: str
    bank_name: str
    available_amount: Optional[float]
    error_message: Optional[str]
    success: bool
    timestamp: datetime


router = APIRouter(prefix="/api/v1/simulation", tags=["simulation"])


def get_simulation_service() -> SimulationService:
    service = SimulationService()

    # Criar todos os bancos disponíveis
    all_banks = {
        "QI": QIBankSimulator(),
        "VCTEX": VCTEXBankSimulator(),
        "FACTA": FactaBankSimulator(),
    }

    active_banks = service.get_active_banks(feature="simulation")

    for bank_name, bank in all_banks.items():
        if bank_name in active_banks:
            service.register_bank(bank)
        else:
            logger.info(f"Banco {bank_name} não está ativo, não será registrado")

    return service


@router.post("/{cpf}", response_model=List[NormalizedSimulationResponse])
async def simulate_fgts(
    cpf: str,
    bank: str | None = Query(
        None, description="Nome do banco específico ou None para todos"
    ),
    service: SimulationService = Depends(get_simulation_service),
):
    """Simula FGTS em um ou todos os bancos disponíveis com resposta normalizada"""
    try:
        cpf = cpf.replace(".", "").replace("-", "")
        return await service.simulate(cpf, bank)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{cpf}/history")
async def get_simulation_history(
    cpf: str,
    bank: str | None = Query(None, description="Filtrar por banco específico"),
    service: SimulationService = Depends(get_simulation_service),
):
    """Retorna histórico de simulações para um CPF específico"""
    return service.get_simulation_history(cpf, bank)


@router.get("/history/all", response_model=Dict)
async def get_all_simulations(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(10, ge=1, le=50, description="Itens por página"),
    bank: str | None = Query(None, description="Filtrar por banco específico"),
    cpf: str | None = Query(None, description="Filtrar por CPF específico"),
    service: SimulationService = Depends(get_simulation_service),
):
    """Retorna histórico de todas as simulações com paginação"""
    return service.get_all_simulations(page, per_page, bank, cpf)


@router.get("/cpfs", response_model=List[str])
async def get_unique_cpfs(
    service: SimulationService = Depends(get_simulation_service),
):
    """Retorna lista de CPFs únicos que têm simulações"""
    return service.get_unique_cpfs()
