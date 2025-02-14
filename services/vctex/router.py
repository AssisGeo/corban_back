from fastapi import APIRouter, HTTPException, Depends
from .service import VCTEXService
from .schemas import SimulationRequest, ProposalRequest, ContractRequest
from typing import Dict, Any

router = APIRouter(prefix="/api/v1/vctex", tags=["vctex"])


async def get_vctex_service():
    return VCTEXService()


@router.post("/simulation", response_model=Dict[str, Any])
async def simulate_fgts(
    simulation_data: SimulationRequest,
    service: VCTEXService = Depends(get_vctex_service),
):
    """Realiza simulação manual de FGTS"""
    try:
        return await service.simulate_credit(simulation_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proposal", response_model=Dict[str, Any])
async def create_proposal(
    proposal_data: ProposalRequest, service: VCTEXService = Depends(get_vctex_service)
):
    """Cria proposta manual de FGTS"""
    try:
        response = service.create_proposal(proposal_data)
        return await response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proposal/link", response_model=Dict[str, Any])
async def get_proposal_status(
    contract_request: ContractRequest,  # Usando o modelo aqui
    service: VCTEXService = Depends(get_vctex_service),
):
    """Consulta status de uma proposta"""
    try:
        formatted_contract_number = contract_request.contract_number.replace("/", "-")

        return await service.get_proposal_status(formatted_contract_number)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
