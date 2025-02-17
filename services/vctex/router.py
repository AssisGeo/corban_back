from fastapi import APIRouter, HTTPException, Depends, Request
from .service import VCTEXService
from .schemas import SimulationRequest, ProposalRequest, ContractRequest
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

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
        logger.info(f"Recebendo requisição de simulação: {simulation_data.dict()}")
        return await service.simulate_credit(simulation_data)
    except Exception as e:
        logger.error(f"Erro na simulação: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proposal", response_model=Dict[str, Any])
async def create_proposal(
    request: Request,
    proposal_data: ProposalRequest,
    service: VCTEXService = Depends(get_vctex_service),
):
    """Cria proposta manual de FGTS"""
    try:
        body = await request.body()
        logger.info(f"Recebendo requisição de proposta. Body: {body.decode()}")

        logger.info(f"Dados validados: {proposal_data.dict()}")

        response = await service.create_proposal(proposal_data)
        return response
    except ValueError as e:
        logger.error(f"Erro de validação: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao criar proposta: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proposal/link", response_model=Dict[str, Any])
async def get_proposal_status(
    contract_request: ContractRequest,
    service: VCTEXService = Depends(get_vctex_service),
):
    """Consulta status de uma proposta"""
    try:
        formatted_contract_number = contract_request.contract_number.replace("/", "-")
        return await service.get_proposal_status(formatted_contract_number)
    except Exception as e:
        logger.error(f"Erro ao consultar status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
