from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException
from math import ceil
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
            raise HTTPException(
                status_code=400,
                detail="Cliente não encontrado",
            )

        customer_data = data.model_dump()

        data_to_update = {
            **customer_data["customer"],
        }

        missing_bank_info = True
        if "in100" in user_data and user_data["in100"]["consulta"]:
            in100_data = user_data["in100"]["consulta"]
            if in100_data.get("contaCorrente"):
                missing_bank_info = False

        if missing_bank_info and "bank_data" in customer_data["customer"]:
            bank_info = customer_data["customer"]["bank_data"]

            if "in100" in user_data:
                redis_key = f"in100_bmg_{user_data['cpf']}_{user_data['benefit']}"
                in100_data = user_data["in100"]

                if "consulta" in in100_data:
                    in100_data["consulta"]["cbcIfPagadora"] = bank_info.get("bankCode")
                    in100_data["consulta"]["agenciaPagadora"] = bank_info.get(
                        "branchNumber"
                    )
                    in100_data["consulta"][
                        "contaCorrente"
                    ] = f"{bank_info.get('accountNumber')}{bank_info.get('accountDigit')}"

                    from services.inapi.redis_cache import add_in100_to_cache

                    add_in100_to_cache(redis_key, in100_data)

        updated_data = repository.update_in_collection_by_id(
            self.collection,
            user_data["id"],
            data=data_to_update,
        )

        return updated_data

    # async def fourth_step(self, data: ThirdStepRequest):
    #     repository = BMGMongoRepository()

    #     user_data = repository.get_from_collection_by_id(
    #         self.collection, data.customer_id
    #     )

    #     if not user_data:
    #         HTTPException(
    #             status_code=400,
    #             detail="Cliente não encontrado",
    #         )

    #     if "in100" not in user_data:
    #         HTTPException(
    #             status_code=400,
    #             detail="Dados do in100 nao encontrados",
    #         )

    #     in100_data = user_data["in100"]["consulta"]
    #     income_value = Decimal(in100_data["valorComprometido"]) + Decimal(
    #         in100_data["valorLiquido"]
    #     )
    #     proposal_data = SaveProposalRequest(
    #         bank_num=in100_data["cbcIfPagadora"],
    #         agency={
    #             "number": in100_data["agenciaPagadora"],
    #             "secure_digit": "",
    #         },
    #         account={
    #             "number": in100_data["contaCorrente"][:-1],
    #             "secure_digit": in100_data["contaCorrente"][-1],
    #         },
    #         banco_ordem_pagamento=in100_data["cbcIfPagadora"],
    #         customer={
    #             "cellphone": user_data["cellphone"],
    #             "phone": user_data["phone"],
    #             "city_of_birth": user_data["city_of_birth"],
    #             "cpf": user_data["cpf"],
    #             "birthdate": user_data["birthdate"],
    #             "email": user_data["email"],
    #             "address": user_data["address"],
    #             "marital_status": user_data["marital_status"],
    #             "educational_level": user_data["educational_level"],
    #             "identity_document": user_data["identity_document"],
    #             "nationality": user_data["nationality"],
    #             "name": user_data["name"],
    #             "spouse_name": user_data["spouse_name"],
    #             "mother_name": user_data["mother_name"],
    #             "father_name": user_data["father_name"],
    #             "ppe": user_data["ppe"],
    #             "gender": user_data["gender"],
    #             "state_of_birth": user_data["state_of_birth"],
    #         },
    #         finalidade_credito=1,
    #         income_date=datetime.now(),
    #         margin=in100_data["margemDisponivelRcc"],
    #         benefit=user_data["benefit"],
    #         benefit_type=in100_data["especie"],
    #         uf_benefit=in100_data["ufPagamento"],
    #         income_value=income_value,
    #     )
    #     bmg_client = BmgApiClient()
    #     proposal_number = bmg_client.save_benefit_card_proposal(proposal_data)

    #     updated_data = repository.update_in_collection_by_id(
    #         self.collection,
    #         user_data["id"],
    #         data={"proposal_number": proposal_number},
    #     )

    #     return updated_data

    async def fourth_step(self, data: FourthStepRequest):
        repository = BMGMongoRepository()

        user_data = repository.get_from_collection_by_id(
            self.collection, data.customer_id
        )

        if not user_data:
            raise HTTPException(
                status_code=400,
                detail="Cliente não encontrado",
            )
        if "in100" not in user_data:
            raise HTTPException(
                status_code=400,
                detail="Dados do in100 não encontrados",
            )

        in100_data = user_data["in100"]["consulta"]
        income_value = Decimal(in100_data["valorComprometido"]) + Decimal(
            in100_data["valorLiquido"]
        )

        if not in100_data.get("contaCorrente"):
            raise HTTPException(
                status_code=400,
                detail="Informações bancárias não disponíveis. Por favor, forneça esses dados no passo anterior.",
            )

        proposal_data = SaveProposalRequest(
            bank_num=in100_data["cbcIfPagadora"],
            agency={
                "number": in100_data["agenciaPagadora"],
                "secure_digit": "",
            },
            account={
                "number": (
                    in100_data["contaCorrente"][:-1]
                    if in100_data["contaCorrente"]
                    else ""
                ),
                "secure_digit": (
                    in100_data["contaCorrente"][-1]
                    if in100_data["contaCorrente"]
                    else ""
                ),
            },
            banco_ordem_pagamento=in100_data["cbcIfPagadora"],
            customer={
                "cellphone": user_data["cellphone"],
                "phone": user_data.get("phone", ""),
                "city_of_birth": user_data["city_of_birth"],
                "cpf": user_data["cpf"],
                "birthdate": user_data["birthdate"],
                "email": user_data["email"],
                "address": user_data["address"],
                "marital_status": user_data.get("marital_status", "S"),
                "educational_level": user_data.get("educational_level", "7"),
                "identity_document": user_data["identity_document"],
                "nationality": user_data["nationality"],
                "name": user_data["name"],
                "spouse_name": user_data.get("spouse_name", ""),
                "mother_name": user_data["mother_name"],
                "father_name": user_data.get("father_name", "Não declarado"),
                "ppe": user_data.get("ppe", False),
                "gender": user_data["gender"],
                "state_of_birth": user_data["state_of_birth"],
            },
            finalidade_credito=1,
            income_date=datetime.now(),
            margin=in100_data.get("margemDisponivelRcc", 0),
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

    async def list_cards(self, page: int = 1, per_page: int = 20, cpf: str = None):
        """
        Lista todos os cartões com paginação e filtro opcional por CPF.
        """
        repository = BMGMongoRepository()

        query = {}
        if cpf:
            query["cpf"] = cpf

        total = repository.count_documents(self.collection, query)

        skip = (page - 1) * per_page
        total_pages = ceil(total / per_page) if total > 0 else 1

        cards = repository.get_paginated(self.collection, query, skip, per_page)

        items = []
        for card in cards:
            items.append(
                {
                    "id": card.get("id"),
                    "name": card.get("name"),
                    "benefit": card.get("benefit", ""),
                    "cpf": card.get("cpf", ""),
                    "status": self._determine_card_status(card),
                    "proposal_number": card.get("proposal_number", ""),
                    "card_limit": card.get("card_simulation", {}).get("limit", 0),
                    "withdrawal_limit": card.get("card_simulation", {}).get(
                        "withdrawal_limit", 0
                    ),
                    "has_proposal": "proposal_number" in card,
                    # "document": card.get("identity_document"),
                    # "bank": card.get("bank_data"),
                    # "address": card.get("address"),
                }
            )

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    def _determine_card_status(self, card_data):
        """Determina o status atual do cartão."""
        if "proposal_number" in card_data:
            return "approved"
        elif "card_simulation" in card_data:
            limit = card_data.get("card_simulation", {}).get("limit", 0)
            if limit > 0:
                return "eligible"
            else:
                return "not_eligible"
        elif "in100" in card_data:
            return "verified"
        else:
            return "pending"

    async def get_card_details(self, proposal_number: str):
        """
        Obtém detalhes completos de um cartão pelo número da proposta.

        Args:
            proposal_number: O número da proposta do cartão

        Returns:
            Detalhes completos do cartão ou None se não encontrado
        """
        repository = BMGMongoRepository()
        card = repository.get_from_collection_by_proposal(
            self.collection, proposal_number
        )

        if not card:
            return None

        in100_data = card.get("in100", {}).get("consulta", {})
        card_simulation = card.get("card_simulation", {})

        return {
            "customer_info": {
                "id": card.get("id"),
                "name": card.get("name", ""),
                "cpf": card.get("cpf", ""),
                "birthdate": card.get("birthdate", ""),
                "phone": card.get("phone", ""),
                "email": card.get("email", ""),
                "address": card.get("address", {}),
                "mother_name": card.get("mother_name", ""),
                "identity_document": card.get("identity_document", {}),
            },
            "benefit_info": {
                "benefit_number": card.get("benefit", ""),
                "benefit_type": in100_data.get("especie", ""),
                "agency": in100_data.get("agenciaPagadora", ""),
                "bank_code": in100_data.get("cbcIfPagadora", ""),
                "account_number": in100_data.get("contaCorrente", ""),
            },
            "card_info": {
                "proposal_number": card.get("proposal_number", ""),
                "status": self._determine_card_status(card),
                "stage": self._determine_card_stage(card),
                "card_limit": card_simulation.get("limit", 0),
                "withdrawal_limit": card_simulation.get("withdrawal_limit", 0),
                "created_at": card.get("created_at", ""),
                "updated_at": card.get("updated_at", ""),
            },
            "in100_data": {
                "full_data": in100_data,
                "available_margin": in100_data.get("margemDisponivel", "0"),
                "committed_value": in100_data.get("valorComprometido", "0"),
                "income_value": in100_data.get("valorLiquido", "0"),
            },
            "steps_completed": {
                "first_step": True,
                "second_step": "card_simulation" in card,
                "third_step": "address" in card and "identity_document" in card,
                "fourth_step": "proposal_number" in card,
            },
        }

    def _determine_card_stage(self, card_data):
        """Determina o estágio atual do cartão com base nos dados."""
        if "proposal_number" in card_data:
            return "proposal_sent"
        elif "card_simulation" in card_data:
            return "simulated"
        elif "in100" in card_data:
            return "in100_consulted"
        else:
            return "started"
