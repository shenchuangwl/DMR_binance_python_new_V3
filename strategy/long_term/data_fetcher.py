import ccxt
import pandas as pd
from datetime import datetime
import time
import os
from config.long_term_config import LONG_TERM_CONFIG
from utils.logger import setup_logger

class LongTermDataFetcher:
    """长周期策略独立数据采集器"""
    
    def __init__(self):
        self.config = LONG_TERM_CONFIG
        self.logger = setup_logger(
            name='LongTermDataFetcher',
            log_file=self.config['log_config']['log_file']
        )
        
        # 初始化交易所连接
        self.exchange = ccxt.binance({
            'apiKey': self.config['api_key'],
            'secret': self.config['api_secret'],
            'sandbox': False,
            'enableRateLimit': self.config['data_config']['rate_limit'],
            'options': {
                'defaultType': 'future',
                'recvWindow': self.config['data_config']['recv_window'],
            }
        })
        
        self.symbol = self.config['symbol']
        self.timeframe = self.config['timeframe']
        self.dmr_period = self.config['dmr_period']
        
        # 设置数据保存路径
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.data_dir = os.path.join(project_root, 'data', 'long_term')
        os.makedirs(self.data_dir, exist_ok=True)
        
        base_currency = self.symbol.split('/')[0]
        self.data_path = f'{self.data_dir}/{base_currency}_USDT_long_term_data.csv'
        
    def sync_time(self, force=False):
        """同步服务器时间"""
        try:
            server_time = self.exchange.fetch_time()
            if server_time is None:
                self.logger.warning("长周期策略时间同步失败：fetch_time 返回 None")
                return

            local_time = int(time.time() * 1000)
            time_diff = abs(server_time - local_time)
            
            if time_diff > 1000 or force:
                self.logger.info(f"长周期策略时间同步 - 服务器时间: {server_time}, 本地时间: {local_time}, 差异: {time_diff}ms")
                
        except Exception as e:
            self.logger.error(f"长周期策略时间同步失败: {e}")
    
    def get_historical_data(self):
        """获取历史K线数据"""
        try:
            self.sync_time()
            
            # 获取足够的历史数据用于DMR计算
            limit = max(self.config['data_config']['data_limit'], self.dmr_period * 3)
            
            ohlcv = self.exchange.fetch_ohlcv(
                self.symbol, 
                self.timeframe, 
                limit=limit
            )
            
            if not ohlcv:
                self.logger.warning("长周期策略未能获取到K线数据(ohlcv)，可能返回了空列表。")
                return pd.DataFrame()

            df = pd.DataFrame(ohlcv)
            df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            self.logger.info(f"长周期策略获取到 {len(df)} 根K线数据")
            return df
            
        except Exception as e:
            self.logger.error(f"长周期策略获取历史数据失败: {e}")
            return None
    
    def calculate_dmr(self, df):
        """计算DMR指标"""
        try:
            # 计算中间价
            df['dmr_midprice'] = (df['high'] + df['low']) / 2
            
            # 计算中间价比率
            df['dmr_ratio'] = df['dmr_midprice'] / df['dmr_midprice'].shift(1)
            df['dmr_ratio'] = df['dmr_ratio'].fillna(1.0)
            
            # 计算DMR均线
            df[f'dmr_{self.dmr_period}'] = df['dmr_ratio'].rolling(
                window=self.dmr_period, 
                min_periods=self.dmr_period
            ).mean() - 1
            
            df[f'dmr_{self.dmr_period}'] = df[f'dmr_{self.dmr_period}'].ffill().fillna(0)
            
            self.logger.info(f"长周期策略DMR{self.dmr_period}计算完成")
            return df
            
        except Exception as e:
            self.logger.error(f"长周期策略DMR计算失败: {e}")
            return df
    
    def get_account_balance(self):
        """获取账户余额"""
        try:
            balance = self.exchange.fetch_balance()
            return {
                'total_usdt': balance['USDT']['total'],
                'free_usdt': balance['USDT']['free'],
                'used_usdt': balance['USDT']['used']
            }
        except Exception as e:
            self.logger.error(f"长周期策略获取账户余额失败: {e}")
            return None
    
    def get_positions(self):
        """获取当前持仓"""
        try:
            positions = self.exchange.fetch_positions([self.symbol])
            if not positions:
                return []
            result = []
            for pos in positions:
                try:
                    if pos and 'contracts' in pos and pos['contracts'] is not None and float(pos['contracts']) != 0:
                        result.append(pos)
                except (ValueError, TypeError):
                    continue
            return result
        except Exception as e:
            self.logger.error(f"长周期策略获取持仓失败: {e}")
            return []
    
    def save_data_to_csv(self, df, filename=None):
        """将数据保存到CSV文件"""
        if filename is None:
            filename = self.data_path
            
        if df is not None and not df.empty:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            # 将索引重命名为'time'并格式化输出
            df.index.name = 'time'
            df.to_csv(filename, index=True, date_format='%Y-%m-%d %H:%M')
            
            self.logger.info(f"长周期数据已保存到 {filename}")
            return True
        else:
            self.logger.warning(f"没有数据保存到 {filename}")
            return False
    
    def get_and_save_data(self):
        """获取数据并保存"""
        try:
            # 获取历史数据
            df = self.get_historical_data()
            if df is not None and not df.empty:
                # 计算DMR指标
                df = self.calculate_dmr(df)
                # 保存数据
                self.save_data_to_csv(df)
                self.logger.info(f"长周期策略数据获取并保存完成，共 {len(df)} 条记录")
                return df
            else:
                self.logger.error("长周期策略获取数据失败")
                return None
        except Exception as e:
            self.logger.error(f"长周期策略数据获取保存失败: {e}")
            return None