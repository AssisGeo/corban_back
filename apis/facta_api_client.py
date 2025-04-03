import aiohttp
import os
import logging
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DadosPessoaisPayload(BaseModel):
    id_simulador: str
    cpf: str
    nome: str
    sexo: str
    estado_civil: Optional[int] = Field(default=1)
    data_nascimento: str
    rg: str
    estado_rg: str
    orgao_emissor: str
    data_expedicao: str
    estado_natural: str
    cidade_natural: int
    nacionalidade: Optional[int] = Field(default=1)
    pais_origem: Optional[str] = Field(default="26")
    celular: str
    renda: str
    cep: str
    endereco: str
    bairro: str
    numero: int
    complemento: Optional[str] = None
    cidade: int
    estado: str
    nome_mae: str
    nome_pai: Optional[str] = None
    valor_patrimonio: Optional[int] = Field(default=2)
    cliente_iletrado_impossibilitado: Optional[str] = Field(default="N")
    banco: str
    agencia: str
    conta: str
    tipo_conta: Optional[str] = Field(default="C")

    class Config:
        validate_assignment = True
        populate_by_name = True

    def model_dump_for_api(self) -> Dict[str, Any]:
        """
        Método personalizado para serializar o modelo para envio à API,
        garantindo que todos os campos opcionais tenham seus valores padrão
        """
        data = self.model_dump(exclude_none=True)

        defaults = {
            "estado_civil": 1,
            "nacionalidade": 1,
            "pais_origem": "26",
            "valor_patrimonio": 2,
            "cliente_iletrado_impossibilitado": "N",
            "tipo_conta": "C",
        }

        for key, default_value in defaults.items():
            if key not in data or data[key] is None:
                data[key] = default_value

        return {key: str(value) for key, value in data.items()}


