import os
import logging
from typing import List, Dict, Any
from pymongo import MongoClient
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.memory import BaseMemory
from langchain_core.messages import (
    BaseMessage,
    message_to_dict,
    messages_from_dict,
    HumanMessage,
    AIMessage,
)
import pytz
from datetime import datetime
from pydantic import Field

logging.basicConfig(level=logging.INFO)
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("mongodb").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class MongoDBChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str, connection_string: str):
        self.session_id = session_id
        self.client = MongoClient(connection_string)
        self.db = self.client["fgts_agent"]
        self.collection = self.db["sessions"]

    @property
    def messages(self) -> List[BaseMessage]:
        session_data = self.collection.find_one({"session_id": self.session_id})
        if not session_data:
            return []
        return messages_from_dict(session_data.get("messages", []))

    def add_message(self, message: BaseMessage) -> None:
        messages = self.messages
        messages.append(message)
        messages_dict = [message_to_dict(msg) for msg in messages]

        brazil_tz = pytz.timezone("America/Sao_Paulo")
        timestamp = datetime.now(brazil_tz)

        self.collection.update_one(
            {"session_id": self.session_id},
            {
                "$set": {
                    "messages": messages_dict,
                    "last_updated": datetime.utcnow(),
                    "message_timestamps": {str(len(messages_dict) - 1): timestamp},
                },
            },
            upsert=True,
        )

    def clear(self) -> None:
        self.collection.update_one(
            {"session_id": self.session_id},
            {"$set": {"messages": []}},
            upsert=True,
        )


class MongoMemory(BaseMemory):
    chat_memory: MongoDBChatMessageHistory = Field(default=None)
    memory_key: str = Field(default="chat_history")
    return_messages: bool = Field(default=True)

    def __init__(self, session_id: str, mongo_url: str):
        super().__init__(
            chat_memory=MongoDBChatMessageHistory(session_id, mongo_url),
            memory_key="chat_history",
            return_messages=True,
        )

    @property
    def memory_variables(self) -> List[str]:
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {self.memory_key: self.chat_memory.messages}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        if inputs.get("input"):
            self.chat_memory.add_message(HumanMessage(content=inputs["input"]))
        if outputs.get("output"):
            self.chat_memory.add_message(AIMessage(content=outputs["output"]))

    def clear(self) -> None:
        self.chat_memory.clear()


class MongoDBMemoryManager:
    def __init__(self):
        self.mongo_url = os.getenv("MONGODB_URL")
        self.client = MongoClient(self.mongo_url)
        self.db = self.client["fgts_agent"]
        self.collection = self.db["sessions"]

    def get_memory(self, session_id: str) -> MongoMemory:
        """Retorna uma instância de memória para a sessão."""
        return MongoMemory(session_id, self.mongo_url)

    def get_user_context(self, session_id: str) -> str:
        """Recupera o contexto do usuário baseado no histórico."""
        try:
            memory = self.get_memory(session_id)
            context = []
            for msg in memory.chat_memory.messages:
                if isinstance(msg, HumanMessage):
                    context.append(f"User: {msg.content}")
                else:
                    context.append(f"Assistant: {msg.content}")
            return "\n".join(context) if context else "Sem contexto prévio."
        except Exception as e:
            logger.error(f"Erro ao obter contexto do usuário para {session_id}: {e}")
            return "Erro ao recuperar contexto."

    def set_session_data(self, session_id: str, key: str, value: Any):
        try:
            self.collection.update_one(
                {"session_id": session_id}, {"$set": {key: value}}, upsert=True
            )
            logger.info(f"Dados da sessão atualizados: {session_id}, chave: {key}")
        except Exception as e:
            logger.error(f"Erro ao definir dados da sessão {session_id}: {e}")

    def get_session_data(self, session_id: str, key: str) -> Any:
        try:
            result = self.collection.find_one({"session_id": session_id})
            return result.get(key) if result else None
        except Exception as e:
            logger.error(f"Erro ao obter dados da sessão {session_id}: {e}")
            return None

    def store_simulation_data(self, session_id: str, simulation_data: dict):
        """Armazena dados específicos de simulação FGTS."""
        try:
            self.collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "simulation_data": simulation_data,
                        "simulation_date": datetime.utcnow(),
                    }
                },
                upsert=True,
            )
            logger.info(
                f"Dados de simulação FGTS armazenados para sessão: {session_id}"
            )
        except Exception as e:
            logger.error(f"Erro ao armazenar simulação FGTS: {e}")

    def store_proposal_data(self, session_id: str, proposal_data: dict):
        """Armazena dados de proposta FGTS."""
        try:
            self.collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "proposal_data": proposal_data,
                        "proposal_date": datetime.utcnow(),
                    }
                },
                upsert=True,
            )
            logger.info(f"Dados de proposta FGTS armazenados para sessão: {session_id}")
        except Exception as e:
            logger.error(f"Erro ao armazenar proposta FGTS: {e}")

    def close(self):
        self.client.close()
        logger.info("Conexão com o MongoDB fechada")
