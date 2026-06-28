import random
from datetime import datetime

class BotManager:
    """
    Simulates MT5 Connection and Cloud Bot execution.
    """

    _bots = [
        {"id": 1, "name": "SMC Scalper Pro", "status": "Running", "profit": 0.0, "start_time": datetime.now()},
        {"id": 2, "name": "Golden HFT", "status": "Running", "profit": 0.0, "start_time": datetime.now()},
        {"id": 3, "name": "Volatility Hunter", "status": "Paused", "profit": -12.0, "start_time": datetime.now()},
    ]

    @classmethod
    def get_bots(cls):
        # Update profits randomly to simulate activity
        for bot in cls._bots:
            if bot["status"] == "Running":
                bot["profit"] += random.uniform(-2.0, 5.0)
        return cls._bots

    @classmethod
    def toggle_bot(cls, bot_id):
        for bot in cls._bots:
            if bot["id"] == bot_id:
                bot["status"] = "Running" if bot["status"] == "Paused" else "Paused"
                return bot
        return None

    @classmethod
    def get_mt5_status(cls):
        return {
            "connected": True,
            "account_id": "8823419",
            "broker": "Deriv (SVG) LLC",
            "balance": 12450.80,
            "equity": 12510.45,
            "margin_level": 1540.20
        }
