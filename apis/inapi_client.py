import os
import requests
from services.inapi.redis_cache import get_in100_from_cache, add_in100_to_cache


class InApiClient:
    def __init__(self):
        self.base_url = "https://inapi.digital/api/check/consult"

    def get_in_100(self, cpf: str, benefit: str):
        redis_key = f"in100_{cpf}_{benefit}"
        cached_in100 = get_in100_from_cache(redis_key)
        if cached_in100 is not None:
            return cached_in100
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
                add_in100_to_cache(redis_key, json["payload"])
                return json["payload"]
            else:
                return None

        else:
            return None
