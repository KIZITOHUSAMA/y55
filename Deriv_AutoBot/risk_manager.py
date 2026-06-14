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

    def calculate_lot(self, symbol_info, balance, risk_percent, sl_points):
        """
        Calculates the lot size based on account balance and risk per trade.
        """
        if sl_points <= 0:
            return symbol_info.volume_min

        risk_amount = balance * (risk_percent / 100)

        # Calculate lot size based on point value if available, else simple ratio
        # For many Deriv indices, volume * sl_points = loss
        lot = risk_amount / sl_points if sl_points != 0 else symbol_info.volume_min

        # Clamp to symbol limits
        lot = max(symbol_info.volume_min, min(symbol_info.volume_max, lot))

        # Round to step
        step = symbol_info.volume_step
        if step > 0:
            lot = round(lot / step) * step

        return round(lot, 2)

    def check_spread(self, symbol, tick, symbol_info):
        spread = (tick.ask - tick.bid) / symbol_info.point

        limit = self.config.MAX_SPREAD_POINTS.get("Volatility", 50) # Default
        for key, val in self.config.MAX_SPREAD_POINTS.items():
            if key in symbol:
                limit = val
                break

        return spread <= limit, spread
