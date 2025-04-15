import os
from typing import Dict
from services.api_credentials.service import APICredentialService
import logging

logger = logging.getLogger(__name__)

_credential_service = None


def get_api_credential_service() -> APICredentialService:
    """Retorna a instância singleton do serviço de credenciais"""
    global _credential_service
    if _credential_service is None:
        _credential_service = APICredentialService()
    return _credential_service


def get_credential(key: str, default: str = None) -> str:
    """
    Obtém o valor de uma credencial específica

    Args:
        key: Nome da credencial (ex: FACTA_USER)
        default: Valor padrão caso não encontre

    Returns:
        Valor da credencial ou o valor padrão
    """
    try:
        service = get_api_credential_service()
        value = service.get_credential(key)

        if value is None and default is not None:
            return default

        return value
    except Exception as e:
        logger.error(f"Erro ao obter credencial {key}: {str(e)}")
        return os.getenv(key, default)


def get_api_credentials(api_name: str) -> Dict[str, str]:
    """
    Obtém todas as credenciais para uma API específica

    Args:
        api_name: Nome da API (ex: FACTA, VCTEX)

    Returns:
        Dicionário com todas as credenciais
    """
    try:
        service = get_api_credential_service()
        return service.get_all_api_credentials(api_name)
    except Exception as e:
        logger.error(f"Erro ao obter credenciais para API {api_name}: {str(e)}")

        result = {}
        for key, value in os.environ.items():
            if key.startswith(f"{api_name}_"):
                result[key] = value

        return result
