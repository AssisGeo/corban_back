import aiohttp
import os
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class EvolutionAPIClient:
    def __init__(self):
        self.base_url = os.getenv("EVOLUTION_API_URL")
        self.instance_name = os.getenv("EVOLUTION_INSTANCE")
        self.api_key = os.getenv("EVOLUTION_API_KEY")
        self.session = None

    async def start_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"apikey": self.api_key, "Content-Type": "application/json"}
            )
            logger.info("Sessão da Evolution API iniciada")

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Sessão da Evolution API fechada")

    async def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        await self.start_session()
        url = f"{self.base_url}/{endpoint}"

        try:
            async with self.session.request(method, url, json=data) as response:
                response_text = await response.text()
                try:
                    response_data = await response.json()
                except Exception:
                    logger.error(f"Resposta não é JSON válido: {response_text}")
                    response_data = {
                        "error": "Formato de resposta inválido",
                        "raw": response_text,
                    }

                if response.status >= 400:
                    logger.error(f"Erro na Evolution API: {response_data}")
                    raise Exception(f"Erro na Evolution API: {response_data}")

                logger.info(
                    f"Resposta da Evolution API para {endpoint}: {response_data}"
                )
                return response_data
        except Exception as e:
            logger.error(f"Erro na requisição para Evolution API: {str(e)}")
            raise

    async def find_chats(self) -> List[Dict]:
        """Obtém a lista de todos os chats"""
        endpoint = f"chat/findChats/{self.instance_name}"
        result = await self._request("POST", endpoint, {})

        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            return result.get("chats", [])
        return []

    def _format_phone(self, phone: str) -> str:
        """Formata o número de telefone para o padrão aceito pela API"""
        phone = "".join(filter(str.isdigit, phone))

        if phone.startswith("55") and len(phone) > 11:
            phone = phone[2:]

        if not phone.endswith("@c.us"):
            phone = f"{phone}@c.us"

        return phone

    async def find_messages(self, phone: str = None) -> List[Dict]:
        """
        Busca mensagens usando o endpoint chat/findMessages

        Args:
            phone: Número do WhatsApp (opcional)

        Returns:
            Lista de mensagens encontradas
        """
        if not phone:
            logger.warning("Telefone não fornecido para buscar mensagens")
            return []

        endpoint = f"chat/findMessages/{self.instance_name}"

        formatted_phone = self._format_phone(phone)

        payload = {
            "number": formatted_phone,
        }

        logger.info(f"Buscando mensagens para o telefone: {formatted_phone}")

        try:
            result = await self._request("POST", endpoint, payload)

            if isinstance(result, dict) and "conversation" in result:
                return result.get("conversation", [])
            elif isinstance(result, dict) and "chat" in result:
                return result.get("chat", [])
            elif (
                isinstance(result, dict)
                and "messages" in result
                and "records" in result["messages"]
            ):
                return result["messages"]["records"]
            else:
                logger.warning(f"Formato desconhecido na resposta: {result}")
                for key, value in result.items():
                    if isinstance(value, list) and len(value) > 0:
                        return value

                return []
        except Exception as e:
            logger.error(f"Erro ao buscar mensagens: {str(e)}")
            return []

    async def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Envia uma mensagem de texto para um número

        Args:
            phone: Número do destinatário (será formatado automaticamente)
            message: Texto da mensagem

        Returns:
            Dict com a resposta da API
        """
        try:
            clean_phone = "".join(filter(str.isdigit, phone))

            if not clean_phone.startswith("55") and len(clean_phone) <= 11:
                clean_phone = "55" + clean_phone

            logger.info(f"Enviando mensagem para {clean_phone}: {message[:30]}...")

            endpoint = f"message/sendText/{self.instance_name}"
            payload = {
                "number": clean_phone,
                "text": message,
                "delay": 1200,  # 1.2 segundos de delay para simular digitação
                "linkPreview": True,  # Ativa preview de links caso a mensagem contenha URLs
            }

            result = await self._request("POST", endpoint, payload)

            return {
                "success": True,
                "message_id": result.get("key", {}).get("id"),
                "status": result.get("status"),
                "timestamp": result.get("messageTimestamp"),
                "raw_response": result,
            }
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            return {"success": False, "error": str(e)}
