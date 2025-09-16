import redis
import os
from dotenv import load_dotenv

load_dotenv()

redis_url = os.environ.get('REDIS_URL')

if not redis_url:
    print("REDIS_URL not found in environment.")
else:
    try:
        r = redis.from_url(redis_url)
        r.ping()
        print("Successfully connected to Redis.")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
