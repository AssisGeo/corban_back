from fastapi import APIRouter
from apis import BmgApiClient, In100Request, In100ConsultFilter, SingleConsultRequest

from services.bmg.card_service import (
    CardService,
    FirstStepRequest,
    SecondStepRequest,
    ThirdStepRequest,
    FourthStepRequest,
)

router = APIRouter(prefix="/api/v1/bmg", tags=["bmg"])


@router.post("/request_in100")
async def request_in100(data: In100Request):
    bmg_client = BmgApiClient()
    response = bmg_client.request_in100(data)

    return response


@router.post("/in100_consult_filter")
async def in100_consult_filter(data: In100ConsultFilter):
    bmg_client = BmgApiClient()
    response = bmg_client.in100_consult_filter(data)

    return response


@router.post("/single_consult_request")
async def single_consult_request(data: SingleConsultRequest):
    bmg_client = BmgApiClient()
    response = bmg_client.single_consult_request(data)

    return response


@router.post("/card/first_step")
async def card_first_step(data: FirstStepRequest):
    card_service = CardService()
    response = await card_service.first_step(data)

    return response


@router.post("/card/second_step")
async def card_second_step(data: SecondStepRequest):
    card_service = CardService()
    response = await card_service.second_step(data)

    return response


@router.post("/card/third_step")
async def card_third_step(data: ThirdStepRequest):
    card_service = CardService()
    response = await card_service.third_step(data)

    return response


@router.post("/card/fourth_step")
async def card_fourth_step(data: FourthStepRequest):
    card_service = CardService()
    response = await card_service.fourth_step(data)

    return response
