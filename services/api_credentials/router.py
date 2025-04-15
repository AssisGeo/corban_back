from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from .service import APICredentialService
from .schemas import CredentialRequest, CredentialResponse


router = APIRouter(prefix="/api/v1/api-credentials", tags=["api-credentials"])


def get_api_credential_service():
    return APICredentialService()


@router.get("/", response_model=List[CredentialResponse])
async def list_credentials(
    api_name: Optional[str] = None,
    service: APICredentialService = Depends(get_api_credential_service),
):
    """Lista todas as credenciais de API (valores são mascarados)"""
    credentials = service.list_credentials(api_name)
    return credentials


@router.post("/", response_model=Dict[str, Any])
async def set_credential(
    request: CredentialRequest,
    service: APICredentialService = Depends(get_api_credential_service),
):
    """Define ou atualiza uma credencial de API"""
    success = service.set_credential(
        key=request.key,
        value=request.value,
        api_name=request.api_name,
        description=request.description,
        updated_by=request.updated_by,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Falha ao definir credencial")

    return {
        "success": True,
        "message": f"Credencial {request.key} definida com sucesso",
    }


@router.delete("/{key}", response_model=Dict[str, Any])
async def delete_credential(
    key: str, service: APICredentialService = Depends(get_api_credential_service)
):
    """Remove uma credencial (define como inativa)"""
    success = service.delete_credential(key)

    if not success:
        raise HTTPException(status_code=404, detail=f"Credencial {key} não encontrada")

    return {"success": True, "message": f"Credencial {key} removida com sucesso"}


@router.get("/{api_name}", response_model=Dict[str, str])
async def get_api_credentials(
    api_name: str, service: APICredentialService = Depends(get_api_credential_service)
):
    """Obtém todas as credenciais para uma API específica"""
    credentials = service.get_all_api_credentials(api_name)

    if not credentials:
        raise HTTPException(
            status_code=404, detail=f"Nenhuma credencial encontrada para API {api_name}"
        )

    return credentials
