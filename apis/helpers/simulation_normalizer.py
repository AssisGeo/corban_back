from typing import Dict, Any, List


class SimulationNormalizer:
    @staticmethod
    def normalize_simulation_results(
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Normaliza os resultados de simulação de diferentes bancos para um formato padrão.

        Args:
            results: Lista de resultados de simulação de diferentes bancos

        Returns:
            Lista de resultados normalizados
        """
        normalized_results = []

        for result in results:
            normalized = result.copy()

            # Normaliza o ID da simulação (financialId)
            normalized["financialId"] = SimulationNormalizer._extract_financial_id(
                result
            )

            # Normaliza o valor disponível
            if "available_amount" in normalized:
                normalized["available_amount"] = float(normalized["available_amount"])

            # Assegura que o valor da simulação esteja no mesmo formato para todos os bancos
            raw_response = result.get("raw_response", {})

            # Adiciona campos normalizados dentro de um objeto 'normalized_data'
            normalized["normalized_data"] = {
                "bank_name": result.get("bank_name", ""),
                "financial_id": SimulationNormalizer._extract_financial_id(result),
                "available_amount": float(result.get("available_amount", 0)),
                "total_amount": SimulationNormalizer._extract_total_amount(
                    raw_response
                ),
                "interest_rate": SimulationNormalizer._extract_interest_rate(
                    raw_response
                ),
                "installments": SimulationNormalizer._extract_installments(
                    raw_response
                ),
            }

            normalized_results.append(normalized)

        return normalized_results

    @staticmethod
    def _extract_financial_id(result: Dict[str, Any]) -> str:
        """Extrai o ID da simulação de diferentes formatos de banco"""
        raw_response = result.get("raw_response", {})
        bank_name = result.get("bank_name", "")

        if bank_name == "QI":
            return raw_response.get("data", {}).get("financialId", "")
        elif bank_name == "VCTEX":
            return raw_response.get("financialId", "")
        elif bank_name == "FACTA":
            return f"facta_{raw_response.get('simulacao_fgts', '')}"

        # Busca genérica para outros bancos
        return (
            raw_response.get("financialId", "")
            or raw_response.get("data", {}).get("financialId", "")
            or raw_response.get("simulacao_fgts", "")
            or ""
        )

    @staticmethod
    def _extract_total_amount(raw_response: Dict[str, Any]) -> float:
        """Extrai o valor total a ser pago da simulação"""
        # Tenta extrair de diferentes formatos
        total = None

        # VCTEX
        if "total_to_pay" in raw_response:
            total = raw_response["total_to_pay"]
        # QI
        elif "data" in raw_response and "simulationData" in raw_response["data"]:
            total = raw_response["data"]["simulationData"].get("totalAmount")

        # Converte para float se for string
        if isinstance(total, str):
            total = total.replace(".", "").replace(",", ".")

        return float(total) if total is not None else 0.0

    @staticmethod
    def _extract_interest_rate(raw_response: Dict[str, Any]) -> float:
        """Extrai a taxa de juros da simulação"""
        # Tenta extrair de diferentes formatos
        rate = None

        # VCTEX
        if "interest_rate" in raw_response:
            rate_str = raw_response["interest_rate"]
            if isinstance(rate_str, str) and "%" in rate_str:
                rate = rate_str.replace("%", "")
        # QI
        elif "data" in raw_response and "simulationData" in raw_response["data"]:
            rate = raw_response["data"]["simulationData"].get("contractRate")
            if rate is not None:
                rate = rate * 100  # Convertendo de decimal para percentual
        # FACTA
        elif "taxa" in raw_response:
            rate = raw_response["taxa"]

        # Converte para float se for string
        if isinstance(rate, str):
            rate = rate.replace(",", ".")

        return float(rate) if rate is not None else 0.0

    @staticmethod
    def _extract_installments(raw_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrai as parcelas da simulação"""
        installments = []

        # QI
        if "data" in raw_response and "simulationData" in raw_response["data"]:
            sim_data = raw_response["data"]["simulationData"]
            if "installments" in sim_data and isinstance(
                sim_data["installments"], list
            ):
                return sim_data["installments"]

        return installments
