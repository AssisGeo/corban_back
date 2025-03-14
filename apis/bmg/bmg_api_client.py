import os
import re
import http.client
from fastapi import HTTPException

from services.inapi.redis_cache import add_in100_to_cache
from services.bmg.repository.mongo_db import BMGMongoRepository
from apis.bmg.payloads.in100.request_in100 import (
    generate_request_in100_payload,
    In100Request,
)
from apis.bmg.payloads.in100.in100_consult_filter import (
    build_in100_consult_filter,
    In100ConsultFilter,
)
from apis.bmg.payloads.in100.single_consult_request import (
    build_single_consult_request_payload,
    SingleConsultRequest,
)
from apis.bmg.payloads.benefit_card.get_offer import (
    build_get_offer_payload,
    OfferRequest,
)
from apis.bmg.payloads.benefit_card.save_proposal import (
    build_save_benefit_card_proposal_payload,
    SaveProposalRequest,
)
from apis.helpers.xml_to_dict import xml_to_dict


class BmgApiClient:
    def __init__(self):
        self.base_url = "https://ws1.bmgconsig.com.br/webservices"
        self.login = os.getenv("BMG_BOT_LOGIN")
        self.password = os.getenv("BMG_BOT_PASSWORD")
        self.login_consig = os.getenv("BMG_CONSIG_LOGIN")
        self.password_consig = os.getenv("BMG_CONSIG_PASSWORD")

    def request_in100(self, data: In100Request):
        repository = BMGMongoRepository()

        user_data = repository.get_from_collection_by_cpf("cards", data.cpf)

        if user_data:
            repository.update_in_collection_by_id(
                "cards", user_data["id"], data=data.model_dump()
            )
        else:
            repository.add_to_collection("cards", data)

        conn = http.client.HTTPSConnection("ws1.bmgconsig.com.br")
        payload = generate_request_in100_payload(data, self.login, self.password)
        headers = {"Content-Type": "text/xml", "SOAPAction": "add"}
        conn.request(
            "POST", "/webservices/ConsultaMargemIN100?wsdl=null", payload, headers
        )
        res = conn.getresponse()
        body = res.read()
        response = xml_to_dict(body)
        if res.status == 200:
            response = response["Body"]["inserirSolicitacaoResponse"][
                "inserirSolicitacaoReturn"
            ]
            return {"message": response}
        else:
            if "Fault" in response["Body"]:
                detail = response["Body"]["Fault"]
            else:
                detail = response["Body"]
            raise HTTPException(status_code=res.status, detail=detail)

    def single_consult_request(self, data: SingleConsultRequest):
        conn = http.client.HTTPSConnection("ws1.bmgconsig.com.br")
        payload = build_single_consult_request_payload(data, self.login, self.password)
        headers = {"Content-Type": "text/xml", "SOAPAction": "add"}
        conn.request(
            "POST", "/webservices/ConsultaMargemIN100?wsdl=null", payload, headers
        )
        res = conn.getresponse()
        body = res.read()
        response = xml_to_dict(body)
        if res.status == 200:
            response = response["Body"]["realizarConsultaAvulsaResponse"][
                "realizarConsultaAvulsaReturn"
            ]
            repository = BMGMongoRepository()
            user_data = repository.get_from_collection_by_cpf("cards", data.cpf)
            if user_data and "benefit" in user_data:
                redis_key = f"in100_bmg_{data.cpf}_{user_data['benefit']}"
                add_in100_to_cache(redis_key, response)

            return {"data": response}

        else:
            if "Fault" in response["Body"]:
                detail = response["Body"]["Fault"]
            else:
                detail = response["Body"]
            raise HTTPException(status_code=res.status, detail=detail)

    def in100_consult_filter(self, data: In100ConsultFilter):
        conn = http.client.HTTPSConnection("ws1.bmgconsig.com.br")
        payload = build_in100_consult_filter(data, self.login, self.password)
        headers = {"Content-Type": "text/xml", "SOAPAction": "add"}
        conn.request(
            "POST", "/webservices/ConsultaMargemIN100?wsdl=null", payload, headers
        )
        res = conn.getresponse()
        body = res.read()
        response = xml_to_dict(body)
        if res.status == 200:
            response = response["Body"]["pesquisarResponse"]["pesquisarReturn"][
                "pesquisarReturn"
            ]

            if isinstance(response, list):
                response = response[0]

            if response["consulta"]["agenciaPagadora"]:
                repository = BMGMongoRepository()
                user_data = repository.get_from_collection_by_cpf("cards", data.cpf)
                if user_data and "benefit" in user_data:
                    redis_key = f"in100_bmg_{data.cpf}_{user_data['benefit']}"
                    add_in100_to_cache(redis_key, response)
                return {"data": response}

            request_number = response["numeroSolicitacao"]
            token = data.token

            form_data = SingleConsultRequest(request_number=request_number, token=token)

            return self.single_consult_request(data=form_data)

        else:
            if "Fault" in response["Body"]:
                detail = response["Body"]["Fault"]
            else:
                detail = response["Body"]
            raise HTTPException(status_code=res.status, detail=detail)

    def get_card_offer(self, data: OfferRequest):
        conn = http.client.HTTPSConnection("ws1.bmgconsig.com.br")
        payload = build_get_offer_payload(data, self.login, self.password)
        headers = {"Content-Type": "text/xml", "SOAPAction": "add"}
        conn.request("POST", "/webservices/CartaoBeneficio?wsdl=null", payload, headers)
        res = conn.getresponse()
        body = res.read()
        response = xml_to_dict(body)
        if res.status == 200:
            response: str = response["Body"]["geraScriptResponse"]["geraScriptReturn"]

            splited_response = response.split("||")
            card_data = [
                text for text in splited_response if "Limite de crédito" in text
            ]
            if card_data:
                pattern = r"R\$\s*([\d.]+,\d{2})(?=[^\d]|$)"
                matches: list[str] = re.findall(pattern, card_data[0])
                print(matches)
                values = [match.replace(".", "").replace(",", ".") for match in matches]
                print(values)
                if values:
                    simulation_data = {
                        "card_simulation": {
                            "limit": values[0],
                            "withdrawal_limit": (0 if len(values) <= 1 else values[1]),
                        }
                    }

                    repository = BMGMongoRepository()

                    user_data = repository.get_from_collection_by_cpf(
                        "cards", data.customer.cpf
                    )
                    if user_data:
                        response = repository.update_in_collection_by_id(
                            "cards", user_data["id"], data=simulation_data
                        )

                    return {"data": response}

                else:
                    return HTTPException(
                        status_code=400,
                        detail={
                            "data": "Não foi possivel extrair dados do cartão a partir do texto retornado. Consulte o administrador do sistema."
                        },
                    )

            return HTTPException(
                status_code=400,
                detail={"data": "Não foi possivel obter dados do cartão"},
            )

        else:
            repository = BMGMongoRepository()

            user_data = repository.get_from_collection_by_cpf(
                "cards", data.customer.cpf
            )
            if user_data:
                simulation_data = {
                    "card_simulation": {
                        "limit": 0,
                        "withdrawal_limit": 0,
                    }
                }
                response = repository.update_in_collection_by_id(
                    "cards", user_data["id"], data=simulation_data
                )

            return {"data": response}

    def save_benefit_card_proposal(self, data: SaveProposalRequest):
        conn = http.client.HTTPSConnection("ws1.bmgconsig.com.br")
        payload = build_save_benefit_card_proposal_payload(
            data, self.login, self.password, self.login_consig, self.password_consig
        )
        headers = {"Content-Type": "text/xml", "SOAPAction": "add"}
        conn.request("POST", "/webservices/CartaoBeneficio?wsdl=null", payload, headers)
        res = conn.getresponse()
        body = res.read()
        response = xml_to_dict(body)
        if res.status == 200:
            response = response["Body"]["gravarPropostaCartaoResponse"][
                "gravarPropostaCartaoReturn"
            ]
            return {"message": response}
        else:
            if "Fault" in response["Body"]:
                detail = response["Body"]["Fault"]
            else:
                detail = response["Body"]
            raise HTTPException(status_code=res.status, detail=detail)
