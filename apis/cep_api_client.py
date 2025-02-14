import aiohttp
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class CepAPIClient:
    def __init__(self):
        self.base_url = "https://viacep.com.br/ws/"
        self.session = None

    async def start_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def fetch_address_by_cep(self, cep: str) -> Dict[str, Any]:
        await self.start_session()
        url = f"{self.base_url}{cep}/json/"

        try:
            async with self.session.get(url) as response:
                logger.debug(f"API Response Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    if "erro" in data:
                        return {"error": "CEP não encontrado"}
                    return {
                        "zipCode": data.get("cep"),
                        "street": data.get("logradouro"),
                        "neighborhood": data.get("bairro"),
                        "city": data.get("localidade"),
                        "state": data.get("uf"),
                    }
                else:
                    return {"error": f"Erro {response.status} ao buscar CEP"}
        except aiohttp.ClientError as e:
            logger.error(f"Erro de conexão: {str(e)}")
            return {"error": "Erro de conexão"}
        except Exception as e:
            logger.error(f"Erro inesperado: {str(e)}")
            return {"error": "Erro inesperado"}
