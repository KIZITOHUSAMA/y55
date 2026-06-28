from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from typing import List
from app.smc_logic import SMCAnalyzer
from app.bot_manager import BotManager

app = FastAPI(title="Pipnex Free API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Signal(BaseModel):
    pair: str
    type: str
    entry: str
    tp: str
    sl: str
    time: str
    strength: str

@app.get("/")
def read_root():
    return {"message": "Pipnex Free API is running"}

@app.get("/api/signals", response_model=List[Signal])
async def get_signals():
    pairs = ["XAUUSD", "EURUSD", "BTCUSD", "GBPUSD"]
    results = []
    for p in pairs:
        res = await SMCAnalyzer.generate_signal(p)
        results.append(res)
    return results

@app.get("/api/bots")
def get_bots():
    return BotManager.get_bots()

@app.post("/api/bots/{bot_id}/toggle")
def toggle_bot(bot_id: int):
    bot = BotManager.toggle_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bot

@app.get("/api/mt5/status")
def get_mt5_status():
    return BotManager.get_mt5_status()

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "bots_active": len([b for b in BotManager.get_bots() if b["status"] == "Running"]),
        "mt5_connected": True,
        "premium_unlocked": True,
        "vps_status": "active"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
