import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Signals Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol TEXT,
                signal_type TEXT,
                ema_fast REAL,
                ema_slow REAL,
                rsi REAL,
                atr REAL,
                spread REAL
            )
        ''')

        # Trades Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                ticket INTEGER PRIMARY KEY,
                symbol TEXT,
                type TEXT,
                entry_price REAL,
                exit_price REAL,
                profit REAL,
                open_time DATETIME,
                close_time DATETIME,
                status TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def log_signal(self, symbol, signal_type, ema_fast, ema_slow, rsi, atr, spread):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO signals (symbol, signal_type, ema_fast, ema_slow, rsi, atr, spread)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, signal_type, ema_fast, ema_slow, rsi, atr, spread))
        conn.commit()
        conn.close()

    def log_trade_open(self, ticket, symbol, trade_type, entry_price, open_time):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades (ticket, symbol, type, entry_price, open_time, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ticket, symbol, trade_type, entry_price, open_time, 'OPEN'))
        conn.commit()
        conn.close()

    def log_trade_close(self, ticket, exit_price, profit, close_time):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE trades
            SET exit_price = ?, profit = ?, close_time = ?, status = ?
            WHERE ticket = ?
        ''', (exit_price, profit, close_time, 'CLOSED', ticket))
        conn.commit()
        conn.close()

    def get_daily_profit(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT SUM(profit) FROM trades
            WHERE date(close_time) = ? AND status = 'CLOSED'
        ''', (today,))
        result = cursor.fetchone()[0]
        conn.close()
        return result if result else 0.0
