from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/process/button1")
async def button1():
    return {"status": "not implemented"}


@app.post("/process/button2")
async def button2():
    return {"status": "not implemented"}


@app.post("/process/button3")
async def button3():
    return {"status": "not implemented"}
