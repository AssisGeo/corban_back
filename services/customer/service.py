import pandas as pd
from fastapi import UploadFile
from datetime import datetime, timezone
from typing import Dict, Any
import logging
from pymongo import MongoClient
import io
import os

logger = logging.getLogger(__name__)


class CustomerService:
    def __init__(self):
        self.mongo_url = os.getenv("MONGODB_URL")
        self.client = MongoClient(self.mongo_url)
        self.db = self.client["fgts_agent"]
        self.collection = self.db["sessions"]

    async def process_csv(self, file: UploadFile) -> Dict[str, Any]:
        try:
            # Ler o CSV
            content = await file.read()
            df = pd.read_csv(io.StringIO(content.decode("utf-8")))

            total_rows = len(df)
            success_count = 0
            error_count = 0

            for _, row in df.iterrows():
                try:
                    # Criar session_id usando DDD e telefone
                    session_id = f"55{row['DDDCEL1']}{row['CEL1']}"

                    # Preparar dados do cliente
                    customer_data = {
                        "customer_info": {
                            "name": str(row["NOME"]) if pd.notna(row["NOME"]) else None,
                            "cpf": (
                                str(row["CPF"]).zfill(11)
                                if pd.notna(row["CPF"])
                                else None
                            ),
                            "mother_name": (
                                str(row["NOME_MAE"])
                                if pd.notna(row["NOME_MAE"])
                                else None
                            ),
                            "gender": (
                                str(row["SEXO"]) if pd.notna(row["SEXO"]) else None
                            ),
                            "birth_date": (
                                f"{str(row['NASC'])[0:4]}-{str(row['NASC'])[4:6]}-{str(row['NASC'])[6:8]}"
                                if pd.notna(row["NASC"])
                                else None
                            ),
                            "address_number": (
                                str(row["NUMERO"]) if pd.notna(row["NUMERO"]) else None
                            ),
                            "zip_code": (
                                str(row["CEP"]) if pd.notna(row["CEP"]) else None
                            ),
                            "phone": {
                                "ddd": str(row["DDDCEL1"]),
                                "number": str(row["CEL1"]),
                            },
                            "email": (
                                str(row["EMAIL1"]) if pd.notna(row["EMAIL1"]) else None
                            ),
                        },
                        "session_id": session_id,
                    }

                    # Inserir ou atualizar no MongoDB
                    self.collection.update_one(
                        {"session_id": session_id},
                        {
                            "$set": {
                                "customer_data": customer_data,
                                "created_at": datetime.now(timezone.utc),
                                "last_updated": datetime.now(timezone.utc),
                                "source": "upload",
                                "metadata": {
                                    "origin": "upload",
                                    "platform": "csv",
                                    "form_type": "bulk_upload"
                                },
                                "status": "active"
                            }
                        },
                        upsert=True,
                    )

                    success_count += 1
                except Exception as e:
                    logger.error(f"Error processing row: {str(e)}")
                    error_count += 1

            return {
                "total_processed": total_rows,
                "success_count": success_count,
                "error_count": error_count,
            }

        except Exception as e:
            logger.error(f"Error processing CSV: {str(e)}")
            raise

    async def get_customers(self, skip: int = 0, limit: int = 20, search: str = None):
        try:
            # Base query
            query = {"customer_data": {"$exists": True}}

            # Add search condition if provided
            if search:
                query["$or"] = [
                    {
                        "customer_data.customer_info.name": {
                            "$regex": search,
                            "$options": "i",
                        }
                    },
                    {
                        "customer_data.customer_info.cpf": {
                            "$regex": search,
                            "$options": "i",
                        }
                    },
                    {"session_id": {"$regex": search, "$options": "i"}},
                ]

            # Get total count
            total = self.collection.count_documents(query)

            # Get paginated results
            customers = list(self.collection.find(query).skip(skip).limit(limit))

            return {"total": total, "items": customers}
        except Exception as e:
            logger.error(f"Error fetching customers: {str(e)}")
            raise

    async def update_customer(self, session_id: str, customer_data: Dict[str, Any]):
        try:
            # Update customer data
            result = self.collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "customer_data.customer_info": customer_data,
                        "last_updated": datetime.now(timezone.utc),
                    }
                },
            )

            if result.matched_count == 0:
                raise ValueError(f"Customer with session_id {session_id} not found")

            return {"message": "Customer updated successfully"}
        except Exception as e:
            logger.error(f"Error updating customer: {str(e)}")
            raise

    async def delete_customer(self, session_id: str):
        try:
            result = self.collection.delete_one({"session_id": session_id})

            if result.deleted_count == 0:
                raise ValueError(f"Customer with session_id {session_id} not found")

            return {"message": "Customer deleted successfully"}
        except Exception as e:
            logger.error(f"Error deleting customer: {str(e)}")
            raise
