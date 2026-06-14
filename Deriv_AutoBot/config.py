# Trading Parameters
EMA_FAST = 50
EMA_SLOW = 200
RSI_PERIOD = 14
ATR_PERIOD = 14

# Risk Management
MAX_SIMULTANEOUS_TRADES = 5
MAX_DAILY_LOSS_PERCENT = 5.0
CONSECUTIVE_LOSS_LIMIT = 3
PAUSE_AFTER_LOSS_LIMIT_HOURS = 2
RISK_RR_RATIO = 2.5
BREAK_EVEN_AT_R = 1.0
TRAIL_START_AT_R = 1.5

# WhatsApp API Configuration (User to fill these)
WHATSAPP_TOKEN = "PLACEHOLDER_TOKEN"
WHATSAPP_PHONE_ID = "YOUR_PHONE_NUMBER_ID"
WHATSAPP_RECIPIENT_PHONE = "YOUR_RECIPIENT_PHONE_NUMBER"

# Strategy Filters
MIN_TREND_STRENGTH = 70  # Scored 0-100
MAX_SPREAD_POINTS = {
    "Volatility": 50,
    "Step": 30,
    "Crash": 60,
    "Boom": 60,
    "Jump": 50
}

# Session Times (EAT)
SESSIONS = {
    "London": {"start": 10, "end": 19, "atr_mult": 1.0, "risk": 1.0},
    "New York": {"start": 15, "end": 0, "atr_mult": 1.2, "risk": 1.5}
}

# Database
DB_PATH = "data/trading.db"
