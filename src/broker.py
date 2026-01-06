import time
import os
import subprocess
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from config import MT5_PATH, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER

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
            authorized = mt5.login(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
            
            if authorized:
                print(f"   ✅ Login Successful!")
                if not mt5.terminal_info().trade_allowed:
                    print("   ⚠️ WARNING: 'Algo Trading' disabled! (Will try to fix via Config)")
                return self._verify_connection()
            else:
                print(f"   ❌ Login Failed: {mt5.last_error()}")
                return False
        except Exception as e:
            print(f"   ❌ Connection Exception: {e}")
            return False

    def _force_launch_mt5(self):
        """
        The Nuclear Option ☢️
        Generates a boot.ini file with credentials and 'ExpertsEnabled=1',
        then launches MT5 forcefully with this config.
        """
        try:
            # 1. Create the magic config file
            ini_content = f"""
[Common]
Login={MT5_LOGIN}
Password={MT5_PASSWORD}
Server={MT5_SERVER}
CertPassword=
ProxyEnable=0
ExpertsEnabled=1
NewsEnable=0
"""
            # Save it next to where we are running
            boot_file = os.path.abspath("boot.ini")
            with open(boot_file, "w") as f:
                f.write(ini_content)
            
            print(f"   📝 Generated Boot Config at: {boot_file}")

            # 2. Construct the Launch Command
            # We use /portable to keep data clean and /config to force settings
            cmd = [MT5_PATH, "/portable", f"/config:{boot_file}"]
            
            print(f"   🚀 Launching: {' '.join(cmd)}")
            
            # 3. Fire in the hole!
            # We use subprocess.Popen so we don't wait for it to close (it needs to stay open)
            subprocess.Popen(cmd)
            
            return True
        except Exception as e:
            print(f"   ❌ Bootloader Failed: {e}")
            return False

    def _verify_connection(self):
        try:
            account_info = mt5.account_info()
            if account_info:
                print(f"   📊 Account: {account_info.login} | Server: {account_info.server} | Balance: {account_info.balance}")
                self.connected = True
                return True
            else:
                print("   ⚠️ Connected, but NO Account Info.")
                return False
        except: return False

    def check_connection(self):
        return mt5.terminal_info() is not None

    def get_server_time_iso(self):
        dt = self.get_server_datetime()
        return dt.isoformat()

    def get_server_datetime(self):
        try:
            tick = mt5.symbol_info_tick("EURUSD")
            if tick: return datetime.fromtimestamp(tick.time)
            server_time = mt5.TimeCurrent()
            if server_time: return datetime.fromtimestamp(server_time)
        except: pass
        return datetime.now()

    def get_balance(self):
        info = mt5.account_info()
        return info.balance if info else 0.0

    def get_spread(self, pair):
        info = mt5.symbol_info(pair)
        if not info: return 0
        return info.spread
    
    def get_open_positions(self):
        if not self.check_connection(): return None
        return mt5.positions_get()

    def get_tick(self, pair):
        return mt5.symbol_info_tick(pair)

    def fetch_candles(self, pair, timeframe, limit=300):
        if not self.check_connection(): return pd.DataFrame()
        tf_map = {'1m': mt5.TIMEFRAME_M1, '5m': mt5.TIMEFRAME_M5, '15m': mt5.TIMEFRAME_M15, 
                  '30m': mt5.TIMEFRAME_M30, '1h': mt5.TIMEFRAME_H1, '4h': mt5.TIMEFRAME_H4, '1d': mt5.TIMEFRAME_D1}
        mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_M15)
        rates = mt5.copy_rates_from_pos(pair, mt5_tf, 0, limit)
        if rates is None or len(rates) == 0: return pd.DataFrame()
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def execute_trade(self, pair, signal, volume, sl, tp, comment):
        if pair in self.closed_markets:
            if time.time() < self.closed_markets[pair]: return None
            else: del self.closed_markets[pair] 

        tick = mt5.symbol_info_tick(pair)
        if not tick: return None
        
        price = tick.ask if signal == 'BUY' else tick.bid
        action_type = mt5.ORDER_TYPE_BUY if signal == 'BUY' else mt5.ORDER_TYPE_SELL
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pair,
            "volume": float(volume),
            "type": action_type,
            "price": float(price),
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": 234000,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = result.comment if result else "Unknown Error"
            print(f"❌ Order Failed ({pair}): {error_msg}")
            self.closed_markets[pair] = time.time() + 60 
            return None
        return result

    def modify_position(self, ticket, sl, tp):
        request = {"action": mt5.TRADE_ACTION_SLTP, "position": int(ticket), "sl": float(sl), "tp": float(tp), "magic": 234000}
        result = mt5.order_send(request)
        if result is None: return False
        return result.retcode == mt5.TRADE_RETCODE_DONE

    def close_trade(self, ticket, symbol, volume, is_long):
        tick = mt5.symbol_info_tick(symbol)
        if not tick: return False
        
        price = tick.bid if is_long else tick.ask
        type_op = mt5.ORDER_TYPE_SELL if is_long else mt5.ORDER_TYPE_BUY
        
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
            "type_filling": mt5.ORDER_FILLING_IOC,
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
                    'close_time': datetime.fromtimestamp(last_deal.time).isoformat(),
                    'comment': last_deal.comment
                }
        except Exception as e:
            print(f"⚠️ History Check Error: {e}")
        return {'status': 'unknown'}
