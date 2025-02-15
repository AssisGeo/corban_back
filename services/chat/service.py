from datetime import datetime
import logging
from typing import Dict, Any, Optional
from memory import MongoDBMemoryManager

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, memory_manager: MongoDBMemoryManager):
        self.memory_manager = memory_manager

    async def get_chat(self, session_id: str) -> Dict[str, Any]:
        try:
            document = self.memory_manager.collection.find_one(
                {"session_id": session_id}
            )
            if not document:
                raise ValueError(f"Chat não encontrado: {session_id}")
            return self._convert_document_to_chat(document)
        except Exception as e:
            logger.error(f"Erro ao obter chat: {str(e)}")
            raise

    async def list_chats(
        self, skip: int = 0, limit: int = 20, search: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            query = {"messages": {"$exists": True, "$ne": []}}
            if search:
                query["$or"] = [
                    {"session_id": {"$regex": search, "$options": "i"}},
                    {
                        "customer_data.customer_info.name": {
                            "$regex": search,
                            "$options": "i",
                        }
                    },
                ]

            total = self.memory_manager.collection.count_documents(query)
            chats = list(
                self.memory_manager.collection.find(query)
                .sort("last_updated", -1)
                .skip(skip)
                .limit(limit)
            )

            return {
                "items": [self._convert_document_to_chat(chat) for chat in chats],
                "total": total,
                "page": skip // limit + 1,
                "pages": -(-total // limit),
            }
        except Exception as e:
            logger.error(f"Erro ao listar chats: {str(e)}")
            raise

    async def get_chat_conversation(self, session_id: str) -> Dict[str, Any]:
        try:
            document = self.memory_manager.collection.find_one(
                {"session_id": session_id}
            )
            if not document:
                raise ValueError(f"Chat não encontrado: {session_id}")

            messages = []
            for msg in document.get("messages", []):
                if msg["type"] == "human" and msg["data"]["content"]:
                    messages.append(
                        {
                            "sender": document.get("customer_data", {})
                            .get("customer_info", {})
                            .get("name", "Cliente"),
                            "content": msg["data"]["content"],
                        }
                    )
                elif msg["type"] == "ai" and msg["data"]["content"]:
                    messages.append(
                        {"sender": "Assistente", "content": msg["data"]["content"]}
                    )

            return {
                "session_id": document.get("session_id"),
                "messages": messages,
                "customer_name": document.get("customer_data", {})
                .get("customer_info", {})
                .get("name"),
            }
        except Exception as e:
            logger.error(f"Erro ao obter conversa: {str(e)}")
            raise

    async def get_chat_stats(self) -> Dict[str, Any]:
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            chats = list(
                self.memory_manager.collection.find(
                    {"messages": {"$exists": True, "$ne": []}}
                )
            )

            total_sessions = len(chats)
            active_today = sum(
                1 for chat in chats if chat.get("last_updated", now) >= today_start
            )
            successful_chats = sum(1 for chat in chats if chat.get("contract_number"))
            success_rate = (
                (successful_chats / total_sessions * 100) if total_sessions > 0 else 0
            )

            durations = []
            total_messages = 0

            for chat in chats:
                messages = chat.get("messages", [])
                total_messages += len(messages)
                if messages:
                    created = chat.get("created_at")
                    last_updated = chat.get("last_updated")
                    if created and last_updated:
                        duration = (last_updated - created).total_seconds() / 60
                        durations.append(duration)

            avg_duration = sum(durations) / len(durations) if durations else 0

            return {
                "total_sessions": total_sessions,
                "active_today": active_today,
                "success_rate": round(success_rate, 2),
                "avg_duration_minutes": round(avg_duration, 2),
                "total_messages": total_messages,
                "completed_proposals": successful_chats,
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}")
            raise

    def _convert_document_to_chat(self, document: Dict) -> Dict[str, Any]:
        messages = []
        for msg in document.get("messages", []):
            if msg["type"] == "human" and msg["data"]["content"]:
                messages.append(
                    {
                        "sender": document.get("customer_data", {})
                        .get("customer_info", {})
                        .get("name", "Cliente"),
                        "content": msg["data"]["content"],
                    }
                )
            elif msg["type"] == "ai" and msg["data"]["content"]:
                messages.append(
                    {"sender": "Assistente", "content": msg["data"]["content"]}
                )

        return {
            "session_id": document.get("session_id"),
            "customer_name": document.get("customer_data", {})
            .get("customer_info", {})
            .get("name"),
            "messages": messages,
            "last_updated": document.get("last_updated"),
            "contract_number": document.get("contract_number", ""),
        }

    async def get_pipeline_data(
        self, skip: int = 0, limit: int = 20, cpf_search: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            query = {"contract_number": {"$exists": True}}

            if cpf_search:
                query["customer_data.customer_info.cpf"] = {
                    "$regex": cpf_search,
                    "$options": "i",
                }

            total = self.memory_manager.collection.count_documents(query)
            pipeline_items = []
            chats = list(
                self.memory_manager.collection.find(query).skip(skip).limit(limit)
            )

            for doc in chats:
                simulation_data = doc.get("simulation_data", {})
                customer_data = doc.get("customer_data", {}).get("customer_info", {})

                def extract_value(text: str) -> str:
                    if not text:
                        return "Valor não informado"
                    if "R$" in text:
                        return text.split("R$")[1].strip().split()[0].rstrip(",.")
                    if "%" in text:
                        return text.split("%")[0].strip().split()[-1].rstrip(",.")
                    return text.rstrip(",.")

                item = {
                    "contract_number": doc.get(
                        "contract_number", "Contrato não informado"
                    ),
                    "session_id": doc.get("session_id", "Telefone não informado"),
                    "customer_name": customer_data.get("name", "Nome não informado"),
                    "cpf": customer_data.get("cpf", "CPF não informado"),
                    "simulation": {
                        "total_released": extract_value(
                            simulation_data.get("total_released")
                        ),
                        "total_to_pay": extract_value(
                            simulation_data.get("total_to_pay")
                        ),
                        "interest_rate": extract_value(
                            simulation_data.get("interest_rate")
                        ),
                        "iof_fee": extract_value(simulation_data.get("iof_fee")),
                    },
                    "send_by": doc.get("send_by", "manual"),
                }
                pipeline_items.append(item)

            return {
                "items": pipeline_items,
                "total": total,
                "page": skip // limit + 1,
                "pages": (total + limit - 1) // limit,
            }
        except Exception as e:
            logger.error(f"Erro ao obter dados da esteira: {str(e)}")
            raise

    async def get_messages_by_hour(self, start_date=None, end_date=None):
        pipeline = [
            {"$match": {"messages": {"$exists": True, "$ne": []}}},
            {"$unwind": "$messages"},
            {"$project": {"hour": {"$hour": "$last_updated"}, "message": "$messages"}},
            {"$group": {"_id": "$hour", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]

        result = list(self.memory_manager.collection.aggregate(pipeline))
        return {
            "labels": [f"{doc['_id']}h" for doc in result],
            "data": [doc["count"] for doc in result],
        }

    async def get_messages_metrics(self):
        pipeline = [
            {
                "$match": {
                    "messages": {"$exists": True, "$ne": []},
                    "last_updated": {"$exists": True, "$ne": None},
                }
            },
            {"$unwind": "$messages"},
            {
                "$group": {
                    "_id": {
                        "weekDay": {"$dayOfWeek": "$last_updated"},
                        "hour": {"$hour": "$last_updated"},
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.weekDay": 1, "_id.hour": 1}},
        ]

        result = list(self.memory_manager.collection.aggregate(pipeline))

        hours = {i: 0 for i in range(24)}
        weekdays = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
        weekday_data = {day: 0 for day in weekdays}

        total_messages = 0
        peak_hour = {"hour": 0, "count": 0}
        peak_day = {"day": "", "count": 0}

        for doc in result:
            try:
                if doc["_id"] and isinstance(doc["_id"], dict):
                    hour = doc["_id"].get("hour")
                    weekday_idx = doc["_id"].get("weekDay")
                    count = doc["count"]

                    if hour is not None and 0 <= hour < 24:
                        hours[hour] += count
                        total_messages += count

                        if hours[hour] > peak_hour["count"]:
                            peak_hour = {"hour": hour, "count": hours[hour]}

                    if weekday_idx is not None and 1 <= weekday_idx <= 7:
                        weekday = weekdays[weekday_idx - 1]
                        weekday_data[weekday] += count

                        if weekday_data[weekday] > peak_day["count"]:
                            peak_day = {
                                "day": weekday,
                                "count": weekday_data[weekday],
                            }
            except Exception:
                continue

            avg_per_hour = total_messages / 24 if total_messages > 0 else 0
            avg_per_day = total_messages / 7 if total_messages > 0 else 0

        return {
            "hourly": {
                "labels": [f"{h}h" for h in range(24)],
                "data": list(hours.values()),
            },
            "weekly": {"labels": weekdays, "data": list(weekday_data.values())},
            "metrics": {
                "total_messages": total_messages,
                "peak_hour": peak_hour,
                "peak_day": peak_day,
                "avg_messages_per_hour": round(avg_per_hour, 2),
                "avg_messages_per_day": round(avg_per_day, 2),
            },
        }