class FactaApi:
    def __init__(self, user=None, password=None):
        self.token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.token_offline: Optional[str] = None
        self.token_expiry_offline: Optional[datetime] = None

        # URLs base
        self.base_url: str = os.getenv("FACTA_BASE_URL")
        self.base_url_offline: str = os.getenv("FACTA_OFFLINE_URL")
        # URLs específicas
        self.token_url: str = f"{self.base_url}/gera-token"
        self.token_url_offline: str = f"{self.base_url_offline}/gera-token"
        self.fgts_saldo_url: str = f"{self.base_url}/fgts/saldo"
        self.fgts_calculo_url: str = f"{self.base_url}/fgts/calculo"
        self.fgts_offline_url: str = f"{self.base_url_offline}/fgts/base-offline"
        self.proposta_etapa1_url: str = f"{self.base_url}/proposta/etapa1-simulador"
        self.proposta_etapa2_url: str = (
            f"{self.base_url}/proposta/etapa2-dados-pessoais"
        )
        self.proposta_etapa3_url: str = (
            f"{self.base_url}/proposta/etapa3-proposta-cadastro"
        )
        self.proposta_envio_link_url: str = f"{self.base_url}/proposta/envio-link"

        # Credenciais
        self.user: str = user or os.getenv("FACTA_USER")
        self.password: str = password or os.getenv("FACTA_PASSWORD")
        self.session: Optional[aiohttp.ClientSession] = None
        self.check_environment_variables()

    def check_environment_variables(self) -> None:
        """Verifica se as variáveis de ambiente estão carregadas corretamente."""
        required_vars = ["FACTA_USER", "FACTA_PASSWORD"]
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

    async def authenticate(self, offline: bool = False) -> str:
        """Autentica na API e obtém o token de sessão.

        Args:
            offline: Se True, autentica na API offline, caso contrário na API principal
        """
        now = datetime.now()

        if offline:
            if (
                self.token_offline
                and self.token_expiry_offline
                and now < self.token_expiry_offline
            ):
                return self.token_offline
        else:
            if self.token and self.token_expiry and now < self.token_expiry:
                return self.token

        await self.start_session()

        token_url = self.token_url_offline if offline else self.token_url
        auth_string = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()

        try:
            async with self.session.get(
                token_url, headers={"Authorization": f"Basic {auth_string}"}
            ) as response:
                response.raise_for_status()
                data = await response.json()

                if data.get("erro"):
                    raise ValueError(f"Erro ao obter token: {data.get('mensagem')}")

                token = data.get("token")
                token_expiry = now + timedelta(minutes=55)

                if not token:
                    raise ValueError("Token não foi recebido após login.")

                # Armazenar token na variável correta
                if offline:
                    self.token_offline = token
                    self.token_expiry_offline = token_expiry
                else:
                    self.token = token
                    self.token_expiry = token_expiry

                logger.info(
                    f"Autenticado com sucesso na API {'offline' if offline else 'principal'}."
                )
                return token

        except aiohttp.ClientResponseError as e:
            logger.error(f"Erro na autenticação: {e.status} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado durante autenticação: {str(e)}")
            raise

    async def get_auth_headers(self, offline: bool = False) -> Dict[str, str]:
        """Retorna os headers de autorização para as requisições."""
        if offline:
            if (
                not self.token_offline
                or not self.token_expiry_offline
                or datetime.now() >= self.token_expiry_offline
            ):
                await self.authenticate(offline=True)
            return {"Authorization": f"Bearer {self.token_offline}"}
        else:
            if (
                not self.token
                or not self.token_expiry
                or datetime.now() >= self.token_expiry
            ):
                await self.authenticate(offline=False)
            return {"Authorization": f"Bearer {self.token}"}

    async def consultar_base_offline(self, cpf: str) -> Dict[str, Any]:
        """Consulta se um CPF está autorizado na base offline da CEF."""
        await self.start_session()
        headers = await self.get_auth_headers(offline=True)
        url = f"{self.fgts_offline_url}?cpf={cpf}"

        try:
            async with self.session.get(url, headers=headers) as response:
                logger.info(f"Chamada API: URL={url}, Status={response.status}")
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                logger.error("Limite de requisições atingido (2 por segundo)")
            logger.error(f"Erro ao consultar base offline: {e.status} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao consultar base offline: {str(e)}")
            raise
        finally:
            await self.close_session()

    async def consultar_saldo_fgts(self, cpf: str) -> Dict[str, Any]:
        """Consulta o saldo disponível para antecipação do FGTS."""
        await self.start_session()
        headers = await self.get_auth_headers()
        url = f"{self.fgts_saldo_url}?cpf={cpf}"

        try:
            async with self.session.get(url, headers=headers) as response:
                logger.info(f"Chamada API: URL={url}, Status={response.status}")
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(f"Erro ao consultar saldo FGTS: {e.status} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao consultar saldo FGTS: {str(e)}")
            raise
        finally:
            await self.close_session()

    async def simular_valor_fgts(
        self,
        cpf: str,
        parcelas: List[Dict[str, str]],
        taxa: str = "1.8",
        tabela: str = "57851",
    ) -> Dict[str, Any]:
        """Simula o valor líquido para antecipação do FGTS usando JSON."""
        await self.start_session()
        headers = await self.get_auth_headers()

        payload = {"cpf": cpf, "taxa": taxa, "tabela": tabela, "parcelas": parcelas}

        try:
            async with self.session.post(
                self.fgts_calculo_url, json=payload, headers=headers
            ) as response:
                logger.info(
                    f"Chamada API: URL={self.fgts_calculo_url}, Status={response.status}"
                )
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(f"Erro ao simular valor FGTS: {e.status} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao simular valor FGTS: {str(e)}")
            raise
        finally:
            await self.close_session()

    async def cadastrar_simulacao(
        self,
        cpf: str,
        data_nascimento: str,
        simulacao_fgts: str,
    ) -> Dict[str, Any]:
        """Etapa 1: Cadastro da simulação."""
        await self.start_session()
        headers = await self.get_auth_headers()
        headers_form = dict(headers)
        headers_form["Content-Type"] = "application/x-www-form-urlencoded"

        if not cpf or not data_nascimento or not simulacao_fgts:
            error_msg = f"Dados inválidos para simulação: CPF={cpf}, Data={data_nascimento}, Simulação={simulacao_fgts}"
            logger.error(error_msg)
            return {"erro": True, "mensagem": error_msg}

        # Verificar formato da data
        if not isinstance(data_nascimento, str):
            data_nascimento = str(data_nascimento)

        # Garantir que não tem caracteres de formatação indevidos
        data_nascimento = data_nascimento.replace("{", "").replace("}", "")

        form_data = {
            "produto": "D",
            "tipo_operacao": 13,
            "averbador": 20095,
            "convenio": 3,
            "cpf": cpf,
            "data_nascimento": data_nascimento,
            "login_certificado": self.user,
            "simulacao_fgts": simulacao_fgts,
        }
        try:
            async with self.session.post(
                self.proposta_etapa1_url, data=form_data, headers=headers_form
            ) as response:
                logger.info(
                    f"Chamada API: URL={self.proposta_etapa1_url}, Status={response.status}"
                )

                response_text = await response.text()
                logger.info(f"Resposta bruta da API: {response_text}")

                try:
                    response_data = json.loads(response_text)
                    logger.info(
                        f"Resposta da API de simulação como JSON: {response_data}"
                    )
                    return response_data
                except json.JSONDecodeError:
                    logger.error(f"Erro ao decodificar JSON: {response_text}")
                    return {
                        "erro": True,
                        "mensagem": f"Resposta inválida: {response_text}",
                    }

        except aiohttp.ClientResponseError as e:
            error_msg = f"Erro no cadastro da simulação: {e.status} - {e.message}"
            logger.error(error_msg)
            return {"erro": True, "mensagem": error_msg}
        except Exception as e:
            error_msg = f"Erro inesperado no cadastro da simulação: {str(e)}"
            logger.error(error_msg)
            return {"erro": True, "mensagem": error_msg}
        finally:
            await self.close_session()

    async def cadastrar_dados_pessoais(
        self, dados_pessoais: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Etapa 2: Cadastro dos dados pessoais do cliente."""
        await self.start_session()
        headers = await self.get_auth_headers()
        headers_form = dict(headers)
        headers_form["Content-Type"] = "application/x-www-form-urlencoded"

        try:
            required_fields = ["id_simulador"]
            for field in required_fields:
                if field not in dados_pessoais or not dados_pessoais[field]:
                    error_msg = f"Campo obrigatório ausente: {field}"
                    logger.error(error_msg)
                    return {"erro": True, "mensagem": error_msg}

            id_simulador = dados_pessoais.get("id_simulador")
            if isinstance(id_simulador, str):
                # Remover prefixo "facta_" e quaisquer chaves/colchetes
                id_simulador = (
                    id_simulador.replace("facta_", "").replace("{", "").replace("}", "")
                )
                # Atualizar o valor nos dados
                dados_pessoais["id_simulador"] = id_simulador

            form_data = {}
            for key, value in dados_pessoais.items():
                if value is not None:
                    form_data[key] = str(value)

            logger.debug(f"Dados completos para envio: {form_data}")

            async with self.session.post(
                self.proposta_etapa2_url, data=form_data, headers=headers_form
            ) as response:
                logger.info(
                    f"Chamada API: URL={self.proposta_etapa2_url}, Status={response.status}"
                )

                response_text = await response.text()
                logger.debug(f"Resposta bruta: {response_text}")

                try:
                    response_data = json.loads(response_text)
                    return response_data
                except json.JSONDecodeError:
                    return {
                        "erro": True,
                        "mensagem": f"Resposta inválida: {response_text}",
                    }

        except aiohttp.ClientResponseError as e:
            error_msg = f"Erro no cadastro dos dados pessoais: {e.status} - {e.message}"
            logger.error(error_msg)
            return {"erro": True, "mensagem": error_msg}
        except Exception as e:
            error_msg = f"Erro inesperado no cadastro dos dados pessoais: {str(e)}"
            logger.error(error_msg)
            return {"erro": True, "mensagem": error_msg}
        finally:
            await self.close_session()

    async def cadastrar_proposta(
        self,
        codigo_cliente: str,
        id_simulador: str,
    ) -> Dict[str, Any]:
        """Etapa 3: Cadastro da proposta."""
        await self.start_session()
        headers = await self.get_auth_headers()
        headers_form = dict(headers)
        headers_form["Content-Type"] = "application/x-www-form-urlencoded"

        form_data = {"codigo_cliente": codigo_cliente, "id_simulador": id_simulador}

        form_data["tipo_formalizacao"] = "DIG"

        try:
            async with self.session.post(
                self.proposta_etapa3_url, data=form_data, headers=headers_form
            ) as response:
                logger.info(
                    f"Chamada API: URL={self.proposta_etapa3_url}, Status={response.status}"
                )
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(f"Erro no cadastro da proposta: {e.status} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado no cadastro da proposta: {str(e)}")
            raise
        finally:
            await self.close_session()

    async def enviar_link_formalizacao(
        self, codigo_af: str, tipo_envio: str  # "whatsapp" ou "sms"
    ) -> Dict[str, Any]:
        """Envia link de formalização para o cliente por SMS ou WhatsApp."""
        await self.start_session()
        headers = await self.get_auth_headers()
        headers_form = dict(headers)
        headers_form["Content-Type"] = "application/x-www-form-urlencoded"

        form_data = {
            "codifo_af": codigo_af,  # Nota: a API usa "codifo_af" em vez de "codigo_af"
            "tipo_envio": tipo_envio,
        }

        try:
            async with self.session.post(
                self.proposta_envio_link_url, data=form_data, headers=headers_form
            ) as response:
                logger.info(
                    f"Chamada API: URL={self.proposta_envio_link_url}, Status={response.status}"
                )
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(
                f"Erro no envio do link de formalização: {e.status} - {e.message}"
            )
            raise
        except Exception as e:
            logger.error(f"Erro inesperado no envio do link de formalização: {str(e)}")
            raise
        finally:
            await self.close_session()

    async def consultar_combobox(
        self, endpoint: str, params: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Consulta os comboboxes disponíveis (produto, banco, averbador, etc.)."""
        await self.start_session()
        headers = await self.get_auth_headers()

        url = f"{self.base_url}/proposta-combos/{endpoint}"
        if params:
            query_params = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_params}"

        try:
            async with self.session.get(url, headers=headers) as response:
                logger.info(f"Chamada API: URL={url}, Status={response.status}")
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(
                f"Erro ao consultar combobox {endpoint}: {e.status} - {e.message}"
            )
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao consultar combobox {endpoint}: {str(e)}")
            raise
        finally:
            await self.close_session()

    @staticmethod
    def criar_payload_parcelas(
        simulate_response: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """
        Cria a estrutura correta de parcelas para envio à API de simulação.

        Args:
            simulate_response: Resposta completa da API de consulta de saldo FGTS

        Returns:
            Lista formatada para envio à API
        """
        if not simulate_response or simulate_response.get("erro", True):
            return []

        retorno = simulate_response.get("retorno", {})
        payload = []

        # Processa as parcelas existentes na resposta
        for i in range(1, 11):
            data_key = f"dataRepasse_{i}"
            valor_key = f"valor_{i}"

            data_repasse = retorno.get(data_key, f"01/07/{2024 + i}")
            valor = retorno.get(valor_key, "0.00")

            parcela = {
                f"dataRepasse_{i}": data_repasse,
                f"valor_{i}": valor,
            }
            payload.append(parcela)

        return payload
