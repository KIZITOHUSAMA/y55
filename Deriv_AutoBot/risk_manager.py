from datetime import datetime, timedelta

class RiskManager:
    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.consecutive_losses = 0
        self.pause_until = None

    def can_trade(self, account_info):
        if self.pause_until and datetime.now() < self.pause_until:
            return False, f"Paused until {self.pause_until}"

        # Session Time Check (EAT)
        now_hour = datetime.now().hour
        in_session = False
        for session_name, params in self.config.SESSIONS.items():
            start = params['start']
            end = params['end']
            if start < end:
                if start <= now_hour < end:
                    in_session = True
                    break
            else: # Overnight session
                if now_hour >= start or now_hour < end:
                    in_session = True
                    break

        if not in_session:
            return False, "Outside trading sessions"

        # Daily Drawdown check
        daily_profit = self.db.get_daily_profit()
        balance = account_info['balance']
        max_loss = balance * (self.config.MAX_DAILY_LOSS_PERCENT / 100)

        if daily_profit < -max_loss:
            return False, "Daily loss limit reached"

        return True, "OK"

    def update_loss_streak(self, last_trade_profit):
        if last_trade_profit < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.config.CONSECUTIVE_LOSS_LIMIT:
                self.pause_until = datetime.now() + timedelta(hours=self.config.PAUSE_AFTER_LOSS_LIMIT_HOURS)
                self.consecutive_losses = 0  # Reset after setting pause
        else:
            self.consecutive_losses = 0

    def calculate_lot(self, symbol_info, risk_percent, sl_points):
        # Simplest approach for Deriv: use minimum volume
        # Or calculate based on balance/risk if SL is provided
        return symbol_info.volume_min

    def check_spread(self, symbol, tick, symbol_info):
        spread = (tick.ask - tick.bid) / symbol_info.point

        limit = self.config.MAX_SPREAD_POINTS.get("Volatility", 50) # Default
        for key, val in self.config.MAX_SPREAD_POINTS.items():
            if key in symbol:
                limit = val
                break

        return spread <= limit, spread
