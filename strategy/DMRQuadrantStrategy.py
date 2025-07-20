import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config.config import SYMBOL, DMR_STRATEGY_CONFIG, QUADRANT_CONFIG

class DMRQuadrantStrategy:
    """
    DMR四象限量化策略
    
    策略逻辑:
    - T1(双多趋势): 4H DMR12>0 且 1H DMR26>0，做多加码
    - T2(双空趋势): 4H DMR12<0 且 1H DMR26<0，做空加码  
    - R1(高位震荡): 4H DMR12>0 且 1H DMR26<0，锁空对冲
    - R2(低位震荡): 4H DMR12<0 且 1H DMR26>0，锁多对冲
    """
    
    def __init__(self, df, order_executor, params=None):
        """
        初始化策略
        
        Args:
            df: DataFrame，包含 'high', 'low', 'close' 的OHLCV数据
            order_executor: 交易执行器
            params: 策略参数字典，可选
        """
        self.df = df
        self.order_executor = order_executor
        
        # 使用配置文件中的默认参数
        self.params = DMR_STRATEGY_CONFIG.copy()
        
        # 如果提供了自定义参数，则更新默认参数
        if params:
            self.params.update(params)
        
        # 交易状态跟踪
        self.positions = {
            'Long_4H_T1': None,
            'Short_4H_T2': None,
            'Long_4H_R1': None,
            'Short_4H_R2': None,
            'Long_1H_T1': None,
            'Short_1H_T2': None,
            'Short_1H_R1': None,
            'Long_1H_R2': None,
        }
        
        # 信号处理标志
        self.signal_4h_processed = False
        self.signal_1h_processed = False
        
        # 历史数据缓存
        self.dmr_history_1h = []
        self.dmr_history_4h = []
        
        # 初始化数据框
        self.df_1h = None
        self.df_4h = None
        
    def calculate_dmr(self):
        """计算DMR指标 - 严格按照aicloin公式"""
        # 1. 计算中间价
        self.df['dmr_midprice'] = (self.df['high'] + self.df['low']) / 2
        
        # 2. 计算中间价比率 (当前中价 / 前一日中价)
        self.df['dmr_ratio'] = self.df['dmr_midprice'] / self.df['dmr_midprice'].shift(1)
        self.df['dmr_ratio'] = self.df['dmr_ratio'].fillna(1.0)  # 第一个值设为1
        
        # 3. 计算移动平均并减1 (严格按照公式，使用固定周期)
        self.df['dmr_avg6'] = self.df['dmr_ratio'].rolling(window=6, min_periods=6).mean() - 1
        self.df['dmr_avg12'] = self.df['dmr_ratio'].rolling(window=12, min_periods=12).mean() - 1
        self.df['dmr_avg26'] = self.df['dmr_ratio'].rolling(window=26, min_periods=26).mean() - 1
        
        # 处理NaN值 - 修复弃用警告
        self.df['dmr_avg6'] = self.df['dmr_avg6'].ffill().fillna(0)
        self.df['dmr_avg12'] = self.df['dmr_avg12'].ffill().fillna(0)
        self.df['dmr_avg26'] = self.df['dmr_avg26'].ffill().fillna(0)
        
        # 添加调试信息
        if len(self.df) > 0:
            print(f"DMR计算完成 - 最新值:")
            print(f"DMR6: {self.df['dmr_avg6'].iloc[-1]:.6f}")
            print(f"DMR12: {self.df['dmr_avg12'].iloc[-1]:.6f}")
            print(f"DMR26: {self.df['dmr_avg26'].iloc[-1]:.6f}")
            print(f"中间价: {self.df['dmr_midprice'].iloc[-1]:.6f}")
            print(f"中价比率: {self.df['dmr_ratio'].iloc[-1]:.6f}")
            
            # 添加数据验证
            print(f"数据验证 - 总K线数: {len(self.df)}")
            print(f"有效DMR12数据: {self.df['dmr_avg12'].notna().sum()}")
            print(f"有效DMR26数据: {self.df['dmr_avg26'].notna().sum()}")

    def resample_data(self):
        """重采样数据到不同时间周期 - 修正重采样逻辑"""
        # 从配置获取时间周期（保持动态配置）
        timeframe_long = self.params['timeframe_4h']   # 长周期（15m）
        timeframe_short = self.params['timeframe_1h']  # 短周期（5m）
        
        # 转换币安时间周期格式为pandas兼容格式
        def convert_timeframe(tf):
            """将币安时间周期格式转换为pandas兼容格式"""
            if tf.endswith('m'):
                return tf.replace('m', 'min')  # 5m -> 5min
            elif tf.endswith('h'):
                return tf.replace('h', 'H')    # 4h -> 4H
            elif tf.endswith('d'):
                return tf.replace('d', 'D')    # 1d -> 1D
            return tf
        
        pandas_long = convert_timeframe(timeframe_long)
        pandas_short = convert_timeframe(timeframe_short)
        
        # 重采样时使用正确的聚合方法
        # 对于价格数据使用OHLC聚合，对于DMR使用重新计算
        
        # 长周期数据重采样
        self.df_4h = self.df.resample(pandas_long).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # 在重采样后的数据上重新计算DMR
        if len(self.df_4h) > 0:
            # 重新计算长周期DMR
            self.df_4h['dmr_midprice'] = (self.df_4h['high'] + self.df_4h['low']) / 2
            self.df_4h['dmr_ratio'] = self.df_4h['dmr_midprice'] / self.df_4h['dmr_midprice'].shift(1)
            self.df_4h['dmr_ratio'] = self.df_4h['dmr_ratio'].fillna(1.0)
            
            self.df_4h['dmr_avg6'] = self.df_4h['dmr_ratio'].rolling(window=6, min_periods=6).mean() - 1
            self.df_4h['dmr_avg12'] = self.df_4h['dmr_ratio'].rolling(window=12, min_periods=12).mean() - 1
            self.df_4h['dmr_avg26'] = self.df_4h['dmr_ratio'].rolling(window=26, min_periods=26).mean() - 1
            
            self.df_4h['dmr_avg6'] = self.df_4h['dmr_avg6'].ffill().fillna(0)
            self.df_4h['dmr_avg12'] = self.df_4h['dmr_avg12'].ffill().fillna(0)
            self.df_4h['dmr_avg26'] = self.df_4h['dmr_avg26'].ffill().fillna(0)
        
        # 短周期数据重采样
        self.df_1h = self.df.resample(pandas_short).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # 在重采样后的数据上重新计算DMR
        if len(self.df_1h) > 0:
            # 重新计算短周期DMR
            self.df_1h['dmr_midprice'] = (self.df_1h['high'] + self.df_1h['low']) / 2
            self.df_1h['dmr_ratio'] = self.df_1h['dmr_midprice'] / self.df_1h['dmr_midprice'].shift(1)
            self.df_1h['dmr_ratio'] = self.df_1h['dmr_ratio'].fillna(1.0)
            
            self.df_1h['dmr_avg6'] = self.df_1h['dmr_ratio'].rolling(window=6, min_periods=6).mean() - 1
            self.df_1h['dmr_avg12'] = self.df_1h['dmr_ratio'].rolling(window=12, min_periods=12).mean() - 1
            self.df_1h['dmr_avg26'] = self.df_1h['dmr_ratio'].rolling(window=26, min_periods=26).mean() - 1
            
            self.df_1h['dmr_avg6'] = self.df_1h['dmr_avg6'].ffill().fillna(0)
            self.df_1h['dmr_avg12'] = self.df_1h['dmr_avg12'].ffill().fillna(0)
            self.df_1h['dmr_avg26'] = self.df_1h['dmr_avg26'].ffill().fillna(0)
        
        print(f"重采样完成:")
        print(f"长周期({timeframe_long})数据: {len(self.df_4h)}根K线")
        print(f"短周期({timeframe_short})数据: {len(self.df_1h)}根K线")
        
        # 输出重采样后的DMR值进行验证
        if len(self.df_4h) > 0:
            print(f"长周期最新DMR12: {self.df_4h['dmr_avg12'].iloc[-1]:.6f}")
        if len(self.df_1h) > 0:
            print(f"短周期最新DMR26: {self.df_1h['dmr_avg26'].iloc[-1]:.6f}")

    def detect_crossover(self, current_value, previous_value, threshold=0):
        """
        检测DMR穿越信号
        
        Args:
            current_value: 当前值
            previous_value: 前一个值
            threshold: 阈值
            
        Returns:
            tuple: (crossover_up, crossover_down)
        """
        # 使用配置文件中的容差值
        tolerance = self.params['tolerance']
        
        # 上穿：前值小于等于阈值，当前值大于阈值+容差
        crossover_up = previous_value <= (threshold - tolerance) and current_value > (threshold + tolerance)
        # 下穿：前值大于等于阈值，当前值小于阈值-容差
        crossover_down = previous_value >= (threshold + tolerance) and current_value < (threshold - tolerance)
        
        return crossover_up, crossover_down

    def get_market_state(self):
        """获取当前市场状态"""
        if len(self.df_4h) == 0 or len(self.df_1h) == 0:
            return "UNKNOWN"
        
        # 获取最新DMR值
        dmr12_long = self.df_4h['dmr_avg12'].iloc[-1]  # 长周期DMR12
        dmr26_short = self.df_1h['dmr_avg26'].iloc[-1]  # 短周期DMR26
        
        # 判断市场状态
        if dmr12_long > 0 and dmr26_short > 0:
            return "T1"  # 双多趋势
        elif dmr12_long < 0 and dmr26_short < 0:
            return "T2"  # 双空趋势
        elif dmr12_long > 0 and dmr26_short < 0:
            return "R1"  # 高位震荡
        elif dmr12_long < 0 and dmr26_short > 0:
            return "R2"  # 低位震荡
        else:
            return "NEUTRAL"

    def generate_signals(self):
        """生成交易信号"""
        # 长周期策略信号（基于DMR12）
        self.df_4h['signal_4h'] = 0
        # 当长周期的DMR12由负值转为正值时开多
        self.df_4h.loc[(self.df_4h['dmr_avg12'].shift(1) < 0) & (self.df_4h['dmr_avg12'] > 0), 'signal_4h'] = 1
        # 当长周期的DMR12由正值转为负值时开空
        self.df_4h.loc[(self.df_4h['dmr_avg12'].shift(1) > 0) & (self.df_4h['dmr_avg12'] < 0), 'signal_4h'] = -1
        
        # 短周期策略信号（基于DMR26）
        self.df_1h['signal_1h'] = 0
        # 当短周期的DMR26由负值转为正值时开多
        self.df_1h.loc[(self.df_1h['dmr_avg26'].shift(1) < 0) & (self.df_1h['dmr_avg26'] > 0), 'signal_1h'] = 1
        # 当短周期的DMR26由正值转为负值时开空
        self.df_1h.loc[(self.df_1h['dmr_avg26'].shift(1) > 0) & (self.df_1h['dmr_avg26'] < 0), 'signal_1h'] = -1
        
        # 计算市场状态
        for i in range(len(self.df_4h)):
            dmr12_long = self.df_4h['dmr_avg12'].iloc[i]
            time_4h = self.df_4h.index[i]
            mask = self.df_1h.index <= time_4h
            if mask.any():
                closest_1h_idx = mask.argmax() if not mask.all() else len(self.df_1h) - 1
                dmr26_short = self.df_1h['dmr_avg26'].iloc[closest_1h_idx]
                
                # 确定市场状态
                dmr12_long_positive = dmr12_long > 0
                dmr26_short_positive = dmr26_short > 0
                
                if dmr12_long_positive and dmr26_short_positive:
                    self.df_4h.loc[self.df_4h.index[i], 'market_state'] = 'T1'
                elif not dmr12_long_positive and not dmr26_short_positive:
                    self.df_4h.loc[self.df_4h.index[i], 'market_state'] = 'T2'
                elif dmr12_long_positive and not dmr26_short_positive:
                    self.df_4h.loc[self.df_4h.index[i], 'market_state'] = 'R1'
                else:
                    self.df_4h.loc[self.df_4h.index[i], 'market_state'] = 'R2'

    def is_trading_window(self, timeframe):
        """判断是否为交易窗口"""
        now = datetime.now()
        
        # 根据时间框架判断
        if timeframe == '5m':
            return now.minute % 5 == 0
        elif timeframe == '15m':
            return now.minute % 15 == 0
        elif timeframe == '30m':
            return now.minute % 30 == 0
        elif timeframe == '1h':
            return now.minute == 0
        elif timeframe == '2h':
            return now.hour % 2 == 0 and now.minute == 0
        elif timeframe == '4h':
            return now.hour % 4 == 0 and now.minute == 0
        else:
            return now.minute == 0  # 默认每小时

    def execute_trade(self, action, position_name, comment=""):
        """
        执行交易操作
        
        Args:
            action: 'buy', 'sell', 'close'
            position_name: 仓位名称
            comment: 交易备注
        """
        size = self.params['position_size']
        current_price = self.df['close'].iloc[-1]
        
        if action == 'buy':
            if self.positions[position_name] is None:
                # 使用限价单开多仓
                order = self.order_executor.open_long(SYMBOL, size, price=current_price, order_type='limit')
                self.positions[position_name] = order
                print(f"{datetime.now()}: {comment} - 限价开多 {size} USDT，价格：{current_price}")
                
            elif action == 'sell':
                if self.positions[position_name] is None:
                    # 使用限价单开空仓
                    order = self.order_executor.open_short(SYMBOL, size, price=current_price, order_type='limit')
                    self.positions[position_name] = order
                    print(f"{datetime.now()}: {comment} - 限价开空 {size} USDT，价格：{current_price}")
                    
            elif action == 'close':
                if self.positions[position_name] is not None:
                    # 根据仓位名称确定平仓方向，使用市价单平仓
                    if 'Long' in position_name:
                        self.order_executor.close_position(SYMBOL, 'LONG', order_type='market')
                        print(f"{datetime.now()}: {comment} - 市价平多")
                    else:
                        self.order_executor.close_position(SYMBOL, 'SHORT', order_type='market')
                        print(f"{datetime.now()}: {comment} - 市价平空")
                    self.positions[position_name] = None

    def execute_trades(self):
        """执行交易逻辑"""
        # 增强数据验证
        if len(self.df) < 26:
            print(f"警告：原始数据不足，当前只有{len(self.df)}根K线，需要至少26根K线计算DMR26")
            return
            
        if len(self.df_4h) < 2 or len(self.df_1h) < 2:
            print("警告：重采样后数据不足，无法检测穿越信号")
            print(f"长周期数据: {len(self.df_4h)}根K线, 短周期数据: {len(self.df_1h)}根K线")
            return
        
        # 获取最新的DMR值
        dmr12_4h = self.df_4h['dmr_avg12'].iloc[-1] if len(self.df_4h) > 0 else 0
        dmr26_1h = self.df_1h['dmr_avg26'].iloc[-1] if len(self.df_1h) > 0 else 0
        
        # 检查DMR值是否有效
        if pd.isna(dmr12_4h) or pd.isna(dmr26_1h):
            print("警告：DMR值无效，跳过本次交易检查")
            print(f"DMR12_4H: {dmr12_4h}, DMR26_1H: {dmr26_1h}")
            return
        
        # 打印详细的DMR统计信息
        print(f"原始数据统计 - 总K线数: {len(self.df)}")
        print(f"DMR26统计 - 最小值: {self.df['dmr_avg26'].min():.6f}, 最大值: {self.df['dmr_avg26'].max():.6f}")
        print(f"DMR26统计 - 平均值: {self.df['dmr_avg26'].mean():.6f}, 当前值: {dmr26_1h:.6f}")
        print(f"DMR12统计 - 最小值: {self.df['dmr_avg12'].min():.6f}, 最大值: {self.df['dmr_avg12'].max():.6f}")
        print(f"DMR12统计 - 平均值: {self.df['dmr_avg12'].mean():.6f}, 当前值: {dmr12_4h:.6f}")
        
        # 检查最近几个DMR值的变化趋势
        if len(self.df) >= 5:
            print("最近5个DMR26值的变化:")
            recent_dmr26 = self.df['dmr_avg26'].tail(5)
            for i, (timestamp, value) in enumerate(recent_dmr26.items()):
                print(f"  {i+1}: {timestamp} = {value:.6f}")
        
        # 获取当前市场状态
        market_state = self.get_market_state()
        
        # 检查当前K线是否已收盘
        is_4h_close = self.is_trading_window(self.params['timeframe_4h'])
        is_1h_close = self.is_trading_window(self.params['timeframe_1h'])
        
        # 获取最新信号
        latest_4h_signal = self.df_4h['signal_4h'].iloc[-1] if len(self.df_4h) > 0 else 0
        latest_1h_signal = self.df_1h['signal_1h'].iloc[-1] if len(self.df_1h) > 0 else 0
        
        # 检测穿越信号
        if len(self.df_4h) > 1:
            dmr12_4h_prev = self.df_4h['dmr_avg12'].iloc[-2]
            dmr12_4h_cross_up, dmr12_4h_cross_down = self.detect_crossover(
                dmr12_4h, dmr12_4h_prev
            )
            print(f"4H DMR12穿越检测: 前值={dmr12_4h_prev:.6f}, 当前值={dmr12_4h:.6f}")
        else:
            dmr12_4h_cross_up = dmr12_4h_cross_down = False
            
        if len(self.df_1h) > 1:
            dmr26_1h_prev = self.df_1h['dmr_avg26'].iloc[-2]
            dmr26_1h_cross_up, dmr26_1h_cross_down = self.detect_crossover(
                dmr26_1h, dmr26_1h_prev
            )
            print(f"1H DMR26穿越检测: 前值={dmr26_1h_prev:.6f}, 当前值={dmr26_1h:.6f}")
        else:
            dmr26_1h_cross_up = dmr26_1h_cross_down = False
            
        # 打印调试信息
        print(f"当前市场状态: {market_state}, 4H DMR12: {dmr12_4h:.6f}, 1H DMR26: {dmr26_1h:.6f}")
        print(f"4H信号: {latest_4h_signal}, 1H信号: {latest_1h_signal}")
        print(f"4H穿越: 上穿={dmr12_4h_cross_up}, 下穿={dmr12_4h_cross_down}")
        print(f"1H穿越: 上穿={dmr26_1h_cross_up}, 下穿={dmr26_1h_cross_down}")
        print(f"时间窗口: 4H={is_4h_close}, 1H={is_1h_close}")
        
        # 重置处理标志
        self.signal_4h_processed = False
        self.signal_1h_processed = False
        
        # 根据市场状态执行相应的交易策略
        # T1 – 多头趋势：4H DMR(12) 负→正，1H DMR(26) 负→正，做多加码
        # T2 – 空头趋势：4H DMR(12) 正→负，1H DMR(26) 正→负，做空加码
        # R1 – 高位震荡：4H DMR(12) 负→正，1H DMR(26) 正→负，锁空对冲
        # R2 – 低位震荡：4H DMR(12) 正→负，1H DMR(26) 负→正，锁多对冲
        
        # 4H信号处理(优先执行)
        if is_4h_close and not self.signal_4h_processed:
            quadrant_config = QUADRANT_CONFIG.get(market_state, {})
            actions = quadrant_config.get('actions', {})
            
            if dmr12_4h_cross_up and '4h_neg_to_pos' in actions:
                action_config = actions['4h_neg_to_pos']
                self.execute_trade(action_config['action'], action_config['position'], action_config['comment'])
                self.signal_4h_processed = True
                
            if dmr12_4h_cross_down and '4h_pos_to_neg' in actions:
                action_config = actions['4h_pos_to_neg']
                self.execute_trade(action_config['action'], action_config['position'], action_config['comment'])
                self.signal_4h_processed = True
        
        # 1H信号处理(在4H信号处理完成后执行)
        if is_1h_close and not self.signal_1h_processed:
            quadrant_config = QUADRANT_CONFIG.get(market_state, {})
            actions = quadrant_config.get('actions', {})
            
            if dmr26_1h_cross_up and '1h_neg_to_pos' in actions:
                action_config = actions['1h_neg_to_pos']
                self.execute_trade(action_config['action'], action_config['position'], action_config['comment'])
                self.signal_1h_processed = True
                
            if dmr26_1h_cross_down and '1h_pos_to_neg' in actions:
                action_config = actions['1h_pos_to_neg']
                self.execute_trade(action_config['action'], action_config['position'], action_config['comment'])
                self.signal_1h_processed = True
    
    def run_strategy(self):
        """运行完整策略"""
        self.calculate_dmr()
        self.resample_data()
        self.generate_signals()
        self.execute_trades()
        return self.df

        # 回测模式示例
        def backtest_dmr_strategy(df, initial_capital=10000):
            """
            回测DMR四象限策略
            
            Args:
                df: 包含OHLCV数据的DataFrame
                initial_capital: 初始资金
            
            Returns:
                回测结果字典
            """
            # 创建回测环境
            # 这里可以使用backtrader或自定义的回测逻辑
            print("回测DMR四象限策略...")
            
            # 示例回测逻辑
            # 实际实现时可以集成backtrader或其他回测框架
            
            # 返回示例结果
            return {
                "initial_capital": initial_capital,
                "final_capital": initial_capital * 1.2,  # 示例收益
                "profit_percentage": 20,
                "max_drawdown": 10,
                "trade_count": 15
            }

        # 测试代码
        if __name__ == "__main__":
            # 这里可以添加测试代码
            print("DMR四象限量化策略 - 测试模式")