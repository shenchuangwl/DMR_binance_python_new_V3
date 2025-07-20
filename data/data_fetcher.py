import pandas as pd
import os
import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

import ccxt
# 导入部分
from config.config import (
    API_KEY, API_SECRET, SYMBOL, TIMEFRAME_LONG as TIMEFRAME, 
    POSITION_SIZE, MA_LONG_PERIOD, MA_SHORT_PERIOD,
    DATA_FETCHER_CONFIG, ORDER_EXECUTOR_CONFIG
)

class DataFetcher:
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'enableRateLimit': DATA_FETCHER_CONFIG['rate_limit'],
            'options': {
                'defaultType': ORDER_EXECUTOR_CONFIG['default_type'],
                'adjustForTimeDifference': ORDER_EXECUTOR_CONFIG['adjust_for_time_diff'],
                'recvWindow': DATA_FETCHER_CONFIG['recv_window']
            }
        })
        # 手动同步时间差异
        self.time_offset = 0
        self.last_time_sync = 0
        # 初始化时强制同步时间
        self.sync_time(force=True)
    
    def sync_time(self, force=False):
        """
        同步本地时间与服务器时间
        force: 是否强制同步，即使上次同步时间未超过阈值
        """
        current_time = int(time.time() * 1000)
        sync_interval = DATA_FETCHER_CONFIG['sync_interval']
        
        # 如果距离上次同步已经超过配置的间隔或强制同步
        if force or (current_time - self.last_time_sync > sync_interval):
            max_retries = DATA_FETCHER_CONFIG['max_retries']
            retry_count = 0
            while retry_count < max_retries:
                try:
                    # 直接调用Binance的/api/v3/time接口获取服务器时间
                    response = self.exchange.publicGetTime()
                    server_time = int(response['serverTime'])  # 确保转换为整数
                    local_time = int(time.time() * 1000)
                    self.time_offset = server_time - local_time
                    self.last_time_sync = current_time
                    print(f"时间同步成功: 服务器时间={server_time}, 本地时间={local_time}, 偏移={self.time_offset}ms")
                    break
                except Exception as e:
                    retry_count += 1
                    print(f"时间同步失败 (尝试 {retry_count}/{max_retries}): {e}")
                    if retry_count < max_retries:
                        time.sleep(1)  # 等待1秒后重试
                    else:
                        print("时间同步最终失败，使用本地时间")
                        self.time_offset = 0
    
    def get_timestamp(self):
        """
        获取调整后的时间戳
        """
        return int(time.time() * 1000) + self.time_offset
    
    def get_server_time(self):
        """
        获取服务器时间
        """
        try:
            response = self.exchange.publicGetTime()
            return response['serverTime']
        except Exception as e:
            print(f"获取服务器时间失败: {e}")
            return self.get_timestamp()
    
    def get_historical_data(self, symbol, timeframe, limit=None):
        """
        获取历史K线数据
        
        Args:
            symbol: 交易对符号
            timeframe: 时间周期
            limit: 数据条数限制，如果为None则使用配置文件中的默认值
        
        Returns:
            DataFrame: 包含OHLCV数据的DataFrame
        """
        if limit is None:
            limit = DATA_FETCHER_CONFIG['data_limit']
            
        max_retries = DATA_FETCHER_CONFIG['max_retries']
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 确保时间同步
                self.sync_time()
                
                # 添加时间戳参数
                params = {
                    'timestamp': self.get_timestamp(),
                    'recvWindow': DATA_FETCHER_CONFIG['recv_window']
                }
                
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit, params=params)
                
                if ohlcv:
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    print(f"成功获取 {symbol} {timeframe} 数据，共 {len(df)} 条记录")
                    return df
                else:
                    print(f"获取 {symbol} {timeframe} 数据为空")
                    return None
                    
            except Exception as e:
                retry_count += 1
                print(f"获取历史数据失败 (尝试 {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    time.sleep(2)  # 等待2秒后重试
                else:
                    print("获取历史数据最终失败")
                    return None
    
    def save_data_to_csv(self, df, filename):
        """将数据保存到CSV文件"""
        if df is not None:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            df.to_csv(filename)
            print(f"Data saved to {filename}")
            return True
        else:
            print(f"No data to save to {filename}")
            return False

    def get_account_balance(self):
        """获取账户余额信息"""
        try:
            # 强制同步时间
            self.sync_time(force=True)
            
            # 添加时间戳和接收窗口参数
            params = {
                'timestamp': self.get_timestamp(),
                'recvWindow': 60000
            }
            
            balance = self.exchange.fetch_balance(params=params)
            total_balance = balance['total']
            used_balance = balance['used']
            free_balance = balance['free']
            
            # 获取USDT余额
            usdt_total = total_balance.get('USDT', 0)
            usdt_used = used_balance.get('USDT', 0)
            usdt_free = free_balance.get('USDT', 0)
            
            return {
                'total_usdt': usdt_total,
                'used_usdt': usdt_used,
                'free_usdt': usdt_free,
                'total_balance': total_balance
            }
        except Exception as e:
            print(f"获取账户余额失败: {e}")
            return None
    
    def get_open_orders(self, symbol=None):
        """获取未完成订单"""
        try:
            # 强制同步时间
            self.sync_time(force=True)
            
            # 添加时间戳和接收窗口参数
            params = {
                'timestamp': self.get_timestamp(),
                'recvWindow': 60000
            }
            
            orders = self.exchange.fetch_open_orders(symbol, params=params)
            return orders
        except Exception as e:
            print(f"获取未完成订单失败: {e}")
            return []
    
    def get_positions(self, symbol=None):
        """获取当前持仓信息"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 强制同步时间
                self.sync_time(force=True)
                
                # 使用正确的API版本和参数
                params = {
                    'timestamp': self.get_timestamp(),
                    'recvWindow': 60000  # 增加接收窗口时间到60秒
                }
                
                # 将symbol转换为数组格式
                symbols = [symbol] if symbol else None
                positions = self.exchange.fetch_positions(symbols, params=params)
                
                # 过滤有效持仓（合约数量大于0）
                active_positions = [p for p in positions if float(p['contracts']) > 0]
                
                # 如果成功获取数据，打印详细信息用于调试
                if symbol:
                    print(f"成功获取{symbol}持仓信息，共{len(active_positions)}个活跃持仓")
                else:
                    print(f"成功获取所有持仓信息，共{len(active_positions)}个活跃持仓")
                    
                return active_positions
                
            except Exception as e:
                retry_count += 1
                print(f"获取持仓信息失败 (尝试 {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    # 等待一段时间后重试
                    time.sleep(2)
                else:
                    print(f"达到最大重试次数，无法获取持仓信息")
                    return []
    
    def get_recent_trades(self, symbol, limit=20):
        """获取最近的交易记录"""
        try:
            # 强制同步时间
            self.sync_time(force=True)
            
            # 添加时间戳和接收窗口参数
            params = {
                'timestamp': self.get_timestamp(),
                'recvWindow': 60000
            }
            
            trades = self.exchange.fetch_my_trades(symbol, limit=limit, params=params)
            return trades
        except Exception as e:
            print(f"获取交易记录失败: {e}")
            return []

    def get_server_time(self):
        """
        获取交易所服务器时间，并返回datetime对象
        同时确保本地时间与服务器时间同步
        """
        try:
            # 强制同步时间
            self.sync_time(force=True)
            
            # 获取服务器时间
            response = self.exchange.publicGetTime()
            server_time = int(response['serverTime'])  # 确保转换为整数
            server_datetime = pd.to_datetime(server_time, unit='ms')
            
            # 记录本地时间与服务器时间的差异
            local_time = pd.Timestamp.now(tz='UTC').timestamp() * 1000
            time_diff = server_time - local_time
            
            if abs(time_diff) > 1000:  # 如果时差超过1秒
                print(f"警告：本地时间与服务器时间差异较大: {time_diff/1000:.2f}秒")
            
            return server_datetime
        except Exception as e:
            print(f"获取服务器时间失败: {e}")
            # 如果无法获取服务器时间，返回本地时间作为备用
            return pd.Timestamp.now()