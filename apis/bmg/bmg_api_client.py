import requests
import os

from apis.bmg.payloads.in100.request_in100 import (
    generate_request_in100_payload,
    In100Request,
)
from apis.helpers.xml_to_dict import xml_to_dict


class BmgApiClient:
    def __init__(self):
        self.base_url = "https://ws1.bmgconsig.com.br/webservices"
        self.login = os.getenv("BMG_BOT_LOGIN")
        self.password = os.getenv("BMG_BOT_PASSWORD")

    def request_in100(self, data: In100Request):
        headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "add"}
        # proxies = {
        #     # "http": "http://77.37.40.109:3128/",
        #     "https": "https://77.37.40.109:3129/",
        # }

        payload = generate_request_in100_payload(data, self.login, self.password)
        endpoint = f"{self.base_url}/ConsultaMargemIN100?wsdl"
        response = requests.post(endpoint, headers=headers, data=payload)

        if response.status_code == 200:
            print(response.text)
            body_data = xml_to_dict(response.text)
            print(body_data)

        else:
            print(response.text)
            return response.text
