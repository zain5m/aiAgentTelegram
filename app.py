import asyncio

from fastapi import FastAPI

from listener import start_listener

app = FastAPI()

listener_task = None


@app.get("/")
def health():
    return {"status": "ok", "listener": "running" if listener_task else "stopped"}


@app.post("/start")
async def start():
    global listener_task

    if listener_task is None:
        loop = asyncio.get_event_loop()
        listener_task = loop.create_task(start_listener())
        return {"message": "listener started"}
    else:
        return {"message": "listener already running"}
