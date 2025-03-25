from fastapi import APIRouter, Depends
from .service import EvolutionService
from typing import Dict, Any
from .schemas import MessageRequest

router = APIRouter(prefix="/api/v1/evolution", tags=["evolution"])


async def get_evolution_service():
    return EvolutionService()


@router.get("/conversation/{phone}", response_model=Dict[str, Any])
async def get_conversation(
    phone: str, service: EvolutionService = Depends(get_evolution_service)
):
    """Busca a conversa completa com um contato específico"""
    return await service.get_conversation(phone)


@router.post("/get_conversation", response_model=Dict[str, Any])
async def get_conversations(service: EvolutionService = Depends(get_evolution_service)):
    """Busca a conversa completa com um contato específico"""
    return await service.find_all_chats()


@router.post("/send/{phone}", response_model=Dict[str, Any])
async def send_message(
    phone: str,
    message_data: MessageRequest,
    service: EvolutionService = Depends(get_evolution_service),
):
    """Envia uma mensagem para um contato específico"""
    return await service.send_message_to_user(phone, message_data.message)
