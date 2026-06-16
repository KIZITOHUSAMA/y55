# PTJ Bot Configuration
ASIA_END_HOUR = 8
NY_END_HOUR = 21

# Risk Management
RISK_PERCENT = 1.0
RR_RATIO = 5.0
PARTIAL_RR = 3.0
PARTIAL_VOLUME_PERCENT = 0.5

# SYMBOLS TO TRADE (Forex Majors)
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]

# MetaTrader 5 Login Details (Placeholders)
MT5_LOGIN = 12345678
MT5_PASSWORD = "PLACEHOLDER_PASSWORD"
MT5_SERVER = "Deriv-Server"

# Risk Manager Requirements
MAX_DAILY_LOSS_PERCENT = 5.0
CONSECUTIVE_LOSS_LIMIT = 3
PAUSE_AFTER_LOSS_LIMIT_HOURS = 2
SESSIONS = {
    "London": {"start": 10, "end": 19, "atr_mult": 1.0, "risk": 1.0},
    "New York": {"start": 15, "end": 0, "atr_mult": 1.2, "risk": 1.5}
}
MAX_SPREAD_POINTS = {
    "Volatility": 50,
    "EURUSD": 10,
    "GBPUSD": 12
}
