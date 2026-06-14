import sqlite3
import os
from datetime import datetime

class LBotDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol TEXT,
                contract_id INTEGER,
                type TEXT,
                stake REAL,
                payout REAL,
                status TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def log_trade(self, symbol, contract_id, trade_type, stake):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades (symbol, contract_id, type, stake, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (symbol, contract_id, trade_type, stake, 'OPEN'))
        conn.commit()
        conn.close()

    def update_trade_result(self, contract_id, payout, status):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE trades
            SET payout = ?, status = ?
            WHERE contract_id = ?
        ''', (payout, status, contract_id))
        conn.commit()
        conn.close()

    def get_last_result(self, symbol):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT status FROM trades
            WHERE symbol = ? AND status != 'OPEN'
            ORDER BY timestamp DESC LIMIT 1
        ''', (symbol,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def get_win_streak(self, symbol):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT status FROM trades
            WHERE symbol = ? AND status != 'OPEN'
            ORDER BY timestamp DESC LIMIT 10
        ''', (symbol,))
        results = cursor.fetchall()
        conn.close()

        streak = 0
        for r in results:
            if r[0] == 'WON':
                streak += 1
            else:
                break
        return streak
