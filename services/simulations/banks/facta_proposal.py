from .base import BankProposal, ProposalResult
from models.vctex.models import SendProposalInput
from typing import Dict, Any, Optional
import logging
from apis.facta_api_client import FactaApi
from pymongo import MongoClient
import os

logger = logging.getLogger(__name__)


class FactaBankProposal(BankProposal):
    def __init__(self):
        self.client = FactaApi()
        # Inicializar conexão com MongoDB para buscar dados da simulação
        self.mongo_client = MongoClient(os.getenv("MONGODB_URL"))
        self.db = self.mongo_client["fgts_agent"]
        self.simulations = self.db["fgts_simulations"]

    @property
    def bank_name(self) -> str:
        return "FACTA"

    async def obter_cpf_correto_da_simulacao(self, simulation_id: str) -> Optional[str]:
        """
        Busca o CPF correto da simulação diretamente na coleção.
        Tenta várias estratégias para encontrar o CPF.
        """
        # Remove prefixo facta_ se existir
        search_id = simulation_id
        normalized_id = simulation_id.replace("facta_", "")

        # Estratégia 1: Buscar simulação pelo ID exato
        simulation = self.simulations.find_one({"financial_id": search_id})
        if simulation and "cpf" in simulation:
            cpf = simulation.get("cpf")
            return cpf

        # Estratégia 2: Buscar simulação pelo ID normalizado
        simulation = self.simulations.find_one({"financial_id": normalized_id})
        if simulation and "cpf" in simulation:
            cpf = simulation.get("cpf")
            return cpf

        # Estratégia 3: Buscar simulação onde o raw_response contenha o ID
        simulation = self.simulations.find_one(
            {"raw_response.simulacao_fgts": normalized_id}
        )
        if simulation and "cpf" in simulation:
            cpf = simulation.get("cpf")
            return cpf

        # Estratégia 4: Procurar em todas as simulações do banco FACTA
        simulations = list(self.simulations.find({"bank_name": "FACTA"}))

        for sim in simulations:
            raw = sim.get("raw_response", {})
            if isinstance(raw, dict) and "simulacao_fgts" in raw:
                if raw["simulacao_fgts"] == normalized_id:
                    cpf = sim.get("cpf")
                    return cpf

        return None

    async def submit_proposal(self, proposal_data: SendProposalInput) -> ProposalResult:
        try:
            normalized_cpf = proposal_data["cpf"].replace(".", "").replace("-", "")

            simulation_id = proposal_data["id_simulador"]
            real_simulation_id = simulation_id.replace("facta_", "")

            # 3. NOVO: Buscar o CPF correto da simulação original
            simulation_cpf = await self.obter_cpf_correto_da_simulacao(simulation_id)

            # 4. Se encontrou um CPF diferente, usar ele
            if simulation_cpf and simulation_cpf != normalized_cpf:
                normalized_cpf = simulation_cpf

            birthdate_str = self._format_date_for_facta(
                proposal_data["data_nascimento"]
            )

            etapa1_result = await self.client.cadastrar_simulacao(
                cpf=normalized_cpf,
                data_nascimento=birthdate_str,
                simulacao_fgts=real_simulation_id,
            )

            # Verificar se houve erro na etapa 1
            if etapa1_result.get("erro"):
                return ProposalResult(
                    bank_name=self.bank_name,
                    error_message=etapa1_result.get("mensagem", "Erro na etapa 1"),
                    success=False,
                    raw_response=etapa1_result,
                )

            # Extrair o ID do simulador retornado na etapa 1
            id_simulador = etapa1_result.get("id_simulador")
            if not id_simulador:
                return ProposalResult(
                    bank_name=self.bank_name,
                    error_message="ID do simulador não foi retornado na etapa 1",
                    success=False,
                    raw_response=etapa1_result,
                )

            # Formatar telefone no formato exato exigido: (DDD) XXXXX-XXXX
            formatted_phone = self._format_phone_exact(proposal_data["celular"])
            # Construir payload da etapa 2 com TODOS os campos obrigatórios
            dados_pessoais = {
                "id_simulador": id_simulador,
                "cpf": normalized_cpf,
                "nome": proposal_data["nome"],
                "sexo": "M" if proposal_data["sexo"].lower() in ["male", "m"] else "F",
                "estado_civil": 1,  # 1=Solteiro por padrão
                "data_nascimento": birthdate_str,
                "rg": proposal_data["rg"],
                "estado_rg": proposal_data["estado_rg"],
                "orgao_emissor": proposal_data["orgao_emissor"],
                "data_expedicao": self._format_date_for_facta(
                    proposal_data["data_expedicao"]
                ),
                "estado_natural": proposal_data["estado_rg"],
                "cidade_natural": 540,  # Valor padrão para cidade
                "nacionalidade": 1,  # 1=Brasileiro
                "pais_origem": "26",  # 26=Brasil
                "celular": formatted_phone,  # No formato exato (099) 99999-9999
                "renda": "2500",  # Valor padrão
                "cep": self._format_cep(proposal_data["cep"]),
                "endereco": proposal_data["endereco"],
                "bairro": proposal_data["bairro"] or "Centro",
                "numero": (
                    int(proposal_data["numero"])
                    if proposal_data["numero"].isdigit()
                    else 1
                ),
                "cidade": 540,
                "estado": proposal_data["estado"],
                "nome_mae": proposal_data["nome_mae"],
                # campos obrigatórios
                "nome_pai": "Não declarado",  # Campo obrigatório
                "cliente_iletrado_impossibilitado": "N",  # Campo obrigatório
                "valor_patrimonio": 2,  # Campo padrão exigido pela API
                "banco": proposal_data["banco"],
                "agencia": proposal_data["agencia"],
                "conta": proposal_data["conta"],
                "tipo_conta": (
                    "C" if proposal_data["tipo_conta"].lower() == "corrente" else "P"
                ),
            }

            etapa2_result = await self.client.cadastrar_dados_pessoais(dados_pessoais)

            if etapa2_result.get("erro"):
                return ProposalResult(
                    bank_name=self.bank_name,
                    error_message=etapa2_result.get("mensagem", "Erro na etapa 2"),
                    success=False,
                    raw_response=etapa2_result,
                )

            codigo_cliente = etapa2_result.get("codigo_cliente")
            if not codigo_cliente:
                return ProposalResult(
                    bank_name=self.bank_name,
                    error_message="Código do cliente não retornado na etapa 2",
                    success=False,
                    raw_response=etapa2_result,
                )

            etapa3_result = await self.client.cadastrar_proposta(
                codigo_cliente=codigo_cliente, id_simulador=id_simulador
            )

            if etapa3_result.get("erro"):
                return ProposalResult(
                    bank_name=self.bank_name,
                    error_message=etapa3_result.get("mensagem", "Erro na etapa 3"),
                    success=False,
                    raw_response=etapa3_result,
                )

            contract_number = etapa3_result.get("codigo")

            if contract_number and proposal_data["celular"]:
                try:
                    await self.client.enviar_link_formalizacao(
                        codigo_af=contract_number, tipo_envio="sms"
                    )
                except Exception as link_error:
                    logger.warning(f"[FACTA] Erro ao enviar link: {str(link_error)}")

            formalization_link = etapa3_result.get("url_formalizacao")

            return ProposalResult(
                bank_name=self.bank_name,
                contract_number=contract_number,
                success=True,
                raw_response=etapa3_result,
                formalization_link=formalization_link,
            )

        except Exception as e:
            logger.error(f"[FACTA] Erro na proposta: {str(e)}", exc_info=True)
            return ProposalResult(
                bank_name=self.bank_name,
                error_message=str(e),
                success=False,
                raw_response={"error": str(e)},
            )

    async def check_status(self, contract_number: str) -> Dict[str, Any]:
        return {
            "success": True,
            "status": "pending",
            "message": "Para Facta, use o link enviado ou consulte o portal",
        }

    async def send_formalization_link(
        self, contract_number: str, method: str = "whatsapp"
    ) -> Dict[str, Any]:
        """Envia link de formalização para o cliente"""
        try:
            result = await self.client.enviar_link_formalizacao(
                codigo_af=contract_number, tipo_envio=method
            )

            return {
                "success": not result.get("erro", False),
                "message": result.get("mensagem", "Link enviado com sucesso"),
                "status": "sent" if not result.get("erro", False) else "error",
            }
        except Exception as e:
            logger.error(f"[FACTA] Erro ao enviar link de formalização: {str(e)}")
            return {"success": False, "error": str(e), "status": "error"}

    def _format_date_for_facta(self, date_obj: Any) -> str:
        """Formata uma data para o padrão aceito pela Facta (DD/MM/YYYY)"""
        if isinstance(date_obj, str):
            # Assumindo formato ISO (YYYY-MM-DD)
            parts = date_obj.split("-")
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
            return date_obj

        if (
            hasattr(date_obj, "day")
            and hasattr(date_obj, "month")
            and hasattr(date_obj, "year")
        ):
            return f"{date_obj.day:02d}/{date_obj.month:02d}/{date_obj.year}"

        return str(date_obj)

    def _format_phone(self, phone: str) -> str:
        """Formata um número de telefone para uso genérico"""
        # Remover todos os caracteres não numéricos
        numbers = "".join(filter(str.isdigit, phone))

        # Se o número começar com 55 (código do Brasil), remover
        if numbers.startswith("55") and len(numbers) > 10:
            numbers = numbers[2:]

        # Formatar como (DD) DDDDD-DDDD
        if len(numbers) >= 10:
            return f"({numbers[:2]}) {numbers[2:7]}-{numbers[7:]}"
        elif len(numbers) >= 8:
            return f"({numbers[:2]}) {numbers[2:]}"
        else:
            return numbers

    def _format_phone_exact(self, phone: str) -> str:
        """
        Formata o número de telefone no formato EXATO: (099) 99999-9999

        Handles various input formats including:
        - Phones with or without country code
        - Phones with different separators
        - Incomplete or malformed phone numbers
        """
        # Remove all non-digit characters
        numeros = "".join(filter(str.isdigit, phone))

        # Remove the country code if it exists (55 for Brazil)
        if numeros.startswith("55"):
            numeros = numeros[2:]

        # Ensure the number has at least 10 digits (DDD + phone)
        if len(numeros) < 10:
            # Pad with zeros if too short
            numeros = numeros.zfill(10)

        # If longer than 11 digits, take the last 11
        numeros = numeros[-11:]

        # Separate the parts
        ddd = numeros[:2]
        prefixo = numeros[2:7]
        sufixo = numeros[7:]

        # Return in the exact format: (099) 99999-9999
        return f"(0{ddd}) {prefixo}-{sufixo}"

    def _format_cep(self, cep: str) -> str:
        """Formata um CEP para o padrão XXXXX-XXX"""
        # Remover todos os caracteres não numéricos
        numbers = "".join(filter(str.isdigit, cep))

        # Formatar como XXXXX-XXX
        if len(numbers) >= 8:
            return f"{numbers[:5]}-{numbers[5:8]}"
        else:
            return numbers
