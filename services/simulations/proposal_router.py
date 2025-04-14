from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional, List
from .proposal_service import ProposalService
from .banks.vctex_proposal import VCTEXBankProposal
from .banks.facta_proposal import FactaBankProposal
from models.normalized.proposal import NormalizedProposalRequest
from .adapters.vctex_adapter import VCTEXBankAdapter
from .adapters.facta_adapter import FactaBankAdapter
import logging

# from .adapters.qi_adapter import QIBankAdapter


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/proposals", tags=["proposals"])


def get_proposal_service() -> ProposalService:
    """Dependency que configura e retorna o serviço de propostas"""
    service = ProposalService()

    # service.register_adapter(QIBankAdapter())
    service.register_adapter(VCTEXBankAdapter())
    service.register_adapter(FactaBankAdapter())

    all_providers = {
        "VCTEX": VCTEXBankProposal(),
        "FACTA": FactaBankProposal(),
    }

    # Consultar quais provedores estão ativos
    active_providers = service.get_active_banks(feature="proposal")

    # Registrar apenas os provedores ativos
    for provider_name, provider in all_providers.items():
        if provider_name in active_providers:
            service.register_provider(provider)
        else:
            logger.info(f"Provedor {provider_name} não está ativo, não será registrado")

    return service


@router.post("", response_model=Dict[str, Any])
async def create_proposal(
    proposal_data: NormalizedProposalRequest,
    bank_name: Optional[str] = Query(
        None, description="Nome do banco para envio da proposta"
    ),
    service: ProposalService = Depends(get_proposal_service),
):
    """
    Cria uma proposta de FGTS com um banco específico ou usando o melhor banco
    identificado pelo financialId - usando um formato de dados normalizado
    """
    try:
        logger.info(
            f"Recebendo requisição de proposta para banco: {bank_name or 'auto'}"
        )
        result = await service.submit_proposal(proposal_data, bank_name)

        if not result.success:
            logger.error(f"Erro na proposta: {result.error_message}")
            return {
                "success": False,
                "error": result.error_message,
                "bank_name": result.bank_name,
            }

        return {
            "success": True,
            "bank_name": result.bank_name,
            "contract_number": result.contract_number,
            "formalization_link": result.formalization_link or "",
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        logger.error(f"Erro ao criar proposta: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{contract_number}", response_model=Dict[str, Any])
async def check_proposal_status(
    contract_number: str,
    bank_name: Optional[str] = Query(None, description="Nome do banco (opcional)"),
    service: ProposalService = Depends(get_proposal_service),
):
    """Verifica o status de uma proposta pelo número do contrato"""
    try:
        result = await service.check_proposal_status(contract_number, bank_name)
        return result
    except Exception as e:
        logger.error(f"Erro ao verificar status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_proposal_history(
    financial_id: Optional[str] = Query(None, description="ID financeiro da simulação"),
    contract_number: Optional[str] = Query(None, description="Número do contrato"),
    service: ProposalService = Depends(get_proposal_service),
):
    """Obtém histórico de propostas por financialId ou número do contrato"""
    if not financial_id and not contract_number:
        raise HTTPException(
            status_code=400,
            detail="Pelo menos um dos parâmetros (financial_id ou contract_number) deve ser fornecido",
        )

    try:
        return service.get_proposal_history(financial_id, contract_number)
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=Dict[str, Any])
async def list_proposals(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(10, ge=1, le=100, description="Itens por página"),
    bank_name: Optional[str] = Query(None, description="Filtrar por banco"),
    success: Optional[bool] = Query(None, description="Filtrar por sucesso"),
    service: ProposalService = Depends(get_proposal_service),
):
    """Lista todas as propostas com paginação e filtros opcionais"""
    try:
        return service.get_all_proposals(page, per_page, bank_name, success)
    except Exception as e:
        logger.error(f"Erro ao listar propostas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers", response_model=List[str])
async def list_providers(service: ProposalService = Depends(get_proposal_service)):
    """Lista todos os provedores de proposta disponíveis"""
    return service.list_providers()
