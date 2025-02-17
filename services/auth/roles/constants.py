from enum import IntEnum


class UserRole(IntEnum):
    ADMIN = 1
    SUPERVISOR = 2
    OPERATOR = 3


ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        "create_user",
        "update_user",
        "delete_user",
        "view_all_reports",
        "manage_settings",
        "manage_simulations",
        "manage_proposals",
        "view_dashboard",
        "export_data",
        "manage_documents",
    ],
    UserRole.SUPERVISOR: [
        "view_team_reports",
        "manage_simulations",
        "manage_proposals",
        "view_dashboard",
        "export_data",
        "view_documents",
    ],
    UserRole.OPERATOR: [
        "create_simulation",
        "create_proposal",
        "view_own_reports",
        "view_documents",
    ],
}

ROLE_NAMES = {
    UserRole.ADMIN: "Administrador",
    UserRole.SUPERVISOR: "Supervisor",
    UserRole.OPERATOR: "Operador",
}
