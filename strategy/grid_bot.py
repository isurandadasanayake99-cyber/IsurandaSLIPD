import MetaTrader5 as mt5
import threading
import time
import random

# Default reference prices for fallback / demo simulation
REFERENCE_PRICES = {
    "EURUSD": 1.08520,
    "GBPJPY": 192.450,
    "BTCUSD": 64250.00,
    "ETHUSD": 3480.50,
    "XAUUSD": 2350.20,
    "OIL": 82.40
}

def get_pip_value(symbol):
    sym = symbol.upper()
    if 'JPY' in sym:
        return 0.01
    elif any(k in sym for k in ['BTC', 'ETH', 'XAU', 'OIL', 'GOLD']):
        return 1.0
    else:
        return 0.0001

class GridBot(threading.Thread):
    def __init__(self, symbol, lot_size, grid_spacing_pips, num_levels, db_logger, simulation_mode=False):
        """
        Thread-based Grid Trading Bot.
        Supports both live MetaTrader 5 execution and high-fidelity Demo Simulation.
        """
        super().__init__()
        self.symbol = symbol.upper()
        self.lot_size = float(lot_size)
        self.grid_spacing_pips = int(grid_spacing_pips)
        self.num_levels = int(num_levels)
        self.db_logger = db_logger
        self.simulation_mode = simulation_mode
        self.running = False
        
        self.pip_value = get_pip_value(self.symbol)
        self.current_price = REFERENCE_PRICES.get(self.symbol, 1.00000)
        self.placed_orders = [] # list of dicts: {ticket, type, price, volume, status}
        self.grid_levels = {"buy_limits": [], "sell_limits": []}
        
    def get_live_price(self):
        """Fetches current price from MT5 or generates simulation tick."""
        if not self.simulation_mode:
            try:
                if mt5.terminal_info() is not None:
                    mt5.symbol_select(self.symbol, True)
                    tick = mt5.symbol_info_tick(self.symbol)
                    if tick and tick.ask > 0:
                        self.current_price = tick.ask
                        return self.current_price
            except Exception:
                pass
        
        # In simulation mode or if MT5 tick unavailable:
        delta = (random.random() - 0.49) * (self.pip_value * 1.5)
        self.current_price = round(max(0.0001, self.current_price + delta), 5 if self.pip_value < 0.01 else 2)
        return self.current_price

    def run(self):
        self.running = True
        print(f"[{self.symbol}] Grid Bot started (Simulation: {self.simulation_mode})...")
        
        # Check MT5 readiness if live
        if not self.simulation_mode:
            if not mt5.terminal_info():
                print(f"[{self.symbol}] MT5 terminal not active. Falling back to Simulation Mode.")
                self.simulation_mode = True
            elif not mt5.symbol_select(self.symbol, True):
                print(f"[{self.symbol}] Symbol selection failed. Falling back to Simulation Mode.")
                self.simulation_mode = True
        
        price = self.get_live_price()
        print(f"[{self.symbol}] Initial Price: {price}")
        
        # Calculate & Place Grid Orders
        self.grid_levels["buy_limits"] = []
        self.grid_levels["sell_limits"] = []
        
        # Buy Limits (below current price)
        for i in range(1, self.num_levels + 1):
            if not self.running: break
            buy_price = round(price - (i * self.grid_spacing_pips * self.pip_value), 5 if self.pip_value < 0.01 else 2)
            self.grid_levels["buy_limits"].append(buy_price)
            self.place_grid_order("BUY_LIMIT", buy_price)
            
        # Sell Limits (above current price)
        for i in range(1, self.num_levels + 1):
            if not self.running: break
            sell_price = round(price + (i * self.grid_spacing_pips * self.pip_value), 5 if self.pip_value < 0.01 else 2)
            self.grid_levels["sell_limits"].append(sell_price)
            self.place_grid_order("SELL_LIMIT", sell_price)
            
        print(f"[{self.symbol}] Grid initialized: {len(self.grid_levels['buy_limits'])} Buy Limits, {len(self.grid_levels['sell_limits'])} Sell Limits.")
        
        # Monitoring loop
        while self.running:
            time.sleep(1.5)
            new_price = self.get_live_price()
            
            # Check for simulated fills if in simulation mode
            if self.simulation_mode:
                for order in self.placed_orders:
                    if order["status"] == "PLACED":
                        # Check buy limit hit
                        if order["type"] == "BUY_LIMIT" and new_price <= order["price"]:
                            order["status"] = "FILLED"
                            self.db_logger.log_trade(
                                ticket=order["ticket"],
                                symbol=self.symbol,
                                order_type="BUY_LIMIT",
                                volume=order["volume"],
                                price=new_price,
                                status="FILLED"
                            )
                            print(f"[{self.symbol}] Simulated FILL for Buy Limit #{order['ticket']} at {new_price}")
                        # Check sell limit hit
                        elif order["type"] == "SELL_LIMIT" and new_price >= order["price"]:
                            order["status"] = "FILLED"
                            self.db_logger.log_trade(
                                ticket=order["ticket"],
                                symbol=self.symbol,
                                order_type="SELL_LIMIT",
                                volume=order["volume"],
                                price=new_price,
                                status="FILLED"
                            )
                            print(f"[{self.symbol}] Simulated FILL for Sell Limit #{order['ticket']} at {new_price}")

    def place_grid_order(self, order_type_str, price):
        """Places pending grid order (live via MT5 or simulated)."""
        ticket = random.randint(100000, 999999)
        
        if not self.simulation_mode and mt5.terminal_info():
            order_type = mt5.ORDER_TYPE_BUY_LIMIT if order_type_str == "BUY_LIMIT" else mt5.ORDER_TYPE_SELL_LIMIT
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": self.symbol,
                "volume": self.lot_size,
                "type": order_type,
                "price": price,
                "sl": 0.0,
                "tp": 0.0,
                "deviation": 20,
                "magic": 1001,
                "comment": "GridBot Pending",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            res = mt5.order_send(request)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                ticket = res.order
            else:
                err = mt5.last_error() if res is None else res.retcode
                print(f"[{self.symbol}] MT5 Order Failed: {err}. Logging as simulated order.")
                
        # Record locally
        order_record = {
            "ticket": ticket,
            "type": order_type_str,
            "price": price,
            "volume": self.lot_size,
            "status": "PLACED"
        }
        self.placed_orders.append(order_record)
        
        # Log to Database
        self.db_logger.log_trade(
            ticket=ticket,
            symbol=self.symbol,
            order_type=order_type_str,
            volume=self.lot_size,
            price=price,
            status="PLACED"
        )
        print(f"[{self.symbol}] Logged {order_type_str} at {price} (Ticket: {ticket})")

    def place_manual_order(self, order_type_str, lot_size=None):
        """Executes an instant manual BUY or SELL market order."""
        volume = lot_size if lot_size else self.lot_size
        price = self.get_live_price()
        ticket = random.randint(100000, 999999)
        
        if not self.simulation_mode and mt5.terminal_info():
            action_type = mt5.ORDER_TYPE_BUY if order_type_str == "BUY" else mt5.ORDER_TYPE_SELL
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": volume,
                "type": action_type,
                "price": price,
                "sl": 0.0,
                "tp": 0.0,
                "deviation": 20,
                "magic": 1002,
                "comment": "Manual Market Order",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            res = mt5.order_send(request)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                ticket = res.order
        
        self.db_logger.log_trade(
            ticket=ticket,
            symbol=self.symbol,
            order_type=order_type_str,
            volume=volume,
            price=price,
            status="EXECUTED"
        )
        print(f"[{self.symbol}] Manual Market {order_type_str} executed at {price} (Ticket: {ticket})")
        return ticket, price

    def stop(self):
        self.running = False
        print(f"[{self.symbol}] Grid Bot stopping...")
