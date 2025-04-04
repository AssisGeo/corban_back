# services/simulations/adapters/facta_adapter.py
from .base import BankAdapter
from models.normalized.simulation import NormalizedSimulationResponse
import re
from datetime import datetime
from models.normalized.proposal import NormalizedProposalRequest


class FactaBankAdapter(BankAdapter):
    @property
    def bank_name(self) -> str:
        return "FACTA"

    def normalize_simulation_response(
        self, raw_response: dict
    ) -> NormalizedSimulationResponse:

        valor_liquido = raw_response.get("valor_liquido", "0")
        if isinstance(valor_liquido, str):
            valor_liquido = re.sub(r"[^\d.,]", "", valor_liquido)
            valor_liquido = valor_liquido.replace(",", ".")

        try:
            available_amount = float(valor_liquido)
        except (ValueError, TypeError):
            available_amount = 0

        total_amount = 0
        iof_amount = raw_response.get("iof", 0)

        taxa = raw_response.get("taxa", "0")
        if isinstance(taxa, str):
            taxa = taxa.replace(",", ".")

        try:
            interest_rate = float(taxa)
        except (ValueError, TypeError):
            interest_rate = 0

        financial_id = f"facta_{raw_response.get('simulacao_fgts', '')}"

        return NormalizedSimulationResponse(
            bank_name=self.bank_name,
            financial_id=financial_id,
            available_amount=available_amount,
            total_amount=total_amount,
            interest_rate=interest_rate,
            iof_amount=iof_amount,
            raw_response=raw_response,
        )

    def prepare_proposal_request(
        self, normalized_request: NormalizedProposalRequest
    ) -> dict:
        # O formato do FACTA é diferente e precisa de mais conversões

        # Obter o ID da simulação sem o prefixo "facta_"
        simulation_id = normalized_request.financial_id
        if simulation_id.startswith("facta_"):
            simulation_id = simulation_id[6:]

        # Converter data de nascimento para o formato esperado pelo FACTA (DD/MM/YYYY)
        birth_date = normalized_request.customer.birth_date
        try:
            birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d")
            formatted_birth_date = birth_date_obj.strftime("%d/%m/%Y")
        except ValueError:
            formatted_birth_date = (
                birth_date  # Mantém o formato original em caso de erro
            )

        # Converter data de emissão do documento
        issue_date = normalized_request.document.issuing_date
        try:
            issue_date_obj = datetime.strptime(issue_date, "%Y-%m-%d")
            formatted_issue_date = issue_date_obj.strftime("%d/%m/%Y")
        except ValueError:
            formatted_issue_date = issue_date

        # Formatar telefone para o padrão do FACTA
        phone = normalized_request.customer.phone
        formatted_phone = self._format_phone(phone)

        # Preparar payload para FACTA
        return {
            "id_simulador": simulation_id,
            "cpf": normalized_request.customer.cpf,
            "data_nascimento": formatted_birth_date,
            "nome": normalized_request.customer.name,
            "sexo": (
                "M"
                if normalized_request.customer.gender.upper() in ["M", "MALE"]
                else "F"
            ),
            "estado_civil": 1,  # Padrão: Solteiro
            "rg": normalized_request.document.number,
            "estado_rg": normalized_request.document.issuing_state,
            "orgao_emissor": normalized_request.document.issuing_authority,
            "data_expedicao": formatted_issue_date,
            "celular": formatted_phone,
            "email": normalized_request.customer.email or "",
            "nome_mae": normalized_request.customer.mother_name,
            "cep": normalized_request.address.zip_code,
            "endereco": normalized_request.address.street,
            "numero": normalized_request.address.number,
            "bairro": normalized_request.address.neighborhood,
            "cidade": normalized_request.address.city,
            "estado": normalized_request.address.state,
            "complemento": normalized_request.address.complement or "",
            "banco": normalized_request.bank_data.bank_code,
            "agencia": normalized_request.bank_data.branch_number,
            "conta": normalized_request.bank_data.account_number,
            "tipo_conta": (
                "C"
                if normalized_request.bank_data.account_type.lower() == "corrente"
                else "P"
            ),
        }

    def _format_phone(self, phone: str) -> str:
        """Formata um número de telefone para o padrão do FACTA: (099) 99999-9999"""
        # Remove caracteres não numéricos
        numbers = "".join(filter(str.isdigit, phone))

        # Se começar com 55 (código do Brasil), remove
        if numbers.startswith("55") and len(numbers) > 10:
            numbers = numbers[2:]

        # Formata como (DDD) XXXXX-XXXX
        if len(numbers) >= 11:
            return f"(0{numbers[:2]}) {numbers[2:7]}-{numbers[7:]}"
        elif len(numbers) >= 10:
            return f"(0{numbers[:2]}) {numbers[2:6]}-{numbers[6:]}"
        else:
            # Caso o número não esteja no formato esperado
            return phone
