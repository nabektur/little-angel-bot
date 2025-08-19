import asyncio
import uvicorn

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def home():
    return {"message": "😎 I'm Awake Already!🔥"}

@app.head("/")
async def head():
    return {"message": "😎 I'm Awake Already!🔥"}

def run():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

def keep_alive():
    loop = asyncio.get_event_loop()
    loop.create_task(asyncio.to_thread(run))