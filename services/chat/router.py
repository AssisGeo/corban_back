# services/chat/router.py
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from .service import ChatService
from .schemas import ChatResponse, ChatStatsResponse
from memory import MongoDBMemoryManager
from typing import Dict, Any
from datetime import datetime

router = APIRouter(prefix="/api/v1/chats", tags=["chats"])


async def get_chat_service():
    memory_manager = MongoDBMemoryManager()
    return ChatService(memory_manager)


@router.get("/pipeline", response_model=Dict[str, Any])
async def get_pipeline_data(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    cpf: Optional[str] = Query(default=None),
    service: ChatService = Depends(get_chat_service),
):
    """Lista todas as propostas enviadas com seus detalhes."""
    try:
        pipeline_data = await service.get_pipeline_data(skip, limit, cpf_search=cpf)
        return pipeline_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ChatStatsResponse)
async def get_chat_stats(service: ChatService = Depends(get_chat_service)):
    """Retorna estatísticas gerais dos chats"""
    try:
        return await service.get_chat_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=Dict[str, Any])
async def list_chats(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    service: ChatService = Depends(get_chat_service),
):
    """Lista todos os chats com paginação e busca opcional"""
    try:
        skip = (page - 1) * per_page
        return await service.list_chats(skip, per_page, search)
    except Exception as e:
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


@router.get("/{session_id}/conversation")
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


@router.get("/metrics/messages-by-hour")
async def get_messages_by_hour(
    start_date: datetime = None,
    end_date: datetime = None,
    service: ChatService = Depends(get_chat_service),
):
    return await service.get_messages_by_hour(start_date, end_date)


@router.get("/metrics/messages")
async def get_message_metrics(service: ChatService = Depends(get_chat_service)):
    return await service.get_messages_metrics()
