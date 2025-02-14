from fastapi import APIRouter, HTTPException, Depends
from .service import CEPService
from .schemas import AddressResponse

router = APIRouter(prefix="/api/v1/cep", tags=["cep"])


@router.get("/{cep}", response_model=AddressResponse)
async def get_address(cep: str, service: CEPService = Depends()):
    """Consulta endereço por CEP."""
    try:
        address = await service.get_address(cep)
        if "error" in address:
            raise HTTPException(status_code=404, detail=address["error"])
        return address
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
