from pymongo import MongoClient
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class APICredentialService:
    """Serviço para gerenciar credenciais de APIs"""

    def __init__(self):
        self.mongo_url = os.getenv("MONGODB_URL")
        self.client = MongoClient(self.mongo_url)
        self.db = self.client["fgts_agent"]
        self.collection = self.db["api_credentials"]

        self._migrate_initial_credentials()

    def _migrate_initial_credentials(self):
        """Migra credenciais iniciais de .env para o banco de dados se a coleção estiver vazia"""
        if self.collection.count_documents({}) > 0:
            return

        apis = ["FACTA", "VCTEX", "BMG", "INAPI"]

        for api_name in apis:
            for key, value in os.environ.items():
                if key.startswith(f"{api_name}_"):
                    if self.collection.find_one({"key": key}):
                        continue

                    self.collection.insert_one(
                        {
                            "key": key,
                            "value": value,
                            "api_name": api_name,
                            "description": f"Migrado automaticamente de .env: {key}",
                            "active": True,
                            "updated_at": datetime.utcnow(),
                            "created_at": datetime.utcnow(),
                        }
                    )

                    logger.info(
                        f"Credencial {key} migrada de .env para o banco de dados"
                    )

    def get_credential(self, key: str) -> Optional[str]:
        """
        Obtém o valor de uma credencial pelo nome

        Args:
            key: Nome da credencial (ex: "FACTA_USER")

        Returns:
            Valor da credencial ou None se não encontrada
        """
        credential = self.collection.find_one({"key": key, "active": True})

        if credential:
            return credential["value"]

        return os.getenv(key)

    def get_all_api_credentials(self, api_name: str) -> Dict[str, str]:
        """
        Obtém todas as credenciais de uma API específica

        Args:
            api_name: Nome da API (ex: "FACTA", "VCTEX")

        Returns:
            Dicionário com chave e valor de todas as credenciais ativas
        """
        credentials = self.collection.find({"api_name": api_name, "active": True})

        result = {}
        for cred in credentials:
            result[cred["key"]] = cred["value"]

        if not result:
            for key, value in os.environ.items():
                if key.startswith(f"{api_name}_"):
                    result[key] = value

        return result

    def set_credential(
        self,
        key: str,
        value: str,
        api_name: str,
        description: str = None,
        updated_by: str = None,
    ) -> bool:
        """
        Define ou atualiza uma credencial

        Args:
            key: Nome da credencial
            value: Valor da credencial
            api_name: Nome da API
            description: Descrição opcional
            updated_by: Quem atualizou

        Returns:
            True se operação bem-sucedida
        """
        try:
            now = datetime.utcnow()

            existing = self.collection.find_one({"key": key})

            if existing:
                self.collection.update_one(
                    {"key": key},
                    {
                        "$set": {
                            "value": value,
                            "api_name": api_name,
                            "description": description or existing.get("description"),
                            "active": True,
                            "updated_at": now,
                            "updated_by": updated_by,
                        }
                    },
                )
            else:
                self.collection.insert_one(
                    {
                        "key": key,
                        "value": value,
                        "api_name": api_name,
                        "description": description or f"Credencial para {api_name}",
                        "active": True,
                        "created_at": now,
                        "updated_at": now,
                        "updated_by": updated_by,
                    }
                )

            logger.info(f"Credencial {key} definida/atualizada com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao definir credencial {key}: {str(e)}")
            return False

    def delete_credential(self, key: str) -> bool:
        """
        Remove uma credencial (define como inativa)

        Args:
            key: Nome da credencial

        Returns:
            True se operação bem-sucedida
        """
        try:
            result = self.collection.update_one(
                {"key": key},
                {"$set": {"active": False, "updated_at": datetime.utcnow()}},
            )

            if result.matched_count == 0:
                logger.warning(f"Credencial {key} não encontrada")
                return False

            logger.info(f"Credencial {key} desativada com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao desativar credencial {key}: {str(e)}")
            return False

    def list_credentials(self, api_name: str = None) -> List[Dict[str, Any]]:
        """
        Lista todas as credenciais

        Args:
            api_name: Filtrar por API específica

        Returns:
            Lista de credenciais
        """
        query = {}
        if api_name:
            query["api_name"] = api_name

        credentials = list(self.collection.find(query, {"_id": 0}))

        for cred in credentials:
            if "value" in cred:
                cred["value"] = "********"

        return credentials
