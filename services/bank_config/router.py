from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from .service import BankConfigService
from .schemas import BankUpdateRequest, BankAddRequest

router = APIRouter(prefix="/api/v1/banks/config", tags=["bank-config"])


def get_bank_config_service():
    return BankConfigService()


@router.get("/", response_model=Dict[str, Any])
async def get_bank_config(
    service: BankConfigService = Depends(get_bank_config_service),
):
    """Obtém a configuração atual de bancos"""
    return service.get_bank_config()


@router.get("/active", response_model=List[str])
async def get_active_banks(
    feature: Optional[str] = None,
    service: BankConfigService = Depends(get_bank_config_service),
):
    """
    Obtém a lista de bancos ativos, opcionalmente filtrados por feature

    - feature: "simulation" ou "proposal" (opcional)
    """
    return service.get_active_banks(feature)


@router.put("/{bank_name}/status", response_model=Dict[str, Any])
async def update_bank_status(
    bank_name: str,
    update_data: BankUpdateRequest,
    service: BankConfigService = Depends(get_bank_config_service),
):
    """
    Atualiza o status de um banco

    - bank_name: Nome do banco a atualizar
    - active: Novo status (ativo/inativo)
    - features: Lista de features suportadas (opcional)
    """
    success = service.update_bank_status(
        bank_name=bank_name,
        active=update_data.active,
        features=update_data.features if update_data.features else None,
        updater=update_data.updated_by,
    )

    if not success:
        raise HTTPException(
            status_code=404, detail=f"Banco não encontrado: {bank_name}"
        )

    return {"success": True, "message": f"Banco {bank_name} atualizado com sucesso"}


@router.post("/", response_model=Dict[str, Any])
async def add_bank(
    bank_data: BankAddRequest,
    service: BankConfigService = Depends(get_bank_config_service),
):
    """
    Adiciona um novo banco à configuração
    """
    success = service.add_bank(
        bank_name=bank_data.bank_name,
        description=bank_data.description,
        active=bank_data.active,
        features=bank_data.features,
        updater=bank_data.updated_by,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Não foi possível adicionar o banco: {bank_data.bank_name}",
        )

    return {
        "success": True,
        "message": f"Banco {bank_data.bank_name} adicionado com sucesso",
    }


@router.get("/check/{bank_name}", response_model=Dict[str, Any])
async def check_bank_status(
    bank_name: str,
    feature: str,
    service: BankConfigService = Depends(get_bank_config_service),
):
    """
    Verifica se um banco está ativo para uma feature específica

    - bank_name: Nome do banco a verificar
    - feature: Feature a verificar ("simulation" ou "proposal")
    """
    is_active = service.is_bank_active(bank_name, feature)

    return {"bank_name": bank_name, "feature": feature, "active": is_active}
