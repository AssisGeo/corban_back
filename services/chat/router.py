from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict, Any
from datetime import datetime
from .service import ChatService
from .schemas import (
    ChatResponse,
    ChatStatsResponse,
    ContractDetailsResponse,
)
from memory import MongoDBMemoryManager
import logging

router = APIRouter(prefix="/api/v1/chats", tags=["chats"])
logger = logging.getLogger(__name__)


async def get_chat_service():
    memory_manager = MongoDBMemoryManager()
    return ChatService(memory_manager)


@router.get("/stats", response_model=ChatStatsResponse)
async def get_chat_stats(service: ChatService = Depends(get_chat_service)):
    """Retorna estatísticas gerais dos chats"""
    try:
        return await service.get_chat_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline", response_model=Dict[str, Any])
async def get_pipeline_data(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    cpf: Optional[str] = Query(default=None),
    service: ChatService = Depends(get_chat_service),
):
    """Lista todas as propostas enviadas com seus detalhes."""
    try:
        pipeline_data = await service.get_pipeline_data(page, per_page, cpf_search=cpf)
        return pipeline_data
    except Exception as e:
        logger.error(f"Erro ao obter dados da pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/details", response_model=ContractDetailsResponse)
async def get_chat_contract_details(
    session_id: str, service: ChatService = Depends(get_chat_service)
):
    """Retorna detalhes completos do contrato/proposta para um chat específico"""
    try:
        return await service.get_contract_details(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/messages")
async def get_message_metrics(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    service: ChatService = Depends(get_chat_service),
):
    """Retorna métricas de mensagens com paginação"""
    try:
        return await service.get_messages_metrics(page, per_page)
    except Exception as e:
        logger.error(f"Erro ao obter métricas de mensagens: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/messages-by-hour")
async def get_messages_by_hour(
    start_date: datetime = None,
    end_date: datetime = None,
    service: ChatService = Depends(get_chat_service),
):
    return await service.get_messages_by_hour(start_date, end_date)


@router.get("/", response_model=Dict[str, Any])
async def list_chats(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    service: ChatService = Depends(get_chat_service),
):
    """Lista todos os chats com paginação e busca opcional"""
    try:
        return await service.list_chats(page=page, per_page=per_page, search=search)
    except Exception as e:
        logger.error(f"Erro ao listar chats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=ChatResponse)
async def get_chat(session_id: str, service: ChatService = Depends(get_chat_service)):
    """Retorna detalhes de um chat específico"""
    try:
        return await service.get_chat(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/conversation", response_model=ChatResponse)
async def get_chat_conversation(
    session_id: str, service: ChatService = Depends(get_chat_service)
):
    """Retorna o histórico de mensagens de um chat"""
    try:
        return await service.get_chat_conversation(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
