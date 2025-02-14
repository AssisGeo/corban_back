from .base import BankSimulator, SimulationResult, BankInfo
import aiohttp
import os
import logging

logger = logging.getLogger(__name__)


class QIBankSimulator(BankSimulator):
    @property
    def bank_name(self) -> str:
        return "QI"

    @property
    def bank_info(self) -> BankInfo:
        return BankInfo(
            code="QI",
            name="QI Sociedade de Crédito Direto",
            description="Antecipação de FGTS com as melhores taxas do mercado",
            logo_url="/static/banks/qi-logo.png",
            active=True,
        )

    async def simulate(self, cpf: str) -> SimulationResult:
        try:
            token = await self._authenticate()
            simulation_data = {"clientCpf": cpf, "feeScheduleId": 0}

            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {token}"}
                async with session.post(
                    f"{os.getenv('VCTEX_API_URL')}/service/simulation",
                    json=simulation_data,
                    headers=headers,
                    proxy=os.getenv("PROXY_URL"),
                ) as response:
                    result = await response.json()

            if "data" in result and "simulationData" in result["data"]:
                simulation_data = result["data"]["simulationData"]
                return SimulationResult(
                    bank_name=self.bank_name,
                    available_amount=simulation_data.get("totalReleasedAmount"),
                    success=True,
                    raw_response=result,
                )

            return SimulationResult(
                bank_name=self.bank_name,
                error_message=result.get("message", "Simulação falhou"),
                success=False,
                raw_response=result,
            )

        except Exception as e:
            logger.error(f"Erro na simulação QI Bank: {str(e)}")
            return SimulationResult(
                bank_name=self.bank_name,
                error_message=str(e),
                success=False,
                raw_response={"error": str(e)},
            )

    async def _authenticate(self) -> str:
        async with aiohttp.ClientSession() as session:
            data = {"cpf": os.getenv("CPF"), "password": os.getenv("PASSWORD")}
            async with session.post(
                f"{os.getenv('VCTEX_API_URL')}/authentication/login",
                json=data,
                proxy=os.getenv("PROXY_URL"),
            ) as response:
                result = await response.json()
                return result["token"]["accessToken"]
