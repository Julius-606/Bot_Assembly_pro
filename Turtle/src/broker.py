import time
import os
import subprocess
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from config import MT5_PATH, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, FIXED_LOT_SIZE

class BrokerAPI:
    """
    The Middleman. 👔
    Talks to MetaTrader 5 so you don't have to.
    """
    def __init__(self):
        self.connected = False
        self.closed_markets = {} 

    def startup(self):
        print(f"   🕵️  Scanning for MT5...")
        
        # 1. ATTEMPT NORMAL CONNECTION
        if self._try_connect():
            return True
        
        # 2. IF FAILED, DEPLOY THE BATTERING RAM
        print("   ⚠️ Standard connection failed. Deploying HEADLESS BOOTLOADER...")
        if self._force_launch_mt5():
            print("   ⏳ Waiting for Headless MT5 to stabilize...")
            time.sleep(15) # Give it time to log in
            return self._try_connect()
            
        return False

    def _try_connect(self):
        """Standard Connection Attempt"""
        try:
            # We use the path specifically
            if not mt5.initialize(path=MT5_PATH, timeout=20000): # 20s timeout
                return False
            
            # Login Check
            print(f"   🔑 Authenticating with account {MT5_LOGIN}...")
            if not mt5.login(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
                print(f"   ❌ Login Failed: {mt5.last_error()}")
                return False
            
            self.connected = True
            print("   ✅ Connected to MT5 Grid!")
            return True
        except Exception as e:
            print(f"   ❌ Connection Error: {e}")
            return False

    def _force_launch_mt5(self):
        """Launches MT5 if it's not running (Linux/Wine friendly)"""
        try:
            subprocess.Popen(MT5_PATH)
            return True
        except Exception as e:
            print(f"   ❌ Failed to launch MT5: {e}")
            return False

    def get_data(self, symbol, timeframe, n=200):
        if not self.connected: return None
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
        if rates is None: return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_spread(self, symbol):
        info = mt5.symbol_info(symbol)
        if info:
            return info.spread
        return 0

    def get_open_positions(self):
        if not self.connected: return []
        return mt5.positions_get()

    def calc_position_size(self, symbol, stop_loss, risk=0.01):
        # 🛡️ SAFETY OVERRIDE
        return FIXED_LOT_SIZE

    def validate_sl_for_risk(self, symbol, is_long, entry, proposed_sl, volume, risk_limit_usd):
        """
        🛡️ The Enforcer.
        Checks if the proposed SL exceeds the dollar risk limit.
        If it does, it calculates a NEW SL that respects the limit.
        Returns: (new_sl, was_adjusted)
        """
        if not self.connected: return proposed_sl, False

        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info: return proposed_sl, False

        # Calculate Contract Size (e.g., 100,000 for Forex, 100 for Gold)
        contract_size = symbol_info.trade_contract_size
        
        # Calculate Potential Loss in Quote Currency
        # Loss = Volume * ContractSize * PriceDifference
        price_diff = abs(entry - proposed_sl)
        potential_loss = volume * contract_size * price_diff

        # If we are within limits, return original
        if potential_loss <= risk_limit_usd:
            return proposed_sl, False

        # If we exceeded limit, calculate MAX allowed price difference
        # MaxDiff = RiskLimit / (Volume * ContractSize)
        max_price_diff = risk_limit_usd / (volume * contract_size)

        # Apply new diff to entry
        if is_long:
            new_sl = entry - max_price_diff
        else:
            new_sl = entry + max_price_diff

        # Round to digits
        new_sl = round(new_sl, symbol_info.digits)
        
        return new_sl, True

    def get_filling_mode(self, symbol):
        """
        Dynamically finds the supported filling mode for the symbol.
        Uses raw bitmask integers to avoid AttributeError on some MT5 libs.
        """
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            return mt5.ORDER_FILLING_IOC 

        filling_modes = symbol_info.filling_mode
        
        # 2 = SYMBOL_FILLING_IOC
        # 1 = SYMBOL_FILLING_FOK
        
        # Prioritize IOC (2), then FOK (1), then RETURN
        if (filling_modes & 2):
            return mt5.ORDER_FILLING_IOC
        elif (filling_modes & 1):
            return mt5.ORDER_FILLING_FOK
        else:
            return mt5.ORDER_FILLING_RETURN

    def execute_trade(self, symbol, signal, volume, sl, tp, comment):
        if not self.connected: return None
        
        # 🛠️ GET SYMBOL INFO & DIGITS FOR NORMALIZATION
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"   ❌ Symbol {symbol} not found")
            return None
            
        digits = symbol_info.digits
        
        is_long = signal == 'BUY'
        type_op = mt5.ORDER_TYPE_BUY if is_long else mt5.ORDER_TYPE_SELL
        
        # Get Price and NORMALIZE everything
        tick = mt5.symbol_info_tick(symbol)
        price = tick.ask if is_long else tick.bid
        
        price = round(price, digits)
        sl = round(sl, digits)
        tp = round(tp, digits)
        
        # 🛠️ GET CORRECT FILLING MODE
        fill_mode = self.get_filling_mode(symbol)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": type_op,
            "price": float(price),
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": 234000,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": fill_mode, 
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"   ❌ Trade Failed: {result.comment} (Retcode: {result.retcode})")
            return None
        return result

    def close_trade(self, ticket, symbol, volume, is_long):
        # Close opposite to open
        type_op = mt5.ORDER_TYPE_SELL if is_long else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if is_long else mt5.symbol_info_tick(symbol).ask
        
        # 🛠️ GET CORRECT FILLING MODE
        fill_mode = self.get_filling_mode(symbol)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": type_op,
            "position": int(ticket),
            "price": float(price),
            "deviation": 20,
            "magic": 234000,
            "comment": "Friday Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": fill_mode, 
        }
        result = mt5.order_send(request)
        if result is None: return False
        return result.retcode == mt5.TRADE_RETCODE_DONE

    def check_trade_status(self, ticket):
        positions = mt5.positions_get(ticket=int(ticket))
        if positions: return {'status': 'open'}

        try:
            history = mt5.history_deals_get(position=int(ticket))
            if history:
                total_profit = sum([d.profit + d.swap + d.commission for d in history])
                last_deal = history[-1]
                return {
                    'status': 'closed',
                    'pnl': round(total_profit, 2),
                    'exit_price': last_deal.price,
                    'close_time': datetime.fromtimestamp(last_deal.time).strftime("%Y-%m-%d %H:%M:%S")
                }
        except:
            pass
        return {'status': 'unknown'}