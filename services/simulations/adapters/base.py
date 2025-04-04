from abc import ABC, abstractmethod
from models.normalized.simulation import NormalizedSimulationResponse
from models.normalized.proposal import NormalizedProposalRequest


class BankAdapter(ABC):
    @property
    @abstractmethod
    def bank_name(self) -> str:
        pass

    @abstractmethod
    def normalize_simulation_response(
        self, raw_response: dict
    ) -> NormalizedSimulationResponse:
        """Converte a resposta bruta do banco para o formato normalizado"""
        pass

    @abstractmethod
    def prepare_proposal_request(
        self, normalized_request: NormalizedProposalRequest
    ) -> dict:
        """Converte o pedido de proposta normalizado para o formato esperado pelo banco"""
        pass
