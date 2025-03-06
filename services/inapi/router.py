from fastapi import APIRouter
from apis import InApiClient

router = APIRouter(prefix="/api/v1/inapi", tags=["inapi"])


@router.get("/in100")
async def get_in_100(cpf: str, benefit: str):
    in_api_client = InApiClient()
    return in_api_client.get_in_100(cpf, benefit)
