import os
from contextlib import asynccontextmanager
from prisma import Prisma
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class PrismaManager:
    _instance = None
    _client = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(PrismaManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    async def get_client(cls):
        """
        Singleton method to get or create Prisma client
        """
        if not cls._client:
            # Recupera a URL do MongoDB do ambiente
            mongodb_url = os.getenv("MONGODB_URL")

            if not mongodb_url:
                raise ValueError(
                    "MONGODB_URL não configurada. Verifique seu arquivo .env"
                )

            cls._client = Prisma(datasources={"db": {"url": mongodb_url}})

            try:
                await cls._client.connect()
                logger.info("Prisma client conectado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao conectar com Prisma: {e}")
                raise
        return cls._client

    @classmethod
    @asynccontextmanager
    async def get_context(cls):
        """
        Provides a context manager for Prisma client
        """
        client = await cls.get_client()
        try:
            yield client
        except Exception as e:
            logger.error(f"Erro no contexto Prisma: {e}")
            raise
        finally:
            # Não desconecta para manter a conexão singleton
            pass

    @classmethod
    async def disconnect(cls):
        """
        Disconnect the Prisma client
        """
        if cls._client:
            try:
                await cls._client.disconnect()
                logger.info("Prisma client desconectado com sucesso")
                cls._client = None
            except Exception as e:
                logger.error(f"Erro ao desconectar Prisma client: {e}")


# Utility function for easy access
@asynccontextmanager
async def get_prisma():
    """
    Async context manager to get Prisma client
    """
    async with PrismaManager.get_context() as client:
        yield client


# Cleanup hook for application shutdown
async def close_prisma_connection():
    """
    Call this during application shutdown to close Prisma connection
    """
    await PrismaManager.disconnect()
