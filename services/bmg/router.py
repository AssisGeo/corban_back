from fastapi import APIRouter
from apis import BmgApiClient, In100Request

router = APIRouter(prefix="/api/v1/bmg", tags=["bmg"])


@router.post("/request_in100")
async def request_in100(data: In100Request) -> None:
    bmg_client = BmgApiClient()
    response = bmg_client.request_in100(data)

    return response
