import aiohttp
from typing import Any, Dict
import os
from urllib.parse import urljoin
from dotenv import load_dotenv
from apis.helpers import format_simulation_response, format_proposal_response
import json
import traceback
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from cachetools import TTLCache
import structlog
from aiohttp import TCPConnector, ClientTimeout

load_dotenv()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

session_cache = TTLCache(maxsize=100, ttl=7200)


class VCTEXAPIClient:
    def __init__(self):
        self.proxy = True
        self.token = None
        self.token_expiration = None
        self.proxy_url = os.getenv("PROXY_URL")
        self.base_url = os.getenv("VCTEX_API_URL")
        self.session = None
        self.timeout = ClientTimeout(total=90)

    async def start_session(self):
        """Inicia uma nova sessão HTTP com configurações otimizadas."""
        if self.session is None or self.session.closed:
            connector = TCPConnector(
                ssl=False,
                limit=100,  # Limite de conexões simultâneas
                ttl_dns_cache=300,  # Cache DNS por 5 minutos
            )
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers={
                    "User-Agent": "VCTEX-Client/1.0",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            logger.info("session_created", status="success")

    async def close_session(self):
        """Fecha a sessão HTTP de forma segura."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("session_closed", status="success")

    def _is_token_expired(self) -> bool:
        """Verifica se o token atual está expirado."""
        if not self.token_expiration:
            return True
        return datetime.now() >= self.token_expiration

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def authenticate(self) -> str:
        """
        Autentica na API com retry automático e cache.
        Retorna o token de acesso.
        """
        try:
            # Verificar cache primeiro
            cached_token = session_cache.get("auth_token")
            if cached_token and not self._is_token_expired():
                return cached_token

            cpf = os.getenv("CPF")
            password = os.getenv("PASSWORD")
            if not cpf or not password:
                raise ValueError("Credenciais não configuradas (CPF/PASSWORD)")

            await self.start_session()
            response = await self._request(
                "POST",
                "authentication/login",
                {"cpf": cpf, "password": password},
                retry_auth=False,
            )

            if "token" not in response or "accessToken" not in response.get(
                "token", {}
            ):
                raise ValueError(f"Resposta de autenticação inválida: {response}")

            self.token = response["token"]["accessToken"]
            self.token_expiration = datetime.now() + timedelta(
                minutes=115
            )  # 5 min buffer

            # Atualizar cache
            session_cache["auth_token"] = self.token

            logger.info(
                "authentication_success", expiration=self.token_expiration.isoformat()
            )
            return self.token

        except Exception as e:
            logger.error(
                "authentication_failed", error=str(e), traceback=traceback.format_exc()
            )
            raise

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        retry_auth: bool = True,
    ) -> Dict[str, Any]:
        url = urljoin(self.base_url, endpoint)
        headers = headers or {}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        if not self.session or self.session.closed:
            await self.start_session()

        try:
            async with self.session.request(
                method,
                url,
                json=data,
                headers=headers,
                proxy=self.proxy_url if self.proxy else None,
                timeout=self.timeout,
            ) as response:
                response_text = await response.text()
                logger.info(
                    "api_request",
                    method=method,
                    endpoint=endpoint,
                    status_code=response.status,
                )

                try:
                    response_json = json.loads(response_text)
                except json.JSONDecodeError:
                    response_json = {"message": response_text}

                if response.status == 401 and retry_auth:
                    self.token = None
                    await self.authenticate()
                    return await self._request(method, endpoint, data, headers, False)

                return response_json

        except Exception as e:
            logger.error(
                "request_error", error=str(e), traceback=traceback.format_exc()
            )
            return {"message": str(e), "statusCode": 500}

    async def simulate_credit(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            await self.authenticate()
            response = await self._request("POST", "service/simulation", data)

            # Verificar se há erro na resposta
            if "message" in response and "statusCode" in response:
                if response["statusCode"] >= 400:
                    logger.error(f"Simulation error: {response}")
                    return response

            # Processar resposta bem-sucedida
            formatted_response = format_simulation_response(response)
            logger.info(
                "simulation_success",
                cpf=data.get("clientCpf"),
                financial_id=formatted_response.get("financialId"),
            )
            return formatted_response

        except Exception as e:
            logger.error(f"Error in simulation: {str(e)}")
            return {"message": str(e), "statusCode": 500}

    async def simulate_credit_by_installments(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simula crédito por parcelas."""
        try:
            await self.authenticate()
            response = await self._request(
                "POST", "service/simulation/installments", data
            )

            if "error" in response:
                return response

            formatted_response = format_simulation_response(response)
            logger.info("installment_simulation_success", cpf=data.get("clientCpf"))
            return formatted_response

        except Exception as e:
            logger.error(
                "installment_simulation_failed",
                error=str(e),
                traceback=traceback.format_exc(),
            )
            return {"error": f"Erro na simulação por parcelas: {str(e)}"}

    async def create_proposal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = await self._request("POST", "service/proposal", data)

            if (
                isinstance(response, dict)
                and "statusCode" in response
                and response["statusCode"] >= 400
            ):
                return {
                    "message": response["message"],
                    "statusCode": response["statusCode"],
                }
            return format_proposal_response(response)
        except Exception as e:
            return {"message": str(e), "statusCode": 500}

    async def proposal_detail(self, contract_number: str) -> Dict[str, Any]:
        """Obtém detalhes da proposta."""
        try:
            formatted_contract_number = contract_number.replace("/", "-")
            headers = {"contract-number": formatted_contract_number}
            response = await self._request(
                "GET", "service/proposal/contract-number", headers=headers
            )
            logger.info(
                "proposal_details_retrieved", contract_number=formatted_contract_number
            )
            return response
        except Exception as e:
            logger.error(
                "proposal_details_failed", contract_number=contract_number, error=str(e)
            )
            return {"error": str(e)}

    async def proposal_status(self, contract_number: str) -> Dict[str, Any]:
        try:
            formatted_contract_number = contract_number.replace("/", "-")
            headers = {"contract-number": formatted_contract_number}
            response = await self._request(
                "GET", "service/proposal/contract-number", headers=headers
            )

            if not response:
                return {"error": "Não foi possível obter resposta da API"}

            if "data" in response:
                format = response.get("data", {}).get("contractFormalizationLink")
                if format:
                    return {"status": format}
                return {"error": "Status não encontrado na resposta"}

            return {
                "error": response.get(
                    "message", "Erro desconhecido ao consultar status"
                )
            }

        except Exception as error:
            logger.error(f"Erro ao consultar status da proposta: {str(error)}")
            return {"error": f"Erro ao consultar status: {str(error)}"}

    async def handle_api_error(
        self, response: aiohttp.ClientResponse
    ) -> Dict[str, Any]:
        """Trata erros da API de forma estruturada."""
        try:
            error_json = await response.json()
            error_info = {
                "message": error_json.get("message", "Erro desconhecido da API"),
                "statusCode": error_json.get("statusCode", response.status),
                "code": error_json.get("code"),
                "sessionId": error_json.get("sessionId"),
            }
            logger.error("api_error_handled", **error_info)
            return error_info
        except json.JSONDecodeError:
            error_text = await response.text()
            error_info = {
                "message": error_text or "Erro desconhecido da API",
                "statusCode": response.status,
            }
            logger.error("api_error_handled", **error_info)
            return error_info
