from typing import Any, Dict


def format_simulation_response(simulation_data: Dict[str, Any]) -> Dict[str, Any]:
    simulation = simulation_data.get("data", {}).get("simulationData", {})
    financialId = simulation_data.get("data", {}).get("financialId", None)
    total_released = simulation.get("totalReleasedAmount", 0)
    total_amount = simulation.get("totalAmount", 0)
    contract_rate = simulation.get("contractRate", 0)
    iof_amount = simulation.get("iofAmount", 0)

    response = {
        "total_released": f"{total_released:.2f}",
        "total_to_pay": f"{total_amount:.2f}",
        "interest_rate": f"{contract_rate*100:.2f}%",
        "iof_fee": f"{iof_amount:.2f}.",
        "financialId": str(financialId),
    }
    return response
