from apis import CepAPIClient


class CEPService:
    def __init__(self):
        self.client = CepAPIClient()

    async def get_address(self, cep: str):
        return await self.client.fetch_address_by_cep(cep)
