from pydantic import BaseModel, Field
from models.vctex.models import Borrower, Document, Address, DisbursementBankAccount


class SimulationRequest(BaseModel):
    cpf: str = Field(..., description="CPF do cliente para simulação")
    fee_schedule_id: int = Field(default=0, description="ID da tabela de taxas")


class ProposalRequest(BaseModel):
    financialId: str = Field(..., description="ID financeiro retornado pela simulação")
    borrower: Borrower
    document: Document
    address: Address
    disbursementBankAccount: DisbursementBankAccount


class ProposalResponse(BaseModel):
    contract_number: str
    status: str
    message: str


class ContractRequest(BaseModel):
    contract_number: str
