# main.py
from fastapi import FastAPI
from app.api.v1 import chat            # ← 폴더 구조에 맞춰 변경!
from dotenv import load_dotenv, find_dotenv


app = FastAPI(title="Emotion-based Finance Chatbot")
app.include_router(chat.router, prefix="/api")

load_dotenv(find_dotenv())

@app.get("/")
def root():
    return {"message": "Welcome to the Emotion-based Finance Chatbot API"}
