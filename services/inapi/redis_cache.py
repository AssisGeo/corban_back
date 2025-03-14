import json
import os
import redis


def get_redis_connection():
    r = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=os.getenv("REDIS_PORT"),
        decode_responses=True,
    )

    return r


def add_in100_to_cache(id, in_100_data):
    r = get_redis_connection()

    r.set(id, json.dumps(in_100_data), ex=60 * 60 * 24 * 30)  # 30 days in_100_data)


def get_in100_from_cache(id):
    r = get_redis_connection()

    data = r.get(id)

    if data is None:
        return None

    return json.loads(data)
