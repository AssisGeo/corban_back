from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional, List
from memory import MongoDBMemoryManager
import math

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
        self, page: int = 1, per_page: int = 20, search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lista chats com paginação.

        Args:
            page: Número da página (começa em 1)
            per_page: Número de itens por página
            search: Termo de busca opcional

        Returns:
            Dict com itens paginados e informações de paginação
        """
        try:
            page = max(1, page)
            per_page = max(1, per_page)

            skip = (page - 1) * per_page

            base_query = {
                "$and": [{"messages": {"$exists": True}}, {"messages": {"$ne": []}}]
            }

            if search:
                base_query["$or"] = [
                    {"session_id": {"$regex": search, "$options": "i"}},
                    {
                        "customer_data.customer_info.name": {
                            "$regex": search,
                            "$options": "i",
                        }
                    },
                    {
                        "customer_data.borrower.name": {
                            "$regex": search,
                            "$options": "i",
                        }
                    },
                    {"cpf": {"$regex": search, "$options": "i"}},
                ]

            total = self.memory_manager.collection.count_documents(base_query)
            total_pages = math.ceil(total / per_page) if total > 0 else 1

            chats = list(
                self.memory_manager.collection.find(base_query)
                .sort("last_updated", -1)
                .skip(skip)
                .limit(per_page)
            )

            items = []
            for chat in chats:
                try:
                    converted = self._convert_document_to_chat(chat)
                    if converted:
                        items.append(converted)
                except Exception as e:
                    logger.error(
                        f"Erro ao converter chat {chat.get('session_id')}: {e}"
                    )
                    continue

            return {
                "items": items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
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
                if isinstance(msg, dict):
                    sender = None
                    content = None

                    # Formato original do bot
                    if "type" in msg and "data" in msg:
                        msg_type = msg["type"]
                        content = msg["data"].get("content")
                        sender = "Cliente" if msg_type == "human" else "Assistente"
                    # Formato role/content
                    elif "role" in msg:
                        sender = "Cliente" if msg["role"] == "user" else "Assistente"
                        content = msg.get("content")

                    if content and sender:
                        if sender == "Cliente":
                            customer_name = (
                                document.get("customer_data", {})
                                .get("customer_info", {})
                                .get("name")
                            )
                            if customer_name:
                                sender = customer_name

                        messages.append({"sender": sender, "content": content})

            return {
                "session_id": document.get("session_id"),
                "customer_name": document.get("customer_data", {})
                .get("customer_info", {})
                .get("name"),
                "messages": messages,
                "last_updated": document.get("last_updated"),
                "contract_number": document.get("contract_number", ""),
            }

        except Exception as e:
            logger.error(f"Erro ao obter conversa: {str(e)}")
            raise

    async def get_chat_stats(self) -> Dict[str, Any]:
        try:
            # Usar UTC para consistência com MongoDB
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            # Contagem de mensagens
            messages_pipeline = [
                {"$match": {"messages": {"$exists": True, "$ne": []}}},
                {"$project": {"message_count": {"$size": "$messages"}}},
                {"$group": {"_id": None, "total": {"$sum": "$message_count"}}},
            ]

            messages_result = list(
                self.memory_manager.collection.aggregate(messages_pipeline)
            )
            total_messages = messages_result[0]["total"] if messages_result else 0

            # Buscar chats válidos (com mensagens)
            chats = list(
                self.memory_manager.collection.find(
                    {"messages": {"$exists": True, "$ne": []}}
                )
            )

            total_sessions = len(chats)

            # CORREÇÃO: Usar query direta no MongoDB para contar sessões ativas hoje
            # Isso evita problemas de timezone e formato de data
            active_today_query = {
                "messages": {"$exists": True, "$ne": []},
                "last_updated": {
                    "$gte": today_start,
                    "$lt": today_start + timedelta(days=1),
                },
            }
            active_today = self.memory_manager.collection.count_documents(
                active_today_query
            )

            # Contratos completos (verificar se contract_number existe e não está vazio)
            successful_chats = sum(
                1
                for chat in chats
                if chat.get("contract_number") and chat.get("contract_number") != ""
            )

            success_rate = (
                (successful_chats / total_sessions * 100) if total_sessions > 0 else 0
            )

            # Cálculo da duração com proteção contra erros
            durations = []
            for chat in chats:
                if chat.get("created_at") and chat.get("last_updated"):
                    try:
                        # Calcular duração em minutos e filtrar valores absurdos
                        duration = (
                            chat["last_updated"] - chat["created_at"]
                        ).total_seconds() / 60
                        if 0 < duration < 1440:  # Entre 0 e 24 horas
                            durations.append(duration)
                    except Exception as e:
                        logger.debug(f"Erro ao calcular duração: {e}")
                        continue

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
        """
        Converte um documento do MongoDB para o formato esperado pelo frontend.

        Args:
            document: Documento do MongoDB

        Returns:
            Dict formatado ou None em caso de erro
        """
        try:
            messages = []
            for msg in document.get("messages", []):
                if isinstance(msg, dict):
                    sender = None
                    content = None

                    # Formato original do bot
                    if "type" in msg and "data" in msg:
                        msg_type = msg["type"]
                        content = msg["data"].get("content")
                        sender = "Cliente" if msg_type == "human" else "Assistente"
                    # Formato role/content
                    elif "role" in msg:
                        sender = "Cliente" if msg["role"] == "user" else "Assistente"
                        content = msg.get("content")

                    if content and sender:
                        if sender == "Cliente":
                            customer_name = (
                                document.get("customer_data", {})
                                .get("customer_info", {})
                                .get("name")
                            )
                            if customer_name:
                                sender = customer_name

                        messages.append({"sender": sender, "content": content})

            customer_name = (
                document.get("customer_data", {}).get("customer_info", {}).get("name")
                or document.get("customer_data", {}).get("borrower", {}).get("name")
                or document.get("name")
                or "Cliente não identificado"
            )

            return {
                "session_id": document.get("session_id"),
                "customer_name": customer_name,
                "messages": messages,
                "last_updated": document.get("last_updated"),
                "contract_number": document.get("contract_number", ""),
            }

        except Exception as e:
            logger.error(f"Erro ao converter documento: {str(e)}")
            return None

    async def get_pipeline_data(
        self, page: int = 1, per_page: int = 20, cpf_search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtém dados da pipeline com paginação, tratando todos os documentos como uma única coleção.
        Versão corrigida para evitar registros duplicados entre páginas.
        """
        try:
            page = max(1, page)
            per_page = max(1, per_page)

            skip = (page - 1) * per_page

            base_query = {}
            if cpf_search:
                base_query["$or"] = [
                    {
                        "customer_data.customer_info.cpf": {
                            "$regex": cpf_search,
                            "$options": "i",
                        }
                    },
                    {"customer_data.cpf": {"$regex": cpf_search, "$options": "i"}},
                    {"cpf": {"$regex": cpf_search, "$options": "i"}},
                ]

            # Usar o $group para garantir que cada session_id apareça apenas uma vez
            pipeline = [
                {"$match": base_query},
                {
                    "$group": {
                        "_id": "$session_id",
                        "doc": {"$first": "$$ROOT"},
                        "last_updated": {"$max": "$last_updated"},
                    }
                },
                {"$replaceRoot": {"newRoot": "$doc"}},
                {
                    "$addFields": {
                        "has_contract": {
                            "$cond": [
                                {
                                    "$and": [
                                        {"$ifNull": ["$contract_number", False]},
                                        {"$ne": ["$contract_number", ""]},
                                    ]
                                },
                                True,
                                False,
                            ]
                        }
                    }
                },
                {"$sort": {"has_contract": -1, "last_updated": -1}},
                {"$skip": skip},
                {"$limit": per_page},
            ]

            # Calcular contagens com a mesma lógica de agrupamento para consistência
            count_pipeline = [
                {"$match": base_query},
                {"$group": {"_id": "$session_id"}},
                {"$count": "total"},
            ]

            count_with_contract_pipeline = [
                {
                    "$match": {
                        **base_query,
                        "contract_number": {"$exists": True, "$ne": ""},
                    }
                },
                {"$group": {"_id": "$session_id"}},
                {"$count": "total"},
            ]

            count_without_contract_pipeline = [
                {
                    "$match": {
                        **base_query,
                        "$or": [
                            {"contract_number": {"$exists": False}},
                            {"contract_number": ""},
                        ],
                    }
                },
                {"$group": {"_id": "$session_id"}},
                {"$count": "total"},
            ]

            # Executar contagens
            count_result = list(
                self.memory_manager.collection.aggregate(count_pipeline)
            )
            total = count_result[0]["total"] if count_result else 0

            count_with_contract = list(
                self.memory_manager.collection.aggregate(count_with_contract_pipeline)
            )
            total_with_contract = (
                count_with_contract[0]["total"] if count_with_contract else 0
            )

            count_without_contract = list(
                self.memory_manager.collection.aggregate(
                    count_without_contract_pipeline
                )
            )
            total_without_contract = (
                count_without_contract[0]["total"] if count_without_contract else 0
            )

            # Executar pipeline principal para obter os registros
            chats = list(self.memory_manager.collection.aggregate(pipeline))

            # Processar os resultados
            pipeline_items = []
            for doc in chats:
                customer_data = doc.get("customer_data", {})

                def determine_stage(data: Dict[str, Any]) -> str:
                    """
                    Determina o estágio atual baseado na última flag True.
                    A ordem dos estágios importa - verificamos na sequência desejada.
                    """
                    stage_flags = [
                        (
                            "post_formalize",
                            customer_data.get("post_formalize_confirmed"),
                        ),
                        ("formalize", customer_data.get("formalize_confirmed")),
                        (
                            "send_proposal",
                            customer_data.get("proposal_sent")
                            or bool(doc.get("contract_number")),
                        ),
                        ("collect_document", customer_data.get("document_confirmed")),
                        ("collect_bank", customer_data.get("bank_data_confirmed")),
                        ("collect_address", customer_data.get("address_confirmed")),
                        (
                            "collect_personal",
                            customer_data.get("personal_data_confirmed"),
                        ),
                        (
                            "simulate",
                            customer_data.get("simulation_complete")
                            or bool(doc.get("simulation_data")),
                        ),
                        ("check_cpf", customer_data.get("cpf_validated")),
                        ("start", True),  # Estágio padrão
                    ]

                    for stage, flag in stage_flags:
                        if flag:
                            return stage

                    return "start"

                simulation_data = doc.get("simulation_data", {})

                def extract_value(text: str) -> str:
                    """Extrai o valor numérico de um texto formatado."""
                    if not text:
                        return "Valor ainda não foi informado"
                    if isinstance(text, str):
                        if "R$" in text:
                            return text.split("R$")[1].strip().split()[0].rstrip(",.")
                        if "%" in text:
                            return text.split("%")[0].strip().split()[-1].rstrip(",.")
                    return str(text).rstrip(",.")

                # Busca CPF em várias possíveis fontes
                cpf = (
                    customer_data.get("customer_info", {}).get("cpf")
                    or customer_data.get("cpf")
                    or doc.get("cpf")
                    or "CPF não informado"
                )

                # Busca link de formalização em várias possíveis fontes
                formalization_link = (
                    doc.get("formalization_link")
                    or customer_data.get("formalization_link")
                    or "Link não disponível"
                )

                # Busca nome do cliente em várias possíveis fontes
                customer_name = (
                    customer_data.get("customer_info", {}).get("name")
                    or customer_data.get("borrower", {}).get("name")
                    or doc.get("name")
                    or "Nome não informado"
                )

                phone_number = doc.get("session_id")
                send_by = doc.get("send_by") or customer_data.get("send_by") or "manual"
                proposal_created_at = customer_data.get("proposal_created_at")

                item = {
                    "contract_number": doc.get("contract_number")
                    or "Contrato não disponível",
                    "session_id": doc.get("session_id", "Sessão não identificada"),
                    "customer_name": customer_name,
                    "cpf": cpf,
                    "stage": determine_stage(customer_data),
                    "simulation": {
                        "total_released": extract_value(
                            simulation_data.get("total_released", "")
                        ),
                        "total_to_pay": extract_value(
                            simulation_data.get("total_to_pay", "")
                        ),
                        "interest_rate": extract_value(
                            simulation_data.get("interest_rate", "")
                        ),
                        "iof_fee": extract_value(simulation_data.get("iof_fee", "")),
                    },
                    "send_by": send_by,
                    "formalization_link": formalization_link,
                    "has_contract": bool(doc.get("contract_number")),
                    "proposal_created_at": proposal_created_at
                    or "Proposta aguardando envio",
                    "phone_number": phone_number,
                }
                pipeline_items.append(item)

            total_pages = math.ceil(total / per_page) if total > 0 else 1

            return {
                "items": pipeline_items,
                "total": total,
                "total_with_contract": total_with_contract,
                "total_without_contract": total_without_contract,
                "page": page,
                "per_page": per_page,
                "pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
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

    async def get_messages_metrics(self, page: int = 1, per_page: int = 20):
        try:
            page = max(1, page)
            per_page = max(1, per_page)

            skip = (page - 1) * per_page

            count_pipeline = [
                {
                    "$match": {
                        "messages": {"$exists": True, "$ne": []},
                    }
                },
                {"$unwind": "$messages"},
                {"$count": "total"},
            ]

            count_result = list(
                self.memory_manager.collection.aggregate(count_pipeline)
            )
            total_messages = count_result[0]["total"] if count_result else 0

            pipeline = [
                {
                    "$match": {
                        "messages": {"$exists": True, "$ne": []},
                    }
                },
                {"$unwind": "$messages"},
                {
                    "$project": {
                        "timestamp": {
                            "$toDate": {
                                "$ifNull": ["$messages.timestamp", "$last_updated"]
                            }
                        },
                        "dayOfWeek": {
                            "$dayOfWeek": {
                                "$toDate": {
                                    "$ifNull": ["$messages.timestamp", "$last_updated"]
                                }
                            }
                        },
                        "hour": {
                            "$hour": {
                                "$toDate": {
                                    "$ifNull": ["$messages.timestamp", "$last_updated"]
                                }
                            }
                        },
                    }
                },
                {"$sort": {"timestamp": -1}},
                {"$skip": skip},
                {"$limit": per_page},
                {
                    "$group": {
                        "_id": {"weekDay": "$dayOfWeek", "hour": "$hour"},
                        "count": {"$sum": 1},
                    }
                },
                {"$sort": {"_id.weekDay": 1, "_id.hour": 1}},
            ]

            result = list(self.memory_manager.collection.aggregate(pipeline))

            hours = {i: 0 for i in range(24)}
            weekdays = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
            weekday_data = {day: 0 for day in weekdays}

            page_messages_count = 0
            peak_hour = {"hour": 0, "count": 0}
            peak_day = {"day": "", "count": 0}

            # Processa resultados
            for doc in result:
                if doc["_id"] and isinstance(doc["_id"], dict):
                    hour = doc["_id"].get("hour")
                    weekday_idx = doc["_id"].get("weekDay")
                    count = doc["count"]
                    page_messages_count += count

                    if hour is not None and 0 <= hour < 24:
                        hours[hour] += count
                        if hours[hour] > peak_hour["count"]:
                            peak_hour = {"hour": hour, "count": hours[hour]}

                    if weekday_idx is not None and 1 <= weekday_idx <= 7:
                        weekday = weekdays[weekday_idx - 1]
                        weekday_data[weekday] += count
                        if weekday_data[weekday] > peak_day["count"]:
                            peak_day = {"day": weekday, "count": weekday_data[weekday]}

            avg_per_hour = page_messages_count / 24 if page_messages_count > 0 else 0
            avg_per_day = page_messages_count / 7 if page_messages_count > 0 else 0

            total_pages = (
                math.ceil(total_messages / per_page) if total_messages > 0 else 1
            )

            return {
                "hourly": {
                    "labels": [f"{h}h" for h in range(24)],
                    "data": list(hours.values()),
                },
                "weekly": {
                    "labels": weekdays,
                    "data": list(weekday_data.values()),
                },
                "metrics": {
                    "total_messages": total_messages,
                    "current_page_messages": page_messages_count,
                    "peak_hour": peak_hour,
                    "peak_day": peak_day,
                    "avg_messages_per_hour": round(avg_per_hour, 2),
                    "avg_messages_per_day": round(avg_per_day, 2),
                },
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_messages,
                    "pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
            }

        except Exception as e:
            logger.error(f"Erro ao obter métricas de mensagens: {str(e)}")
            raise

    async def get_contract_details(self, session_id: str) -> Dict[str, Any]:
        """
        Obtém detalhes completos do contrato/proposta para um chat específico.

        Args:
            session_id: Identificador único da sessão

        Returns:
            Dict com informações detalhadas sobre o contrato, cliente, dados financeiros e formalização

        Raises:
            ValueError: Se o chat não for encontrado
            Exception: Para outros erros durante o processamento
        """
        try:
            document = self.memory_manager.collection.find_one(
                {"session_id": session_id}
            )
            if not document:
                raise ValueError(f"Chat não encontrado: {session_id}")

            # Tratar dados do cliente
            customer_data = document.get("customer_data", {})
            customer_info = customer_data.get("customer_info", {})
            borrower = customer_data.get("borrower", {})
            proposal_data = document.get("proposal_data", {})

            # Obter nome do cliente de múltiplas fontes possíveis
            customer_name = (
                customer_info.get("name")
                or borrower.get("name")
                or document.get("name", "")
            )

            # Obter CPF de múltiplas fontes possíveis
            customer_cpf = customer_data.get("cpf", "")
            if not customer_cpf:
                customer_cpf = (
                    customer_info.get("cpf")
                    or borrower.get("cpf")
                    or document.get("cpf")
                    or proposal_data.get("cpf")
                    or ""
                )

            # Obter email do cliente
            customer_email = (
                borrower.get("email")
                or customer_info.get("email")
                or document.get("email", "")
            )

            # Verificar contrato
            contract_number = document.get("contract_number", "")
            has_contract = bool(contract_number) and contract_number != ""

            # Determinar estágio atual
            def determine_stage(data: Dict[str, Any]) -> str:
                """Determina o estágio atual com base nas flags de progresso"""
                stage_flags = [
                    ("post_formalize", data.get("post_formalize_confirmed")),
                    ("formalize", data.get("formalize_confirmed")),
                    ("send_proposal", data.get("proposal_sent") or has_contract),
                    ("collect_document", data.get("document_confirmed")),
                    ("collect_bank", data.get("bank_data_confirmed")),
                    ("collect_address", data.get("address_confirmed")),
                    ("collect_personal", data.get("personal_data_confirmed")),
                    (
                        "simulate",
                        data.get("simulation_complete")
                        or bool(document.get("simulation_data")),
                    ),
                    ("check_cpf", data.get("cpf_validated")),
                    ("start", True),  # Estágio padrão
                ]

                for stage, flag in stage_flags:
                    if flag:
                        return stage

                return "start"

            # Dados de simulação
            simulation_data = document.get("simulation_data", {})

            # Endereço
            address = {}
            if "address" in customer_data:
                address = customer_data.get("address", {})
            elif "address" in document:
                address = document.get("address", {})
            elif "address" in proposal_data:
                address = proposal_data.get("address", {})
            elif "zip_code" in customer_info:
                address = {
                    "zipCode": customer_info.get("zip_code"),
                    "street": customer_info.get("street", ""),
                    "number": customer_info.get("address_number", ""),
                    "neighborhood": customer_info.get("neighborhood", ""),
                    "city": customer_info.get("city", ""),
                    "state": customer_info.get("state", ""),
                }

            if not isinstance(address, dict):
                address = {}

            # Link de formalização
            formalization_link = customer_data.get("formalization_link", "")
            if not formalization_link:
                formalization_link = (
                    document.get("formalization_link", "")
                    or document.get("proposal_data", {}).get("formalization_link", "")
                    or document.get("contractFormalizationLink", "")
                )

            # Status de formalização
            formalization_status = "pending"
            if customer_data.get("formalize_confirmed") or document.get(
                "formalization_completed"
            ):
                formalization_status = "completed"
            elif customer_data.get("formalization_initiated"):
                formalization_status = "in_progress"

            # Data de criação
            created_at = self._get_value_from_nested_paths(
                document,
                [
                    "created_at",
                    "metadata.created_at",
                    "customer_data.created_at",
                    "proposal_data.created_at",
                ],
            )

            # Data de atualização
            updated_at = self._get_value_from_nested_paths(
                document,
                [
                    "last_updated",
                    "updated_at",
                    "metadata.updated_at",
                    "customer_data.updated_at",
                ],
            )

            # Data de envio da proposta
            proposal_sent_at = customer_data.get("proposal_created_at")
            if not proposal_sent_at:
                proposal_sent_at = self._get_value_from_nested_paths(
                    document,
                    [
                        "proposal_sent_at",
                        "proposal_data.created_at",
                        "proposal_data.sent_at",
                    ],
                )

            # Data de formalização
            formalization_completed_at = document.get("formalization_completed_at")

            # Função para formatar datas
            def format_date(date_obj):
                if date_obj:
                    if hasattr(date_obj, "isoformat"):
                        return date_obj.isoformat()
                    return str(date_obj)
                return None

            # Eventos importantes
            events = []
            if created_at:
                events.append(
                    {
                        "type": "created",
                        "description": "Sessão iniciada",
                        "timestamp": format_date(created_at),
                    }
                )

            # Timestamp de simulação
            simulation_timestamp = self._get_value_from_nested_paths(
                document,
                [
                    "simulation_data.timestamp",
                    "simulation_data.created_at",
                    "simulation_date",
                ],
            )

            if document.get("simulation_data"):
                events.append(
                    {
                        "type": "simulation",
                        "description": "Simulação realizada",
                        "timestamp": format_date(simulation_timestamp)
                        or format_date(updated_at),
                    }
                )

            # Evento de proposta
            if contract_number:
                events.append(
                    {
                        "type": "proposal",
                        "description": f"Proposta criada: {contract_number}",
                        "timestamp": format_date(proposal_sent_at)
                        or format_date(updated_at),
                    }
                )

            # Evento de formalização
            if formalization_status in ["in_progress", "completed"]:
                events.append(
                    {
                        "type": "formalization",
                        "description": (
                            "Formalização iniciada"
                            if formalization_status == "in_progress"
                            else "Formalização concluída"
                        ),
                        "timestamp": format_date(
                            formalization_completed_at or updated_at
                        ),
                    }
                )

            # Outros eventos registrados
            if "events" in document and isinstance(document.get("events"), list):
                for event in document.get("events"):
                    if (
                        isinstance(event, dict)
                        and "type" in event
                        and "description" in event
                    ):
                        if "timestamp" in event:
                            event["timestamp"] = format_date(event["timestamp"])
                        events.append(event)

            # Metadados
            metadata = {
                "source": document.get("source", ""),
                "platform": document.get("metadata", {}).get("platform", ""),
                "send_by": customer_data.get("send_by")
                or document.get("send_by", "manual"),
                "origin": document.get("metadata", {}).get("origin", ""),
                "form_type": document.get("metadata", {}).get("form_type", ""),
                "current_state": document.get("current_state", ""),
            }

            # Dados bancários
            bank_data = customer_data.get("bank_data", {})
            if not bank_data:
                bank_data = (
                    document.get("disbursementBankAccount", {})
                    or customer_data.get("disbursementBankAccount", {})
                    or proposal_data.get("disbursementBankAccount", {})
                    or {}
                )

            # Construir resposta
            response = {
                "contract": {
                    "contract_number": contract_number or "Não disponível",
                    "status": determine_stage(customer_data),
                    "has_contract": has_contract,
                    "stage": determine_stage(customer_data),
                    "financial_id": document.get("financial_id", "")
                    or simulation_data.get("financialId", ""),
                    "created_at": format_date(created_at),
                    "updated_at": format_date(updated_at),
                },
                "customer": {
                    "name": customer_name,
                    "cpf": customer_cpf,
                    "phone_number": session_id,
                    "email": customer_email,
                    "address": address,
                    "bank_data": bank_data,
                    "document": customer_data.get("document", {}),
                },
                "financial": {
                    "total_released": simulation_data.get("total_released", ""),
                    "total_to_pay": simulation_data.get("total_to_pay", ""),
                    "interest_rate": simulation_data.get("interest_rate", ""),
                    "iof_fee": simulation_data.get("iof_fee", ""),
                },
                "formalization": {
                    "link": formalization_link,
                    "status": formalization_status,
                    "sent_at": format_date(proposal_sent_at),
                    "completed_at": format_date(formalization_completed_at),
                    "initiated": customer_data.get("formalization_initiated", False),
                },
                "events": events,
                "metadata": metadata,
            }

            # Adicionar parcelas se disponíveis
            installments = self._get_value_from_nested_paths(
                document,
                [
                    "installments",
                    "proposal_data.installments",
                    "simulation_data.installments",
                ],
            )

            if (
                installments
                and isinstance(installments, list)
                and len(installments) > 0
            ):
                response["financial"]["installments"] = installments

            return response

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Erro ao obter detalhes do contrato: {str(e)}")
            raise

    def _get_value_from_nested_paths(self, document: Dict, paths: List[str]):
        """Obtém o primeiro valor não nulo de uma lista de caminhos aninhados"""
        for path in paths:
            parts = path.split(".")
            value = document
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    value = None
                    break
            if value:
                return value
        return None
