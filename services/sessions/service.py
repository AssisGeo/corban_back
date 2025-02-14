from datetime import datetime
from typing import Dict, Any, Optional
from memory import MongoDBMemoryManager
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import pytz

logger = logging.getLogger(__name__)

# Timezone Brasil
BR_TZ = pytz.timezone("America/Sao_Paulo")


class SessionService:
    def __init__(self, memory_manager: MongoDBMemoryManager):
        self.memory_manager = memory_manager
        self.client = AsyncIOMotorClient(memory_manager.mongo_url)
        self.db = self.client["fgts_agent"]
        self.collection = self.db["sessions"]

    async def create_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            session_id = f"55{session_data['phone']}"
            session = {
                "session_id": session_id,
                "customer_data": {
                    "customer_info": {
                        "name": session_data["name"],
                        "email": session_data["email"],
                        "cpf": session_data["cpf"],
                        "phone": {
                            "ddd": session_data["phone"][:2],
                            "number": session_data["phone"][2:],
                        },
                        "zip_code": session_data["zip_code"],
                    }
                },
                "created_at": datetime.now(BR_TZ),
                "status": "active",
                "source": "trafego",
                "metadata": {
                    "origin": "trafego",
                    "platform": "website",
                    "form_type": "session_creation",
                },
            }

            result = await self.collection.update_one(
                {"session_id": session_id}, {"$set": session}, upsert=True
            )

            return {**session, "created": result.upserted_id is not None}

        except Exception as e:
            logger.error(f"Erro ao criar sessão: {str(e)}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self.collection.find_one({"session_id": session_id})
        except Exception as e:
            logger.error(f"Erro ao buscar sessão: {str(e)}")
            raise

    async def list_traffic_leads(
        self, skip: int = 0, limit: int = 10
    ) -> Dict[str, Any]:
        """
        List all sessions with their sources (traffic or upload) with pagination
        """
        try:
            logger.debug("Iniciando busca por leads")
            query = {
                "$or": [
                    {"metadata.origin": "trafego"},
                    {"metadata.origin": "upload"},
                    {"source": "trafego"},
                    {"source": "upload"},
                ]
            }
            projection = {
                "session_id": 1,
                "customer_data.customer_info": 1,
                "created_at": 1,
                "status": 1,
                "metadata": 1,
                "source": 1,
            }

            # Conta total de documentos
            total = await self.collection.count_documents(query)

            # Busca os leads com paginação
            cursor = (
                self.collection.find(query, projection)
                .sort("created_at", -1)
                .skip(skip)
                .limit(limit)
            )
            leads = await cursor.to_list(length=None)

            # Converte a data para o timezone do Brasil
            for lead in leads:
                if "created_at" in lead:
                    lead["created_at"] = lead["created_at"].astimezone(BR_TZ)

            return {
                "leads": leads,
                "total": total,
                "page": skip // limit + 1,
                "total_pages": (total + limit - 1) // limit,
            }
        except Exception as e:
            logger.error(f"Error listing leads: {str(e)}")
            logger.error(f"Stack trace: {e.__traceback__}")
            return {"leads": [], "total": 0, "page": 1, "total_pages": 0}
