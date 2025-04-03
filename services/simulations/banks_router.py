from fastapi import APIRouter, Depends
from typing import Dict, Any
from .services import SimulationService
from .banks.qi_bank import QIBankSimulator
from .banks.vctex_bank import VCTEXBankSimulator
from .banks.facta_bank import FactaBankSimulator


router = APIRouter(prefix="/api/v1", tags=["banks"])


def get_simulation_service() -> SimulationService:
    service = SimulationService()
    service.register_bank(QIBankSimulator())
    service.register_bank(VCTEXBankSimulator())
    service.register_bank(FactaBankSimulator())

    return service


@router.get("/banks", response_model=Dict[str, Any])
async def list_banks(service: SimulationService = Depends(get_simulation_service)):
    """Lista todos os bancos disponíveis para simulação"""
    return service.list_banks()
