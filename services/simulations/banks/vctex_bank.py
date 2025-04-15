from .base import BankSimulator, SimulationResult, BankInfo
import logging
from apis.vctex_api_client import VCTEXAPIClient
from aiohttp import ClientTimeout

logger = logging.getLogger(__name__)


class VCTEXBankSimulator(BankSimulator):
    def __init__(self):
        self.client = VCTEXAPIClient()
        self.timeout = ClientTimeout(total=90)

    @property
    def bank_name(self) -> str:
        return "VCTEX"

    @property
    def bank_info(self) -> BankInfo:
        return BankInfo(
            code="VCTEX",
            name="VCTEX Bank",
            description="Antecipação de FGTS VCTEX",
            logo_url="/static/banks/vctex-logo.png",
            active=True,
        )

    async def simulate(self, cpf: str, table_id: str = None) -> SimulationResult:
        try:

            fee_schedule_id = 0
            if table_id is not None:
                try:
                    fee_schedule_id = int(table_id)
                except ValueError:
                    logger.warning(
                        f"Valor de tabela inválido para VCTEX: {table_id}, usando 0"
                    )

            simulation_data = {
                "clientCpf": cpf,
                "feeScheduleId": fee_schedule_id,
            }

            # Realizar a simulação usando o cliente VCTEX
            result = await self.client.simulate_credit(simulation_data)

            # Verificar se há erro na resposta
            if isinstance(result, dict):
                if result.get("statusCode", 0) >= 400:
                    error_msg = result.get("message", "Simulação falhou")
                    logger.error(f"Erro na simulação VCTEX: {error_msg}")
                    return SimulationResult(
                        bank_name=self.bank_name,
                        error_message=error_msg,
                        success=False,
                        raw_response=result,
                    )

                if "total_released" in result:
                    try:
                        amount = float(result["total_released"])
                        return SimulationResult(
                            bank_name=self.bank_name,
                            available_amount=amount,
                            success=True,
                            raw_response=result,
                        )
                    except (ValueError, AttributeError) as e:
                        logger.error(f"Erro ao converter valor: {e}")
                        return SimulationResult(
                            bank_name=self.bank_name,
                            error_message="Erro ao processar valor disponível",
                            success=False,
                            raw_response=result,
                        )

            return SimulationResult(
                bank_name=self.bank_name,
                error_message="Formato de resposta inválido",
                success=False,
                raw_response=result,
            )

        except Exception as e:
            logger.error(f"Erro na simulação VCTEX: {str(e)}")
            return SimulationResult(
                bank_name=self.bank_name,
                error_message=str(e),
                success=False,
                raw_response={"error": str(e)},
            )
