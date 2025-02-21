import os
import requests


class InApiClient:
    def __init__(self):
        self.base_url = "https://inapi.digital/api/check/consult"

    def get_in_100(self, cpf: str, benefit: str):
        in_api_token = os.getenv("INAPI_TOKEN")
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + in_api_token,
        }

        params = (
            ("cpf", cpf),
            ("benefit", benefit),
            ("with_loans", True),
        )

        response = requests.get(
            "https://inapi.digital/api/check/consult", headers=headers, params=params
        )

        if response.status_code == 200:
            json = response.json()

            if json["error"] is False:
                return json["payload"]
            else:
                return None

        else:
            return None
