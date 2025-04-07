from pymongo import MongoClient
import os
from bson.objectid import ObjectId

from services.inapi.redis_cache import get_in100_from_cache


class BMGMongoRepository:
    def __init__(self):
        self.mongo_url = os.getenv("MONGODB_URL")
        self.client = MongoClient(self.mongo_url)
        self.db = self.client["bmg"]

    def add_to_collection(self, collection_name, data):
        collection = self.db[collection_name]
        result = collection.insert_one(data)
        inserted_id = result.inserted_id

        # Fetch the inserted document
        inserted_doc = collection.find_one({"_id": inserted_id})

        if inserted_doc and "benefit" in inserted_doc:
            redis_key = f"in100_bmg_{data.cpf}_{inserted_doc['benefit']}"
            in100_data = get_in100_from_cache(redis_key)
            inserted_doc["in100"] = in100_data

        return self.parse_mongo_return(inserted_doc)

    def get_collection(self, collection_name):
        collection = self.db[collection_name]
        return collection

    def get_from_collection_by_id(self, collection_name, id):
        collection = self.db[collection_name]
        result = collection.find_one({"_id": ObjectId(id)})
        if not result:
            return None
        if result and "benefit" in result:
            redis_key = f"in100_bmg_{result['cpf']}_{result['benefit']}"
            in100_data = get_in100_from_cache(redis_key)
            if in100_data:
                result["in100"] = in100_data

        return self.parse_mongo_return(result)

    def get_from_collection_by_cpf(self, collection_name, cpf):
        collection = self.db[collection_name]
        result = collection.find_one({"cpf": cpf})

        if not result:
            return None

        if result and "benefit" in result:
            redis_key = f"in100_bmg_{result['cpf']}_{result['benefit']}"
            in100_data = get_in100_from_cache(redis_key)
            if in100_data:
                result["in100"] = in100_data

        return self.parse_mongo_return(result)

    def update_in_collection_by_id(self, collection_name, id, data):
        collection = self.db[collection_name]
        collection.update_one({"_id": ObjectId(id)}, {"$set": data})

        return self.get_from_collection_by_id(collection_name, id)

    def delete_from_collection_by_id(self, collection_name, id):
        collection = self.db[collection_name]
        collection.delete_one({"_id": ObjectId(id)})

    def parse_mongo_return(self, data):
        response = {
            "id": str(data["_id"]),
            **data,
        }
        del response["_id"]
        return response
