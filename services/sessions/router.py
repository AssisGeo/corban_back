from fastapi import APIRouter, HTTPException, Depends
from .schemas import SessionCreate, SessionResponse
from .service import SessionService
from memory import MongoDBMemoryManager
import pytz
from datetime import datetime
import logging

BR_TZ = pytz.timezone("America/Sao_Paulo")
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

        customer_info = session.get("customer_data", {}).get("customer_info", {})
        phone_info = customer_info.get("phone", {})
        phone = (
            f"{phone_info.get('ddd', '')}{phone_info.get('number', '')}"
            if phone_info
            else ""
        )
        created_at = datetime.now(BR_TZ)
        print(created_at.isoformat())
        return SessionResponse(
            session_id=session.get("session_id", ""),
            name=customer_info.get("name"),
            email=customer_info.get("email"),
            cpf=customer_info.get("cpf"),
            phone=phone,
            zip_code=customer_info.get("zip_code"),
            created_at=created_at.isoformat(),
            status=session.get("status", "unknown"),
            source=session.get("source", "unknown"),
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
        leads = []

        for lead in result["leads"]:
            customer_info = lead.get("customer_data", {}).get("customer_info", {})
            phone_info = customer_info.get("phone", {})

            # Construindo o número de telefone com validação
            phone = ""
            if phone_info:
                ddd = phone_info.get("ddd", "")
                number = phone_info.get("number", "")
                if ddd and number:
                    phone = f"{ddd}{number}"

            leads.append(
                SessionResponse(
                    session_id=lead.get("session_id", ""),
                    name=customer_info.get("name"),
                    email=customer_info.get("email"),
                    cpf=customer_info.get("cpf"),
                    phone=phone,
                    zip_code=customer_info.get("zip_code"),
                    created_at=lead["created_at"].isoformat(),
                    status=lead.get("status", "unknown"),
                    source=lead.get("metadata", {}).get(
                        "origin", lead.get("source", "unknown")
                    ),
                )
            )

        return {
            "leads": leads,
            "total": result["total"],
            "page": result["page"],
            "total_pages": result["total_pages"],
        }
    except Exception as e:
        logger.error(f"Erro ao listar leads de tráfego: {str(e)}")
        return {"leads": [], "total": 0, "page": 1, "total_pages": 0}


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

        customer_info = session.get("customer_data", {}).get("customer_info", {})
        phone_info = customer_info.get("phone", {})
        phone = (
            f"{phone_info.get('ddd', '')}{phone_info.get('number', '')}"
            if phone_info
            else ""
        )

        return SessionResponse(
            session_id=session.get("session_id", ""),
            name=customer_info.get("name"),
            email=customer_info.get("email"),
            cpf=customer_info.get("cpf"),
            phone=phone,
            zip_code=customer_info.get("zip_code"),
            created_at=session["created_at"].isoformat(),
            status=session.get("status", "unknown"),
            source=session.get("source", "unknown"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar sessão: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
