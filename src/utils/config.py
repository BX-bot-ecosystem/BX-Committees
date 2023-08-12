from pathlib import Path
import redis
import json
from dotenv import load_dotenv
import os

load_dotenv()
_REDIS_HOST = os.getenv("REDIS_HOST")
_REDIS_PORT = int(os.getenv("REDIS_PORT"))

ROOT = str(Path(__file__).parent.parent)

r = redis.Redis(host=_REDIS_HOST, port=_REDIS_PORT, decode_responses=True)

with open(ROOT + "/data/Committees/committees.json") as f:
    committees_info = json.load(f)
