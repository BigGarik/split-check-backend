from fastapi import FastAPI
from redis import asyncio as aioredis

app = FastAPI()

redis_client = aioredis.from_url("redis://backendredisuser:d#q?3%.(oS1b6S@192.168.0.4", encoding="utf8", decode_responses=True)


@app.get("/")
async def root():    
    return {"message": "Привет, мир!"}

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    await redis_client.set("test", item_id)
    return {"item_id": redis_client.get("test")}