from apis.evolution.evolution_api_client import EvolutionAPIClient
from memory import MongoDBMemoryManager
import logging
import pytz
from typing import Dict, Any

logger = logging.getLogger(__name__)
BR_TZ = pytz.timezone("America/Sao_Paulo")


class EvolutionService:
    def __init__(self):
        self.client = EvolutionAPIClient()
        self.memory_manager = MongoDBMemoryManager()

    async def find_all_chats(self) -> Dict[str, Any]:
        """
        Busca todos os chats do WhatsApp

        Returns:
            Dict com a lista de chats
        """
        try:
            chats = await self.client.find_chats()
            logger.info(f"Chats encontrados: {len(chats)}")

            simplified_chats = []
            for chat in chats:
                if isinstance(chat, dict):
                    simplified_chats.append(
                        {
                            "id": chat.get("id"),
                            "phone": chat.get("remoteJid"),
                            "name": chat.get("pushName", "Sem nome"),
                            "profile_pic": chat.get("profilePicUrl"),
                            "updated_at": chat.get("updatedAt"),
                        }
                    )

            return {
                "success": True,
                "chats": simplified_chats,
                "count": len(simplified_chats),
            }
        except Exception as e:
            logger.error(f"Erro ao buscar chats: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_conversation(self, phone: str) -> Dict[str, Any]:
        """
        Busca a conversa completa com um contato

        Args:
            phone: Número de telefone

        Returns:
            Dict com as mensagens da conversa
        """
        try:
            chats = await self.client.find_chats()
            chat_info = None

            clean_phone = "".join(filter(str.isdigit, phone))

            for chat in chats:
                if isinstance(chat, dict) and "remoteJid" in chat:
                    remote_jid = chat.get("remoteJid", "")
                    if clean_phone in remote_jid:
                        chat_info = chat
                        break

            messages = await self.client.find_messages(phone)
            logger.info(f"Mensagens encontradas para {phone}: {len(messages)}")

            conversation = []
            for msg in messages:
                if isinstance(msg, dict):
                    key = msg.get("key", {})
                    if isinstance(key, dict):
                        remote_jid = key.get("remoteJid", "")
                        if clean_phone not in remote_jid:
                            continue

                    content = None
                    msg_type = "text"
                    is_from_me = False

                    if isinstance(key, dict):
                        is_from_me = key.get("fromMe", False)

                    message_data = msg.get("message", {})
                    if isinstance(message_data, dict):
                        if "conversation" in message_data:
                            content = message_data["conversation"]
                        elif "imageMessage" in message_data:
                            content = message_data.get("imageMessage", {}).get(
                                "caption", "[Imagem]"
                            )
                            msg_type = "image"
                        elif "videoMessage" in message_data:
                            content = message_data.get("videoMessage", {}).get(
                                "caption", "[Vídeo]"
                            )
                            msg_type = "video"
                        elif "audioMessage" in message_data:
                            content = "[Áudio]"
                            msg_type = "audio"
                        elif "documentMessage" in message_data:
                            content = f"[Documento: {message_data.get('documentMessage', {}).get('fileName', '')}]"
                            msg_type = "document"

                    if not content:
                        if "body" in msg:
                            content = msg["body"]
                        else:
                            content = "[Conteúdo não suportado]"

                    conversation.append(
                        {
                            "id": msg.get("id", ""),
                            "sender": (
                                "Você"
                                if is_from_me
                                else (
                                    chat_info.get("pushName")
                                    if chat_info
                                    else "Contato"
                                )
                            ),
                            "content": content,
                            "type": msg_type,
                            "timestamp": msg.get("messageTimestamp", 0),
                            "fromMe": is_from_me,
                        }
                    )

            conversation.sort(key=lambda x: x.get("timestamp", 0))

            return {
                "success": True,
                "contact": {
                    "name": (
                        chat_info.get("pushName", "Contato") if chat_info else "Contato"
                    ),
                    "phone": phone,
                    "profile_pic": (
                        chat_info.get("profilePicUrl") if chat_info else None
                    ),
                },
                "messages": conversation,
                "count": len(conversation),
            }
        except Exception as e:
            logger.error(f"Erro ao buscar conversa: {str(e)}")
            return {"success": False, "error": str(e)}

    async def send_message_to_user(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Envia uma mensagem para um usuário

        Args:
            phone: Número do telefone do destinatário
            message: Texto da mensagem

        Returns:
            Dict com informações sobre o envio
        """
        try:
            result = await self.client.send_message(phone, message)

            return {
                "success": result.get("success", False),
                "message_id": result.get("message_id"),
                "status": result.get("status"),
                "timestamp": result.get("timestamp"),
            }

        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para o usuário: {str(e)}")
            return {"success": False, "error": str(e)}
