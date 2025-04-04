from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel
from datetime import datetime
from models.vctex.models import SendProposalInput


class BankInfo(BaseModel):
    """Informações sobre o banco disponível para simulação"""

    code: str
    name: str
    description: str
    logo_url: str | None = None
    active: bool = True
    updated_at: datetime = datetime.utcnow()


class SimulationResult(BaseModel):
    """Modelo padronizado para resultado de simulações"""

    bank_name: str
    available_amount: float | None = None
    error_message: str | None = None
    success: bool
    raw_response: Dict[str, Any]
    timestamp: datetime = datetime.utcnow()


class BankSimulator(ABC):
    """Interface base para implementações de simulação de bancos"""

    @property
    @abstractmethod
    def bank_name(self) -> str:
        """Nome identificador do banco"""
        pass

    @property
    @abstractmethod
    def bank_info(self) -> BankInfo:
        """Informações do banco"""
        pass

    @abstractmethod
    async def simulate(self, cpf: str) -> SimulationResult:
        """Realiza simulação de FGTS para o banco específico"""
        pass


class ProposalResult(BaseModel):
    """Modelo padronizado para resultado de propostas"""

    bank_name: str
    contract_number: str = ""
    formalization_link: str = ""
    error_message: str | None = None
    success: bool
    raw_response: Dict[str, Any]
    timestamp: datetime = datetime.utcnow()


class BankProposal(ABC):
    """Interface base para implementações de propostas de bancos"""

    @property
    @abstractmethod
    def bank_name(self) -> str:
        """Nome identificador do banco"""
        pass

    @abstractmethod
    async def submit_proposal(self, proposal_data: SendProposalInput) -> ProposalResult:
        """Envia proposta para o banco específico"""
        pass

    @abstractmethod
    async def check_status(self, contract_number: str) -> Dict[str, Any]:
        """Verifica o status da proposta"""
        pass
