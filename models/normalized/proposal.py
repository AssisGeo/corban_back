from pydantic import BaseModel
from typing import Optional


class CustomerInfo(BaseModel):
    name: str
    cpf: str
    birth_date: str
    gender: str
    phone: str
    email: Optional[str] = None
    mother_name: str


class DocumentInfo(BaseModel):
    type: str
    number: str
    issuing_date: str
    issuing_authority: str
    issuing_state: str


class AddressInfo(BaseModel):
    zip_code: str
    street: str
    number: str
    neighborhood: str
    city: str
    state: str
    complement: Optional[str] = None


class BankInfo(BaseModel):
    bank_code: str
    branch_number: str
    account_number: str
    account_digit: str
    account_type: str


class NormalizedProposalRequest(BaseModel):
    financial_id: str
    customer: CustomerInfo
    document: DocumentInfo
    address: AddressInfo
    bank_data: BankInfo
