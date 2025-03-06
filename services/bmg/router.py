from fastapi import APIRouter
from apis import BmgApiClient, In100Request, In100ConsultFilter, SingleConsultRequest

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
