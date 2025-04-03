from .base import BankSimulator, SimulationResult, BankInfo
from apis import FactaApi
import logging

logger = logging.getLogger(__name__)


class FactaBankSimulator(BankSimulator):
    def __init__(self):
        self.client = FactaApi()

    @property
    def bank_name(self) -> str:
        return "FACTA"

    @property
    def bank_info(self) -> BankInfo:
        return BankInfo(
            code="FACTA",
            name="Banco Facta",
            description="Antecipação de FGTS com condições especiais",
            logo_url="/static/banks/facta-logo.png",
            active=True,
        )

    async def simulate(self, cpf: str) -> SimulationResult:
        try:
            # Primeiro checa base offline
            offline_result = await self.client.consultar_base_offline(cpf)

            if "erro" in offline_result and offline_result.get("erro"):
                return SimulationResult(
                    bank_name=self.bank_name,
                    error_message=offline_result.get(
                        "mensagem", "CPF não autorizado na base offline"
                    ),
                    success=False,
                    raw_response=offline_result,
                )

            # Consulta saldo FGTS
            saldo_result = await self.client.consultar_saldo_fgts(cpf)

            if "erro" in saldo_result and saldo_result.get("erro"):
                return SimulationResult(
                    bank_name=self.bank_name,
                    error_message=saldo_result.get(
                        "mensagem", "Erro ao consultar saldo FGTS"
                    ),
                    success=False,
                    raw_response=saldo_result,
                )

            # Simular valor
            parcelas_payload = self.client.criar_payload_parcelas(saldo_result)
            simulation_result = await self.client.simular_valor_fgts(
                cpf, parcelas_payload
            )

            if "erro" in simulation_result and simulation_result.get("erro"):
                return SimulationResult(
                    bank_name=self.bank_name,
                    error_message=simulation_result.get(
                        "mensagem", "Erro na simulação"
                    ),
                    success=False,
                    raw_response=simulation_result,
                )

            # transformo aqui a string em int pra transformar em float...
            valor_liquido_str = simulation_result.get("valor_liquido")
            if isinstance(valor_liquido_str, str):
                valor_liquido_str = valor_liquido_str.replace(".", "").replace(",", ".")

            valor_liquido = float(valor_liquido_str)

            return SimulationResult(
                bank_name=self.bank_name,
                available_amount=float(valor_liquido),
                success=True,
                raw_response=simulation_result,
            )

        except Exception as e:
            logger.error(f"Erro na simulação Facta: {str(e)}")
            return SimulationResult(
                bank_name=self.bank_name,
                error_message=str(e),
                success=False,
                raw_response={"error": str(e)},
            )
