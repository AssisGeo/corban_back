from fastapi import APIRouter, HTTPException, Depends
from .schemas import SessionCreate, SessionResponse
from .service import SessionService
from memory import MongoDBMemoryManager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


async def get_session_service():
    memory_manager = MongoDBMemoryManager()
    return SessionService(memory_manager)


@router.post("", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate, service: SessionService = Depends(get_session_service)
):
    logger.debug(f"Recebendo requisição de criação de sessão: {session_data}")
    try:
        session = await service.create_session(session_data.model_dump())
        logger.debug(f"Sessão criada com sucesso: {session}")

        return SessionResponse(
            session_id=session["session_id"],
            name=session["customer_data"]["customer_info"]["name"],
            email=session["customer_data"]["customer_info"]["email"],
            cpf=session["customer_data"]["customer_info"]["cpf"],
            phone=f"{session['customer_data']['customer_info']['phone']['ddd']}{session['customer_data']['customer_info']['phone']['number']}",
            zip_code=session["customer_data"]["customer_info"]["zip_code"],
            created_at=session["created_at"].isoformat(),
            status=session["status"],
            source=session["source"],
        )
    except Exception as e:
        logger.error(f"Erro ao criar sessão: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traffic/leads")
async def list_traffic_leads(
    skip: int = 0,
    limit: int = 10,
    service: SessionService = Depends(get_session_service),
):
    logger.debug("Listando leads de tráfego")
    try:
        result = await service.list_traffic_leads(skip=skip, limit=limit)
        leads = [
            SessionResponse(
                session_id=lead["session_id"],
                name=lead["customer_data"]["customer_info"]["name"],
                email=lead["customer_data"]["customer_info"]["email"],
                cpf=lead["customer_data"]["customer_info"]["cpf"],
                phone=f"{lead['customer_data']['customer_info']['phone']['ddd']}{lead['customer_data']['customer_info']['phone']['number']}",
                zip_code=lead["customer_data"]["customer_info"]["zip_code"],
                created_at=lead["created_at"].isoformat(),
                status=lead["status"],
                source=lead.get("metadata", {}).get(
                    "origin", lead.get("source", "unknown")
                ),
            )
            for lead in result["leads"]
        ]

        return {
            "leads": leads,
            "total": result["total"],
            "page": result["page"],
            "total_pages": result["total_pages"],
        }
    except Exception as e:
        logger.error(f"Erro ao listar leads de tráfego: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str, service: SessionService = Depends(get_session_service)
):
    logger.debug(f"Buscando sessão: {session_id}")
    try:
        session = await service.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")

        logger.debug(f"Sessão encontrada: {session}")

        return SessionResponse(
            session_id=session["session_id"],
            name=session["customer_data"]["customer_info"]["name"],
            email=session["customer_data"]["customer_info"]["email"],
            cpf=session["customer_data"]["customer_info"]["cpf"],
            phone=f"{session['customer_data']['customer_info']['phone']['ddd']}{session['customer_data']['customer_info']['phone']['number']}",
            zip_code=session["customer_data"]["customer_info"]["zip_code"],
            created_at=session["created_at"].isoformat(),
            status=session["status"],
            source=session["source"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar sessão: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
