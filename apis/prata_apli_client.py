import aiohttp
import os
import logging
from typing import Optional, Dict, Any
from apis.helpers import format_prata_response

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PrataApi:
    def __init__(self):
        self.token: Optional[str] = None
        self.proxy_url: str = os.getenv("PROXY_URL", "")
        self.base_url: str = "https://api.bancoprata.com.br/v1"
        self.login_url: str = f"{self.base_url}/users/login"
        self.pix_url: str = f"{self.base_url}/payments/bank-account/info"
        self.user: str = os.getenv("PRATA_USER_NAME", "")
        self.password: str = os.getenv("PRATA_USER_PASSWORD", "")
        self.session: Optional[aiohttp.ClientSession] = None
        self.check_environment_variables()

    def check_environment_variables(self) -> None:
        """Verifica se as variáveis de ambiente estão carregadas corretamente."""
        required_vars = ["PROXY_URL", "PRATA_USER_NAME", "PRATA_USER_PASSWORD"]
        for var in required_vars:
            if not os.getenv(var):
                logger.error(f"Variável de ambiente {var} não está definida.")
                raise EnvironmentError(f"Variável de ambiente {var} não está definida.")

    async def start_session(self) -> None:
        """Inicia uma sessão HTTP com os headers necessários."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False),
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            logger.info("Nova sessão HTTP iniciada.")

    async def close_session(self) -> None:
        """Fecha a sessão HTTP."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Sessão HTTP fechada.")

    async def authenticate(self) -> str:
        """Autentica na API e obtém o token de sessão."""
        if self.token:
            return self.token
        await self.start_session()
        try:
            payload = {"email": self.user, "password": self.password}
            async with self.session.post(
                self.login_url, json=payload, proxy=self.proxy_url
            ) as response:
                response.raise_for_status()
                data = await response.json()
                self.token = data.get("data", {}).get("token")
                if not self.token:
                    raise ValueError("Token não foi recebido após login.")
                logger.info("Autenticado com sucesso.")
                return self.token
        except aiohttp.ClientResponseError as e:
            logger.error(f"Erro na autenticação: {e.status} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado durante autenticação: {str(e)}")
            raise

    async def get_auth_headers(self) -> Dict[str, str]:
        """Retorna os headers de autorização para as requisições."""
        if not self.token:
            await self.authenticate()
        return {"Authorization": f"Bearer {self.token}"}

    async def fetch_pix(self, pix_key: str) -> Optional[Dict[str, Any]]:
        """Busca as informações PIX com base na chave PIX fornecida."""
        await self.start_session()
        headers = await self.get_auth_headers()
        url = f"{self.pix_url}?pix_key={pix_key}"
        try:
            async with self.session.get(
                url, headers=headers, proxy=self.proxy_url
            ) as response:
                logger.info(f"Chamada API: URL={url}, Status={response.status}")
                response.raise_for_status()
                pix_data = await response.json()
                if not pix_data.get("data"):
                    raise ValueError("Informações PIX não encontradas.")
                formatted_data = format_prata_response(pix_data)
                if formatted_data:
                    return formatted_data.model_dump()
                else:
                    logger.warning("Falha ao formatar os dados da conta.")
                    return None
        except aiohttp.ClientResponseError as e:
            logger.error(f"Erro ao buscar informações PIX: {e.status} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar informações PIX: {str(e)}")
            raise
        finally:
            await self.close_session()
