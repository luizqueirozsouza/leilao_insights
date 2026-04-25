import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Carrega variáveis do mesmo .env que o Django
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

app = FastAPI(title="Leilão Insights AI Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AI Engine (FastAPI) is running", "status": "online"}

@app.get("/ai/summarize/{auction_id}")
async def summarize_auction(auction_id: str):
    # Futura integração com LLM para resumir o leilão
    return {
        "auction_id": auction_id,
        "summary": "Este leilão apresenta um imóvel com 30% de desconto abaixo da média do bairro.",
        "risk_level": "low"
    }
