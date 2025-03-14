from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException

from services.bmg.repository.mongo_db import BMGMongoRepository
from apis import BmgApiClient, OfferRequest, CustomerFirstStep


class FirstStepRequest(BaseModel):
    cpf: str
    name: str
    birthdate: datetime
    gender: str
    legal_representative: bool = False


class SecondStepRequest(BaseModel):
    customer_id: str


class CardService:
    def __init__(self):
        self.collection = "cards"

    async def first_step(self, data: FirstStepRequest):
        repository = BMGMongoRepository()

        user_data = repository.get_from_collection_by_cpf(self.collection, data.cpf)

        if not user_data:
            user_data = repository.add_to_collection(self.collection, data.model_dump())

        return user_data

    async def second_step(self, data: SecondStepRequest):
        repository = BMGMongoRepository()

        user_data = repository.get_from_collection_by_id(
            self.collection, data.customer_id
        )

        if not user_data or "in100" not in user_data:
            raise HTTPException(
                status_code=400,
                detail="Não foi possivel obter dados do cartão",
            )

        in100_data = user_data["in100"]["consulta"]
        bmg_client = BmgApiClient()
        income_value = Decimal(in100_data["valorComprometido"]) + Decimal(
            in100_data["valorLiquido"]
        )
        customer_data = CustomerFirstStep(
            city_of_birth=user_data["city"],
            cpf=user_data["cpf"],
            birthdate=user_data["birthdate"],
            name=user_data["name"],
            state_of_birth=user_data["state"],
        )
        form_data = OfferRequest(
            bank_code=in100_data["cbcIfPagadora"],
            bank_agency=in100_data["agenciaPagadora"],
            bank_account=in100_data["contaCorrente"][:-1],
            bank_account_digit=in100_data["contaCorrente"][-1],
            customer=customer_data,
            benefit=user_data["benefit"],
            benefit_type=in100_data["especie"],
            card_avaiable_margin=in100_data["margemDisponivelCartao"],
            uf_benefit=in100_data["ufPagamento"],
            income_value=income_value,
        )

        offer = bmg_client.get_card_offer(form_data)

        return offer
