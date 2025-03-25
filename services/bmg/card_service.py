from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException

from services.bmg.repository.mongo_db import BMGMongoRepository
from apis import (
    BmgApiClient,
    OfferRequest,
    CustomerFirstStep,
    Customer,
    SaveProposalRequest,
)


class FirstStepRequest(BaseModel):
    cpf: str
    name: str
    birthdate: datetime
    legal_representative: bool = False


class SecondStepRequest(BaseModel):
    customer_id: str


class ThirdStepRequest(BaseModel):
    customer_id: str
    customer: Customer


class FourthStepRequest(BaseModel):
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
            bank_account=(
                "3054258"
                if not in100_data["contaCorrente"]
                else in100_data["contaCorrente"][:-1]
            ),
            bank_account_digit=(
                "1"
                if not in100_data["contaCorrente"]
                else in100_data["contaCorrente"][-1]
            ),
            customer=customer_data,
            benefit=user_data["benefit"],
            benefit_type=in100_data["especie"],
            card_avaiable_margin=in100_data["margemDisponivelCartao"],
            uf_benefit=in100_data["ufPagamento"],
            income_value=income_value,
        )

        offer = bmg_client.get_card_offer(form_data)

        return offer

    async def third_step(self, data: ThirdStepRequest):
        repository = BMGMongoRepository()

        user_data = repository.get_from_collection_by_id(
            self.collection, data.customer_id
        )

        if not user_data:
            HTTPException(
                status_code=400,
                detail="Cliente não encontrado",
            )

        customer_data = data.model_dump()

        data_to_update = {
            **customer_data["customer"],
        }

        updated_data = repository.update_in_collection_by_id(
            self.collection,
            user_data["id"],
            data=data_to_update,
        )

        return updated_data

    async def fourth_step(self, data: ThirdStepRequest):
        repository = BMGMongoRepository()

        user_data = repository.get_from_collection_by_id(
            self.collection, data.customer_id
        )

        if not user_data:
            HTTPException(
                status_code=400,
                detail="Cliente não encontrado",
            )

        if "in100" not in user_data:
            HTTPException(
                status_code=400,
                detail="Dados do in100 nao encontrados",
            )

        in100_data = user_data["in100"]["consulta"]
        income_value = Decimal(in100_data["valorComprometido"]) + Decimal(
            in100_data["valorLiquido"]
        )
        proposal_data = SaveProposalRequest(
            bank_num=in100_data["cbcIfPagadora"],
            agency={
                "number": in100_data["agenciaPagadora"],
                "secure_digit": "",
            },
            account={
                "number": in100_data["contaCorrente"][:-1],
                "secure_digit": in100_data["contaCorrente"][-1],
            },
            banco_ordem_pagamento=in100_data["cbcIfPagadora"],
            customer={
                "cellphone": user_data["cellphone"],
                "phone": user_data["phone"],
                "city_of_birth": user_data["city_of_birth"],
                "cpf": user_data["cpf"],
                "birthdate": user_data["birthdate"],
                "email": user_data["email"],
                "address": user_data["address"],
                "marital_status": user_data["marital_status"],
                "educational_level": user_data["educational_level"],
                "identity_document": user_data["identity_document"],
                "nationality": user_data["nationality"],
                "name": user_data["name"],
                "spouse_name": user_data["spouse_name"],
                "mother_name": user_data["mother_name"],
                "father_name": user_data["father_name"],
                "ppe": user_data["ppe"],
                "gender": user_data["gender"],
                "state_of_birth": user_data["state_of_birth"],
            },
            finalidade_credito=1,
            income_date=datetime.now(),
            margin=in100_data["margemDisponivelRcc"],
            benefit=user_data["benefit"],
            benefit_type=in100_data["especie"],
            uf_benefit=in100_data["ufPagamento"],
            income_value=income_value,
        )
        bmg_client = BmgApiClient()
        proposal_number = bmg_client.save_benefit_card_proposal(proposal_data)

        updated_data = repository.update_in_collection_by_id(
            self.collection,
            user_data["id"],
            data={"proposal_number": proposal_number},
        )

        return updated_data
