import pandas as pd
import pandas_ta as ta
import httpx
import numpy as np

class SMCAnalyzer:
    """
    SMC (Smart Money Concepts) Analysis Engine using real market data.
    """

    @staticmethod
    async def fetch_data(symbol="BTCUSDT", interval="1h", limit=100):
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                if response.status_code != 200:
                    return pd.DataFrame()
                data = response.json()
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
                df['close'] = df['close'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                return df
            except Exception as e:
                print(f"Error fetching data: {e}")
                return pd.DataFrame()

    @staticmethod
    async def get_analysis(pair):
        # Map pair to Binance symbols
        symbol_map = {"XAUUSD": "PAXGUSDT", "BTCUSD": "BTCUSDT", "EURUSD": "EURUSDT", "GBPUSD": "GBPUSDT"}
        symbol = symbol_map.get(pair, "BTCUSDT")

        df = await SMCAnalyzer.fetch_data(symbol)
        if df.empty:
            return {"pair": pair, "type": "HOLD", "entry": "0", "tp": "0", "sl": "0", "strength": "Low", "time": "N/A"}

        # Basic Technical Analysis for Bias
        df['sma_50'] = ta.sma(df['close'], length=50)

        current_price = df['close'].iloc[-1]
        # Use simple mean if sma_50 is nan (warmup)
        sma_val = df['sma_50'].iloc[-1]
        if np.isnan(sma_val):
            sma_val = df['close'].mean()

        # Simple SMC-like logic: Bias based on price vs SMA
        bias = "BUY" if current_price > sma_val else "SELL"

        # Mocking Order Block as recent swing high/low
        if bias == "BUY":
            entry = df['low'].iloc[-10:].min()
            tp = current_price + (current_price - entry) * 2
            sl = entry * 0.99
            strength = "Strong" if current_price > sma_val else "Moderate"
        else:
            entry = df['high'].iloc[-10:].max()
            tp = current_price - (entry - current_price) * 2
            sl = entry * 1.01
            strength = "Strong" if current_price < sma_val else "Moderate"

        return {
            "pair": pair,
            "type": bias,
            "entry": f"{entry:.2f}" if entry > 1 else f"{entry:.4f}",
            "tp": f"{tp:.2f}" if tp > 1 else f"{tp:.4f}",
            "sl": f"{sl:.2f}" if sl > 1 else f"{sl:.4f}",
            "time": "Just now",
            "strength": strength
        }

    @staticmethod
    async def generate_signal(pair):
        return await SMCAnalyzer.get_analysis(pair)
