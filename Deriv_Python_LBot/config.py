# Deriv API Configuration
DERIV_TOKEN = "PLACEHOLDER_DERIV_TOKEN"
APP_ID = "1089" # Default for deriv.com

# Strategy Parameters
EMA_FAST = 6
EMA_SLOW = 9
MACD_FAST = 5
MACD_SLOW = 35
MACD_SIGNAL = 5

# Trade Settings
INITIAL_STAKE = 0.35
DURATION_MINUTES = 10
TRADE_TYPE = "CALL"  # or "PUT" based on signal
CURRENCY = "USD"

# Risk Management (Reverse Martingale)
WIN_STAKE_MULTIPLIER = 1.5
MAX_WIN_STREAK = 5

# Symbols to Trade
VOLATILITY_INDICES = [
    "R_10", "R_25", "R_50", "R_75", "R_100",
    "1HZ10V", "1HZ25V", "1HZ50V", "1HZ75V", "1HZ100V"
]

# Database
DB_PATH = "data/lbot_trading.db"
