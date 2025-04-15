from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from .service import TableConfigService
from .schemas import TableAddRequest

router = APIRouter(prefix="/api/v1/tables/config", tags=["table-config"])


def get_table_config_service():
    return TableConfigService()


@router.get("/", response_model=Dict[str, Any])
async def get_table_config(
    service: TableConfigService = Depends(get_table_config_service),
):
    """Obtém a configuração atual de tabelas"""
    return service.get_table_config()


@router.get("/bank/{bank_name}", response_model=List[Dict])
async def get_tables_by_bank(
    bank_name: str, service: TableConfigService = Depends(get_table_config_service)
):
    """
    Obtém todas as tabelas para um banco específico

    - bank_name: Nome do banco
    """
    return service.get_tables_by_bank(bank_name)


@router.get("/active/{bank_name}", response_model=Dict[str, Any])
async def get_active_table(
    bank_name: str, service: TableConfigService = Depends(get_table_config_service)
):
    """
    Obtém a tabela ativa para um banco específico

    - bank_name: ID do banco
    """
    table = service.get_active_table_for_bank(bank_name)
    if not table:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhuma tabela ativa encontrada para o banco ID {bank_name}",
        )

    return table


@router.put("/activate/{table_id}", response_model=Dict[str, Any])
async def set_active_table(
    table_id: str,
    updater: str = None,
    service: TableConfigService = Depends(get_table_config_service),
):
    """
    Define uma tabela como ativa (e as outras do mesmo banco como inativas)

    - table_id: ID da tabela a ativar
    - updater: Identificador de quem está atualizando
    """
    success = service.set_active_table(table_id, updater)

    if not success:
        raise HTTPException(
            status_code=404, detail=f"Tabela não encontrada: {table_id}"
        )

    return {"success": True, "message": f"Tabela {table_id} ativada com sucesso"}


@router.post("/", response_model=Dict[str, Any])
async def add_table(
    table_data: TableAddRequest,
    service: TableConfigService = Depends(get_table_config_service),
):
    """
    Adiciona uma nova tabela à configuração
    """
    success = service.add_table(
        table_id=table_data.table_id,
        name=table_data.name,
        description=table_data.description,
        bank_name=table_data.bank_name,  # Aqui mudamos para bank_name
        active=table_data.active,
        updater=table_data.updated_by,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Não foi possível adicionar a tabela: {table_data.table_id}",
        )

    return {
        "success": True,
        "message": f"Tabela {table_data.table_id} adicionada com sucesso",
    }
