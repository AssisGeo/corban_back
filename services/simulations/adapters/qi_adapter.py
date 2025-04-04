from .base import BankAdapter
from models.normalized.simulation import NormalizedSimulationResponse
from models.normalized.proposal import NormalizedProposalRequest


class QIBankAdapter(BankAdapter):
    @property
    def bank_name(self) -> str:
        return "QI"

    def normalize_simulation_response(
        self, raw_response: dict
    ) -> NormalizedSimulationResponse:
        data = raw_response.get("data", {}).get("simulationData", {})

        return NormalizedSimulationResponse(
            bank_name=self.bank_name,
            financial_id=raw_response.get("data", {}).get("financialId", ""),
            available_amount=data.get("totalReleasedAmount", 0),
            total_amount=data.get("totalAmount", 0),
            interest_rate=(
                data.get("contractRate", 0) * 100 if data.get("contractRate") else 0
            ),
            iof_amount=data.get("iofAmount", 0),
            raw_response=raw_response,
        )

    def prepare_proposal_request(
        self, normalized_request: NormalizedProposalRequest
    ) -> dict:
        return {
            "financialId": normalized_request.financial_id,
            "borrower": {
                "name": normalized_request.customer.name,
                "cpf": normalized_request.customer.cpf,
                "birthdate": normalized_request.customer.birth_date,
                "gender": (
                    "male"
                    if normalized_request.customer.gender.upper() in ["M", "MALE"]
                    else "female"
                ),
                "phoneNumber": normalized_request.customer.phone,
                "email": normalized_request.customer.email,
                "motherName": normalized_request.customer.mother_name,
            },
            "document": {
                "type": normalized_request.document.type.lower(),
                "number": normalized_request.document.number,
                "issuingState": normalized_request.document.issuing_state,
                "issuingAuthority": normalized_request.document.issuing_authority,
                "issueDate": normalized_request.document.issuing_date,
            },
            "address": {
                "zipCode": normalized_request.address.zip_code,
                "street": normalized_request.address.street,
                "number": normalized_request.address.number,
                "neighborhood": normalized_request.address.neighborhood,
                "city": normalized_request.address.city,
                "state": normalized_request.address.state,
                "complement": (
                    normalized_request.address.complement
                    if hasattr(normalized_request.address, "complement")
                    else ""
                ),
            },
            "disbursementBankAccount": {
                "bankCode": normalized_request.bank_data.bank_code,
                "branchNumber": normalized_request.bank_data.branch_number,
                "accountNumber": normalized_request.bank_data.account_number,
                "accountDigit": normalized_request.bank_data.account_digit,
                "accountType": normalized_request.bank_data.account_type,
            },
        }
