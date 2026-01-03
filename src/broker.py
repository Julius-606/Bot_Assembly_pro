import time
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

class BrokerAPI:
    """
    The Middleman. 👔
    Talks to MetaTrader 5 so you don't have to.
    """
    def __init__(self):
        self.connected = False
        self.closed_markets = {} 

    def startup(self):
        if not mt5.initialize():
            print(f"❌ MT5 Init Failed: {mt5.last_error()}")
            return False
        
        account_info = mt5.account_info()
        if account_info:
            print(f"✅ MT5 Connected to {account_info.server} (Account: {account_info.login})")
            self.connected = True
            return True
        return False

    def check_connection(self):
        return mt5.terminal_info() is not None

    def get_server_time_iso(self):
        """Returns ISO format string for logging. No more local PC time lies."""
        dt = self.get_server_datetime()
        return dt.isoformat()

    def get_server_datetime(self):
        """
        Returns a proper datetime object of the Server Time.
        Used for 'Monday' and 'Weekend' logic to ensure we are synced with New York/Broker time.
        """
        try:
            # Try getting time from a major pair (most accurate)
            tick = mt5.symbol_info_tick("EURUSD")
            if tick:
                return datetime.fromtimestamp(tick.time)
            
            # Fallback to general Server Time
            server_time = mt5.TimeCurrent()
            if server_time:
                return datetime.fromtimestamp(server_time)
                
        except Exception as e:
            print(f"⚠️ Time Fetch Error: {e}")
            
        # Ultimate Fallback: Local PC Time (Keeps the bot alive, but barely)
        return datetime.now()

    def get_balance(self):
        """Returns the actual account balance (Equity? No, Balance. We don't realize floating PnL)."""
        info = mt5.account_info()
        return info.balance if info else 0.0

    def get_tick(self, pair):
        return mt5.symbol_info_tick(pair)

    def get_spread(self, pair):
        info = mt5.symbol_info(pair)
        if not info: return 0
        # Spread is usually in points
        return info.spread
    
    def fetch_candles(self, pair, timeframe, limit=300):
        """
        Fetches historical candle data for strategy calculation.
        """
        if not self.check_connection(): return pd.DataFrame()
        
        # Map string timeframe to MT5 constant
        tf_map = {
            '1m': mt5.TIMEFRAME_M1,
            '5m': mt5.TIMEFRAME_M5,
            '15m': mt5.TIMEFRAME_M15,
            '30m': mt5.TIMEFRAME_M30,
            '1h': mt5.TIMEFRAME_H1,
            '4h': mt5.TIMEFRAME_H4,
            '1d': mt5.TIMEFRAME_D1,
        }
        
        mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_M15)
        
        rates = mt5.copy_rates_from_pos(pair, mt5_tf, 0, limit)
        
        if rates is None or len(rates) == 0:
            return pd.DataFrame()
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        return df

    def execute_trade(self, pair, signal, volume, sl, tp, comment):
        # Cooldown check
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
            # Penalty box for 60 seconds
            self.closed_markets[pair] = time.time() + 60 
            return None
             
        return result

    def modify_position(self, ticket, sl, tp):
        """
        Updates the SL/TP on the Server Side. 
        """
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(ticket),
            "sl": float(sl),
            "tp": float(tp),
            "magic": 234000,
        }
        result = mt5.order_send(request)
        if result is None:
            return False
        return result.retcode == mt5.TRADE_RETCODE_DONE

    def close_trade(self, ticket, symbol, volume, is_long):
        """Manual Close for Strategy Exits or Emergencies."""
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
            "comment": "Bot Exit",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None:
            return False
        return result.retcode == mt5.TRADE_RETCODE_DONE

    def check_trade_status(self, ticket):
        """
        Checks if the trade is alive. 
        If closed, fetches the Real PnL from history.
        """
        # 1. Is it still open?
        positions = mt5.positions_get(ticket=int(ticket))
        if positions:
            return {'status': 'open'}

        # 2. If not open, it's closed. Fetch History to find out why/how much.
        try:
            history = mt5.history_deals_get(position=int(ticket))
            if history:
                # Sum profit + swap + commission
                total_profit = sum([d.profit + d.swap + d.commission for d in history])
                # Accessing the last deal for exit info
                last_deal = history[-1]
                exit_price = last_deal.price
                close_time_ts = last_deal.time
                
                return {
                    'status': 'closed',
                    'pnl': round(total_profit, 2),
                    'exit_price': exit_price,
                    'close_time': datetime.fromtimestamp(close_time_ts).isoformat()
                }
        except Exception as e:
            print(f"⚠️ History Check Error: {e}")
            
        return {'status': 'unknown'}