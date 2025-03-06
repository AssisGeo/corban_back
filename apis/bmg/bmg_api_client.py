import os
from fastapi import HTTPException

from apis.bmg.payloads.in100.request_in100 import (
    generate_request_in100_payload,
    In100Request,
)
from apis.bmg.payloads.in100.in100_consult_filter import (
    build_in100_consult_filter,
    In100ConsultFilter,
)
from apis.bmg.payloads.benefit_card.save_proposal import (
    build_save_benefit_card_proposal_payload,
    SaveProposalRequest,
)
from apis.helpers.xml_to_dict import xml_to_dict
import http.client


class BmgApiClient:
    def __init__(self):
        self.base_url = "https://ws1.bmgconsig.com.br/webservices"
        self.login = os.getenv("BMG_BOT_LOGIN")
        self.password = os.getenv("BMG_BOT_PASSWORD")
        self.login_consig = os.getenv("BMG_CONSIG_LOGIN")
        self.password_consig = os.getenv("BMG_CONSIG_PASSWORD")

    def request_in100(self, data: In100Request):
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
            response = response["Body"]["pesquisarResponse"]["pesquisarReturn"]

            return {"message": response}
        else:
            if "Fault" in response["Body"]:
                detail = response["Body"]["Fault"]
            else:
                detail = response["Body"]
            raise HTTPException(status_code=res.status, detail=detail)

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
