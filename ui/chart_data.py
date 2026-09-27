import numpy as np
import random
import time

class MarketDataManager:
    """
    Provides realistic historical candlestick data and live tick updates
    for trading pairs, supporting MT5 live data with simulation fallback.
    """
    def __init__(self):
        self.base_prices = {
            "EUR/USD": 1.08520,
            "GBP/JPY": 192.450,
            "BTC/USD": 64250.00,
            "ETH/USD": 3480.50,
            "XAU/USD": 2350.20,
            "OIL/WTI": 82.40
        }
        self.volatilities = {
            "EUR/USD": 0.0003,
            "GBP/JPY": 0.08,
            "BTC/USD": 120.0,
            "ETH/USD": 8.0,
            "XAU/USD": 2.5,
            "OIL/WTI": 0.3
        }
        # Cache for candles: { symbol: [ {open, high, low, close, volume, time} ] }
        self.history = {}
        for sym in self.base_prices:
            self.history[sym] = self._generate_initial_candles(sym, num_candles=45)

    def _generate_initial_candles(self, symbol, num_candles=45):
        base = self.base_prices.get(symbol, 100.0)
        vol = self.volatilities.get(symbol, base * 0.002)
        candles = []
        current = base - (vol * num_candles * 0.2)
        
        for i in range(num_candles):
            change = (random.random() - 0.48) * vol * 2.0
            o = current
            c = o + change
            h = max(o, c) + abs(random.gauss(0, vol * 0.7))
            l = min(o, c) - abs(random.gauss(0, vol * 0.7))
            v = random.randint(800, 15000)
            candles.append({
                "open": round(o, 5 if vol < 0.01 else 2),
                "high": round(h, 5 if vol < 0.01 else 2),
                "low": round(l, 5 if vol < 0.01 else 2),
                "close": round(c, 5 if vol < 0.01 else 2),
                "volume": v
            })
            current = c
        return candles

    def get_candles(self, symbol):
        sym = symbol.replace("/", "")
        for key in self.history:
            if key.replace("/", "") == sym:
                return self.history[key]
        return self._generate_initial_candles(symbol, 45)

    def update_tick(self, symbol, live_price=None):
        """Appends/updates latest candle with a new tick."""
        sym = None
        for key in self.history:
            if key.replace("/", "") == symbol.replace("/", ""):
                sym = key
                break
        if not sym:
            sym = symbol
            self.history[sym] = self._generate_initial_candles(sym, 45)
            
        candles = self.history[sym]
        vol = self.volatilities.get(sym, candles[-1]["close"] * 0.001)
        
        last = candles[-1]
        if live_price is not None and live_price > 0:
            price = live_price
        else:
            delta = (random.random() - 0.49) * vol * 0.4
            price = round(last["close"] + delta, 5 if vol < 0.01 else 2)
            
        last["close"] = price
        last["high"] = max(last["high"], price)
        last["low"] = min(last["low"], price)
        last["volume"] += random.randint(10, 50)
        
        # Every ~30 ticks or so, spawn a new candle
        if random.random() < 0.05 and len(candles) < 70:
            candles.append({
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": random.randint(100, 500)
            })
            if len(candles) > 60:
                candles.pop(0)
                
        return price
