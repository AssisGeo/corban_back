from pymongo import MongoClient
import os
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TableConfigService:
    def __init__(self):
        self.mongo_url = os.getenv("MONGODB_URL")
        self.client = MongoClient(self.mongo_url)
        self.db = self.client["fgts_agent"]
        self.collection = self.db["table_configs"]

        self._ensure_default_config()

    def _ensure_default_config(self):
        """Cria a configuração padrão se não existir"""
        if self.collection.count_documents({}) == 0:
            default_config = {
                "tables": {
                    "57851": {
                        "table_id": "57851",
                        "name": "Tabela Padrão FGTS",
                        "description": "Tabela padrão para antecipação de FGTS",
                        "active": True,
                        "bank_name": "FACTA",
                        "updated_at": datetime.utcnow(),
                    },
                    "0": {
                        "table_id": "0",
                        "name": "Tabela VCTEX Padrão",
                        "description": "Tabela padrão VCTEX (feeScheduleId)",
                        "active": True,
                        "bank_name": "VCTEX",
                        "updated_at": datetime.utcnow(),
                    },
                    "1": {
                        "table_id": "1",
                        "name": "Tabela VCTEX Promocional",
                        "description": "Tabela promocional VCTEX (feeScheduleId)",
                        "active": False,
                        "bank_name": "VCTEX",
                        "updated_at": datetime.utcnow(),
                    },
                    "DEFAULT_QI": {
                        "table_id": "DEFAULT_QI",
                        "name": "Tabela QI Bank",
                        "description": "Tabela padrão QI Bank",
                        "active": True,
                        "bank_name": "QI",
                        "updated_at": datetime.utcnow(),
                    },
                },
                "last_updated": datetime.utcnow(),
            }
            self.collection.insert_one(default_config)
            logger.info("Configuração padrão de tabelas criada")

    def get_table_config(self) -> Dict:
        """Obtém a configuração atual das tabelas"""
        config = self.collection.find_one({})
        if not config:
            self._ensure_default_config()
            config = self.collection.find_one({})

        if "_id" in config:
            del config["_id"]

        return config

    def get_tables_by_bank(self, bank_name: str) -> List[Dict]:
        """
        Retorna todas as tabelas para um banco específico

        Args:
            bank_name: Nome do banco para filtrar

        Returns:
            Lista de tabelas do banco
        """
        config = self.get_table_config()

        bank_tables = []
        for table_id, table_info in config["tables"].items():
            if table_info["bank_name"] == bank_name:
                table_copy = table_info.copy()
                table_copy["table_id"] = table_id
                bank_tables.append(table_copy)

        return bank_tables

    def get_active_table_for_bank(self, bank_name: str) -> Optional[Dict]:
        """
        Obtém a tabela ativa para um banco específico

        Args:
            bank_name: ID do banco

        Returns:
            Tabela ativa ou None se não encontrar
        """
        bank_tables = self.get_tables_by_bank(bank_name)

        for table in bank_tables:
            if table["active"]:
                return table

        return None

    def set_active_table(self, table_id: str, updater: str = None) -> bool:
        """
        Define uma tabela como ativa e as outras do mesmo banco como inativas

        Args:
            table_id: ID da tabela a ativar
            updater: Identificador de quem atualizou

        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        config = self.get_table_config()

        if table_id not in config["tables"]:
            logger.warning(f"Tentativa de ativar tabela inexistente: {table_id}")
            return False

        # Determinar o ID do banco da tabela
        bank_name = config["tables"][table_id]["bank_name"]

        # Desativar todas as tabelas do mesmo banco
        for tid, table_info in config["tables"].items():
            if table_info["bank_name"] == bank_name:
                config["tables"][tid]["active"] = tid == table_id
                config["tables"][tid]["updated_at"] = datetime.utcnow()
                if updater:
                    config["tables"][tid]["updated_by"] = updater

        config["last_updated"] = datetime.utcnow()

        self.collection.replace_one({}, config)

        logger.info(f"Tabela {table_id} definida como ativa para o banco {bank_name}")
        return True

    def add_table(
        self,
        table_id: str,
        name: str,
        description: str,
        bank_name: str,
        active: bool = False,
        updater: str = None,
    ) -> bool:
        """
        Adiciona uma nova tabela à configuração

        Args:
            table_id: ID da tabela a adicionar
            name: Nome amigável da tabela
            description: Descrição da tabela
            bank_name: ID do banco ao qual a tabela pertence
            active: Se deve ativar esta tabela (e desativar outras do mesmo banco)
            updater: Identificador de quem adicionou

        Returns:
            True se adicionado com sucesso, False caso contrário
        """
        config = self.get_table_config()

        if table_id in config["tables"]:
            logger.warning(f"Tabela já existe: {table_id}")
            return False

        # Adicionar nova tabela
        config["tables"][table_id] = {
            "table_id": table_id,
            "name": name,
            "description": description,
            "active": False,  # Inicialmente inativa
            "bank_name": bank_name,
            "updated_at": datetime.utcnow(),
            "updated_by": updater,
        }

        config["last_updated"] = datetime.utcnow()

        # Atualizar no MongoDB
        self.collection.replace_one({}, config)

        logger.info(f"Nova tabela adicionada: {table_id}")

        # Se deve ativar, chama método separado
        if active:
            self.set_active_table(table_id, updater)

        return True

    @staticmethod
    def get_active_table_for_bank_static(bank_name: str) -> Optional[str]:
        """
        Método estático para obter a tabela ativa para um banco específico

        Args:
            bank_name: ID do banco

        Returns:
            ID da tabela ativa ou None se não encontrar
        """
        try:
            mongo_client = MongoClient(os.getenv("MONGODB_URL"))
            db = mongo_client["fgts_agent"]
            collection = db["table_configs"]

            config = collection.find_one({})
            if not config or "tables" not in config:
                return None

            for table_id, table_info in config["tables"].items():
                if table_info["bank_name"] == bank_name and table_info["active"]:
                    return table_id

            return None
        except Exception as e:
            logger.error(f"Erro ao obter tabela ativa (static): {str(e)}")
            return None
