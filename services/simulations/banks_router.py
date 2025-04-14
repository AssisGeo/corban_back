from fastapi import APIRouter, Depends
from typing import Dict, Any
from .services import SimulationService
from .banks.qi_bank import QIBankSimulator
from .banks.vctex_bank import VCTEXBankSimulator
from .banks.facta_bank import FactaBankSimulator
from services.bank_config.service import BankConfigService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["banks"])


def get_simulation_service() -> SimulationService:
    service = SimulationService()

    all_banks = {
        "QI": QIBankSimulator(),
        "VCTEX": VCTEXBankSimulator(),
        "FACTA": FactaBankSimulator(),
    }

    # Consultar quais bancos estão ativos
    active_banks = BankConfigService.get_active_banks_static(feature="simulation")

    # Registrar apenas os bancos ativos
    for bank_name, bank in all_banks.items():
        if bank_name in active_banks:
            service.register_bank(bank)
        else:
            logger.info(f"Banco {bank_name} não está ativo, não será registrado")

    return service


@router.get("/banks", response_model=Dict[str, Any])
async def list_banks(service: SimulationService = Depends(get_simulation_service)):
    """Lista todos os bancos disponíveis para simulação"""
    return service.list_banks()
