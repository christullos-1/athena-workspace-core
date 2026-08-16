# server.py

import os
import sys
from fastapi import FastAPI
from pydantic import BaseModel

# DEBUG: Show where the server is running from
print("DEBUG: SERVER WORKING DIRECTORY:", os.getcwd())
print("DEBUG: PYTHON MODULE SEARCH PATH:")
for p in sys.path:
    print(" -", p)

from core.logic_loop import LogicLoop
from core.model_client import ModelClient


app = FastAPI()

client = ModelClient()
athena = LogicLoop(client)


class UserMessage(BaseModel):
    message: str


@app.post("/athena")
def chat_endpoint(payload: UserMessage):
    response = athena.process(payload.message)
    return {"response": response}