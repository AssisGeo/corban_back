from pymongo import MongoClient
import os
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BankConfigService:
    def __init__(self):
        self.mongo_url = os.getenv("MONGODB_URL")
        self.client = MongoClient(self.mongo_url)
        self.db = self.client["fgts_agent"]
        self.collection = self.db["bank_configs"]

        self._ensure_default_config()

    def _ensure_default_config(self):
        """Cria a configuração padrão se não existir"""
        if self.collection.count_documents({}) == 0:
            default_config = {
                "banks": {
                    "VCTEX": {
                        "bank_name": "VCTEX",
                        "active": True,
                        "features": ["simulation", "proposal"],
                        "description": "VCTEX Bank - Antecipação de FGTS",
                        "updated_at": datetime.utcnow(),
                    },
                    "FACTA": {
                        "bank_name": "FACTA",
                        "active": True,
                        "features": ["simulation", "proposal"],
                        "description": "Banco Facta - Antecipação de FGTS",
                        "updated_at": datetime.utcnow(),
                    },
                }
            }
            self.collection.insert_one(default_config)
            logger.info("Configuração padrão de bancos criada")

    def get_bank_config(self) -> Dict:
        """Obtém a configuração atual dos bancos"""
        config = self.collection.find_one({})
        if not config:
            self._ensure_default_config()
            config = self.collection.find_one({})

        if "_id" in config:
            del config["_id"]

        return config

    def get_active_banks(self, feature: Optional[str] = None) -> List[str]:
        """
        Retorna a lista de bancos ativos, opcionalmente filtrados por feature

        Args:
            feature: Feature a filtrar ("simulation" ou "proposal")

        Returns:
            Lista de nomes dos bancos ativos
        """
        config = self.get_bank_config()

        active_banks = []
        for bank_name, bank_info in config["banks"].items():
            if bank_info["active"]:
                if feature is None or feature in bank_info["features"]:
                    active_banks.append(bank_name)

        return active_banks

    def update_bank_status(
        self,
        bank_name: str,
        active: bool,
        features: List[str] = None,
        updater: str = None,
    ) -> bool:
        """
        Atualiza o status de um banco

        Args:
            bank_name: Nome do banco a atualizar
            active: Novo status de atividade
            features: Lista de features suportadas
            updater: Identificador de quem atualizou

        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        config = self.get_bank_config()

        if bank_name not in config["banks"]:
            logger.warning(f"Tentativa de atualizar banco inexistente: {bank_name}")
            return False

        config["banks"][bank_name]["active"] = active
        if features is not None:
            config["banks"][bank_name]["features"] = features
        config["banks"][bank_name]["updated_at"] = datetime.utcnow()
        if updater:
            config["banks"][bank_name]["updated_by"] = updater

        config["last_updated"] = datetime.utcnow()

        self.collection.replace_one({}, config)

        logger.info(
            f"Banco {bank_name} atualizado: active={active}, features={features}"
        )
        return True

    def is_bank_active(self, bank_name: str, feature: str) -> bool:
        """
        Verifica se um banco está ativo para uma determinada feature

        Args:
            bank_name: Nome do banco a verificar
            feature: Feature a verificar ("simulation" ou "proposal")

        Returns:
            True se o banco estiver ativo para a feature, False caso contrário
        """
        config = self.get_bank_config()

        if bank_name not in config["banks"]:
            return False

        bank_info = config["banks"][bank_name]
        return bank_info["active"] and feature in bank_info["features"]

    def add_bank(
        self,
        bank_name: str,
        description: str,
        active: bool = False,
        features: List[str] = None,
        updater: str = None,
    ) -> bool:
        """
        Adiciona um novo banco à configuração

        Args:
            bank_name: Nome do banco a adicionar
            description: Descrição do banco
            active: Status inicial
            features: Lista de features suportadas
            updater: Identificador de quem adicionou

        Returns:
            True se adicionado com sucesso, False caso contrário
        """
        config = self.get_bank_config()

        if bank_name in config["banks"]:
            logger.warning(f"Banco já existe: {bank_name}")
            return False

        features = features or []

        config["banks"][bank_name] = {
            "bank_name": bank_name,
            "active": active,
            "features": features,
            "description": description,
            "updated_at": datetime.utcnow(),
            "updated_by": updater,
        }

        config["last_updated"] = datetime.utcnow()

        self.collection.replace_one({}, config)

        logger.info(f"Novo banco adicionado: {bank_name}")
        return True

    @staticmethod
    def get_active_banks_static(feature: Optional[str] = None) -> List[str]:
        """
        Método estático para obter bancos ativos sem criar instância completa
        """
        try:
            mongo_client = MongoClient(os.getenv("MONGODB_URL"))
            db = mongo_client["fgts_agent"]
            collection = db["bank_configs"]

            config = collection.find_one({})
            if not config or "banks" not in config:
                return []

            active_banks = []
            for bank_name, bank_info in config["banks"].items():
                if bank_info.get("active", True) and (
                    feature is None or feature in bank_info.get("features", [])
                ):
                    active_banks.append(bank_name)

            return active_banks
        except Exception as e:
            logger.error(f"Erro ao obter bancos ativos (static): {str(e)}")
            return []
