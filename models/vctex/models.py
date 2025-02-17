from pydantic import BaseModel, Field
from typing import Dict, Any


class SimulationInput(BaseModel):
    cpf: str = Field(..., description="CPF do cliente para simulação")


class Borrower(BaseModel):
    name: str = Field(
        ...,
        description="Nome completo do cliente, incluindo primeiro nome e sobrenome(s)",
    )
    cpf: str = Field(
        ...,
        description="CPF do cliente, apenas números, sem pontos ou traços (11 dígitos)",
    )
    birthdate: str = Field(
        ...,
        description="Data de nascimento do cliente no formato AAAA-MM-DD (exemplo: 1990-12-31)",
    )
    gender: str = Field(
        ...,
        description="Gênero do cliente: 'male' para masculino ou 'female' para feminino",
    )
    phoneNumber: str = Field(
        ...,
        description="Número de telefone celular do cliente, incluindo DDD, sem códigos ou máscaras (exemplo: 11987654321)",
    )
    email: str = Field(
        ...,
        description="Endereço de e-mail válido do cliente (exemplo: nome@dominio.com)",
    )
    maritalStatus: str = Field(
        ...,
        description="Estado civil do cliente (opções: single, married)",
    )
    nationality: str = Field(
        "brasileiro",
        description="Nacionalidade do cliente (exemplo: brazilian)",
    )
    motherName: str = Field(
        ...,
        description="Nome completo da mãe do cliente, incluindo primeiro nome e sobrenome(s)",
    )
    pep: bool = Field(
        False,
        description="Indica se o cliente é uma Pessoa Exposta Politicamente (PEP). True para sim, False para não",
    )
    naturalness: str = Field(
        "Rio de Janeiro - RJ",
        description="Cidade e estado de nascimento do cliente (exemplo: São Paulo - SP)",
    )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        # Normalizar gênero
        gender_map = {
            "M": "male",
            "F": "female",
            "MALE": "male",
            "FEMALE": "female",
        }
        if "gender" in data:
            data["gender"] = gender_map.get(data["gender"].upper(), data["gender"])

        # Normalizar CPF
        if "cpf" in data:
            data["cpf"] = data["cpf"].replace(".", "").replace("-", "")

        return cls(**data)


class Document(BaseModel):
    type: str = Field(
        ...,
        description="Tipo de documento de identificação do cliente. Deve ser 'cnh' para Carteira Nacional de Habilitação ou 'rg' para Registro Geral",
    )
    number: str = Field(
        ..., description="Número do documento de identificação, sem pontos ou traços"
    )
    issuingState: str = Field(
        ...,
        description="Sigla do estado brasileiro que emitiu o documento (exemplo: SP, RJ, MG)",
    )
    issuingAuthority: str = Field(
        ..., description="Órgão emissor do documento (exemplo: SSP, DETRAN)"
    )
    issueDate: str = Field(
        ...,
        description="Data de emissão do documento no formato AAAA-MM-DD (exemplo: 2015-06-30)",
    )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)


class Address(BaseModel):
    zipCode: str = Field(
        ...,
        description="CEP do endereço do cliente, apenas números, sem hífen (8 dígitos)",
    )
    street: str = Field(
        ..., description="Nome da rua, avenida, ou logradouro do endereço do cliente"
    )
    number: str = Field(
        ..., description="Número do endereço. Use 'S/N' se não houver número"
    )
    neighborhood: str = Field(..., description="Nome do bairro onde o cliente reside")
    city: str = Field(..., description="Nome completo da cidade onde o cliente reside")
    state: str = Field(
        ...,
        description="Sigla do estado brasileiro onde o cliente reside (exemplo: SP, RJ, MG)",
    )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)


class DisbursementBankAccount(BaseModel):
    bankCode: str = Field(
        ...,
        description="Código numérico do banco onde o cliente possui conta (3 dígitos)",
    )
    accountType: str = Field(
        ...,
        description="Tipo de conta bancária. Deve ser 'corrente' para conta corrente ou 'poupanca' para conta poupança",
    )
    accountNumber: str = Field(
        ..., description="Número da conta bancária do cliente, sem o dígito verificador"
    )
    accountDigit: str = Field(
        ..., description="Dígito verificador da conta bancária do cliente"
    )
    branchNumber: str = Field(
        ...,
        description="Número da agência bancária, sem o dígito verificador (se houver)",
    )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)


class SendProposalInput(BaseModel):
    feeScheduleId: int = Field(
        ..., description="ID numérico da tabela de taxas a ser utilizada na proposta"
    )
    financialId: str = Field(
        ...,
        description="ID único retornado pela simulação de crédito prévia, necessário para vincular a proposta à simulação",
    )
    borrower: Borrower = Field(
        ...,
        description="Objeto contendo todas as informações pessoais do cliente necessárias para a proposta",
    )
    document: Document = Field(
        ...,
        description="Objeto contendo as informações do documento de identificação do cliente",
    )
    address: Address = Field(
        ...,
        description="Objeto contendo as informações de endereço residencial do cliente",
    )
    disbursementBankAccount: DisbursementBankAccount = Field(
        ...,
        description="Objeto contendo as informações da conta bancária do cliente para recebimento do FGTS",
    )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            feeScheduleId=data["feeScheduleId"],
            financialId=data["financialId"],
            borrower=Borrower.from_dict(data["borrower"]),
            document=Document.from_dict(data["document"]),
            address=Address.from_dict(data["address"]),
            disbursementBankAccount=DisbursementBankAccount.from_dict(
                data["disbursementBankAccount"]
            ),
        )
