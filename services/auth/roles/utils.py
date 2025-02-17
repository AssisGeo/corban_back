from typing import List
from fastapi import HTTPException, status
from .constants import UserRole, ROLE_PERMISSIONS, ROLE_NAMES


def get_user_permissions(role: UserRole) -> List[str]:
    """Retorna a lista de permissões para uma role específica"""
    return ROLE_PERMISSIONS.get(role, [])


def get_role_name(role: UserRole) -> str:
    """Retorna o nome amigável da role"""
    return ROLE_NAMES.get(role, "Desconhecido")


def validate_role_access(current_role: UserRole, target_role: UserRole) -> None:
    """
    Valida se um usuário com current_role pode modificar um usuário com target_role
    Admin pode modificar qualquer role
    Supervisor só pode modificar operadores
    Operadores não podem modificar roles
    """
    if current_role == UserRole.ADMIN:
        return

    if current_role == UserRole.SUPERVISOR and target_role != UserRole.OPERATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supervisors can only modify operator roles",
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to modify roles",
    )


def has_permission(user_role: UserRole, permission: str) -> bool:
    """Verifica se uma role tem uma permissão específica"""
    return permission in ROLE_PERMISSIONS.get(user_role, [])
