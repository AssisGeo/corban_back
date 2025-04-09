from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from .card_service import (
    CardService,
    ThirdStepRequest,
)
from .schemas import CardProposalResponse, CardListResponse

router = APIRouter(prefix="/api/v1/cards", tags=["cards"])


def get_card_service():
    return CardService()


@router.get("/", response_model=CardListResponse)
async def list_cards(
    page: int = 1,
    per_page: int = 20,
    cpf: str = None,
    service: CardService = Depends(get_card_service),
):
    """Lista todas as propostas de cartão com paginação e filtros"""
    return await service.list_cards(page, per_page, cpf)


@router.post("/proposal", response_model=CardProposalResponse)
async def create_card_proposal(
    proposal_data: ThirdStepRequest, service: CardService = Depends(get_card_service)
):
    """Cria uma proposta de cartão completa"""
    return await service.create_full_proposal(proposal_data)


@router.get("/{proposal_number}", response_model=Dict[str, Any])
async def get_card_details(
    proposal_number: str, service: CardService = Depends(get_card_service)
):
    """Obtém detalhes completos de um cartão pelo número da proposta."""
    card_details = await service.get_card_details(proposal_number)

    if not card_details:
        raise HTTPException(
            status_code=404,
            detail=f"Cartão com proposta {proposal_number} não encontrado",
        )

    return card_details
