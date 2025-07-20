import pandas as pd
from datetime import datetime
import os
import json
from config.long_term_config import LONG_TERM_CONFIG
from utils.logger import setup_logger

class LongTermDMRStrategy:
    """长周期DMR12策略引擎"""
    
    def __init__(self, data_fetcher, order_executor, position_manager, risk_manager):
        self.data_fetcher = data_fetcher
        self.order_executor = order_executor
        self.position_manager = position_manager
        self.risk_manager = risk_manager
        self.config = LONG_TERM_CONFIG
        self.logger = setup_logger(
            name='LongTermStrategy',
            log_file=self.config['log_config']['log_file']
        )
        
        self.dmr_period = self.config['dmr_period']
        self.position_size = self.config['position_size']
        
        # 信号状态跟踪
        self.last_dmr_value = None
        
        # 初始化策略持仓为空
        self.strategy_position = None
        safe_symbol = self.config['symbol'].replace('/', '_')
        # 修改：将位置文件路径从/tmp更改为项目内更持久的路径
        self.position_file = f"data/positions/long_term_position_{safe_symbol}.json"
        self.reset_flag_file = f"data/positions/long_term_reset.flag"

    def reconcile_state(self):
        """
        启动时核对状态。
        1. 检查强制重置标志。
        2. 对比本地与交易所状态，处理手动平仓等情况。
        3. “认领”逻辑已移至 execute_signal，启动时不再主动认领未知持仓。
        """
        # 1. 检查强制重置标志文件
        if os.path.exists(self.reset_flag_file):
            self.logger.warning("检测到重置标志文件，将强制重置策略状态。")
            self._reset_position_state()
            try:
                os.remove(self.reset_flag_file)
                self.logger.info(f"已删除重置标志文件: {self.reset_flag_file}")
            except OSError as e:
                self.logger.error(f"删除重置标志文件失败: {e}")
            return # 完成重置，直接返回

        # 2. 正常核对流程
        self._load_strategy_position()
        local_position = self.get_strategy_position()

        if local_position:
            # 如果本地有持仓记录, 我们就精确地检查对应方向的持仓
            expected_side = local_position['side']
            exchange_position = self.position_manager.get_current_position(side=expected_side)
            
            if not exchange_position:
                self.logger.info(f"检测到本地有 '{expected_side}' 持仓记录但交易所无对应持仓，判定为外部手动平仓。")
                self._reset_position_state()
            else:
                # 还可以增加对仓位大小的核对
                self.logger.info(f"本地与交易所均有 '{expected_side}' 持仓，状态同步。")
        else:
            # 如果本地无持仓记录，我们假定本策略当前没有持仓。
            # 真正的“认领”将在 execute_signal 中根据信号方向进行，以确保只认领自己的仓位。
            self.logger.info("本地无持仓记录，策略以无持仓状态启动。")
        
    def detect_signal(self, df):
        """检测DMR穿越信号"""
        if len(df) < 2:
            return None
            
        current_dmr = df[f'dmr_{self.dmr_period}'].iloc[-1]
        previous_dmr = df[f'dmr_{self.dmr_period}'].iloc[-2]
        
        # 检测穿越信号
        if previous_dmr <= 0 and current_dmr > 0:
            signal = 'LONG'  # 由负转正，开多信号
        elif previous_dmr >= 0 and current_dmr < 0:
            signal = 'SHORT'  # 由正转负，开空信号
        else:
            signal = None
            
        if signal:
            self.logger.info(f"长周期策略检测到信号: {signal}, DMR{self.dmr_period}: {previous_dmr:.6f} -> {current_dmr:.6f}")
            
        return signal
    
    def execute_signal(self, signal, current_price):
        """
        执行交易信号。
        新增逻辑：在开仓前，如果本地无持仓记录，会先检查交易所是否存在同向的、可能是本策略遗漏的持仓。
        """
        try:
            trade_quantity = self.position_manager.calculate_position_size(current_price)
            strategy_position = self.get_strategy_position()

            if signal == 'LONG':
                if strategy_position and strategy_position['side'] == 'long':
                    self.logger.info("长周期策略：本策略已有多仓，无需操作")
                    return

                # 检查是否存在需要认领的交易所多头持仓
                if strategy_position is None:
                    exchange_long_pos = self.position_manager.get_current_position(side='long')
                    if exchange_long_pos:
                        self.logger.info("检测到未追踪的多头持仓，且当前信号为多头，长周期策略将认领该持仓。")
                        self._claim_exchange_position(exchange_long_pos)
                        return  # 认领后，本次操作完成

                # 如果有空仓，先平仓
                if strategy_position and strategy_position['side'] == 'short':
                    self.logger.info("长周期策略：先平空仓")
                    self.order_executor.close_short(strategy_position['amount'], strategy_position)

                # 执行开多操作
                self.logger.info("长周期策略：执行开多操作")
                self.order_executor.open_long(current_price, trade_quantity)
                self._update_strategy_position('long', trade_quantity, current_price)

            elif signal == 'SHORT':
                if strategy_position and strategy_position['side'] == 'short':
                    self.logger.info("长周期策略：本策略已有空仓，无需操作")
                    return

                # 检查是否存在需要认领的交易所空头持仓
                if strategy_position is None:
                    exchange_short_pos = self.position_manager.get_current_position(side='short')
                    if exchange_short_pos:
                        self.logger.info("检测到未追踪的空头持仓，且当前信号为空头，长周期策略将认领该持仓。")
                        self._claim_exchange_position(exchange_short_pos)
                        return  # 认领后，本次操作完成
                
                # 如果有多仓，先平仓
                if strategy_position and strategy_position['side'] == 'long':
                    self.logger.info("长周期策略：先平多仓")
                    self.order_executor.close_long(strategy_position['amount'], strategy_position)

                # 执行开空操作
                self.logger.info("长周期策略：执行开空操作")
                self.order_executor.open_short(current_price, trade_quantity)
                self._update_strategy_position('short', trade_quantity, current_price)

        except Exception as e:
            self.logger.error(f"长周期策略执行信号失败: {e}", exc_info=True)
    
    def _claim_exchange_position(self, exchange_position):
        """根据交易所的持仓信息，更新并保存本地策略状态"""
        try:
            self.logger.info(f"正在认领的持仓详情: {exchange_position}")
            side = exchange_position.get('side')
            # 'contracts' for binance, 'positionAmt' for futures API
            amount_str = exchange_position.get('contracts', exchange_position.get('positionAmt'))
            entry_price_str = exchange_position.get('entryPrice')

            if side and amount_str is not None and entry_price_str is not None:
                amount = abs(float(amount_str))  # positionAmt is negative for short side
                entry_price = float(entry_price_str)

                if amount > 0:
                    self.logger.info(f"正在同步交易所持仓: 方向={side}, 数量={amount}, 入场价={entry_price}")
                    self._update_strategy_position(side.lower(), amount, entry_price)
                    self.logger.info("交易所持仓认领完成，已在本地创建记录。")
                else:
                    self.logger.warning("尝试认领的交易所持仓数量为0，无需同步。")
            else:
                self.logger.error(f"无法从交易所持仓信息中提取必要数据进行认领: {exchange_position}")

        except (ValueError, TypeError) as e:
            self.logger.error(f"转换交易所持仓数据时出错: {e}")
        except Exception as e:
            self.logger.error(f"认领交易所持仓时发生意外错误: {e}")

    def get_strategy_position(self):
        """获取本策略的持仓记录"""
        return getattr(self, 'strategy_position', None)
    
    def _update_strategy_position(self, side, amount, price):
        """更新本策略的持仓记录"""
        self.strategy_position = {
            'side': side,
            'amount': amount,
            'entry_price': price,
            'timestamp': datetime.now()
        }
        self._save_strategy_position()
    
    def _save_strategy_position(self):
        """保存策略持仓到文件"""
        try:
            os.makedirs(os.path.dirname(self.position_file), exist_ok=True)
            with open(self.position_file, 'w') as f:
                json.dump(self.strategy_position, f, default=str)
        except Exception as e:
            self.logger.warning(f"保存策略持仓失败: {e}")
    
    def _load_strategy_position(self):
        """从文件加载策略持仓"""
        try:
            with open(self.position_file, 'r') as f:
                self.strategy_position = json.load(f)
                if self.strategy_position:
                    self.logger.info(f"从文件加载策略持仓成功: {self.strategy_position}")
        except (FileNotFoundError, json.JSONDecodeError):
            self.strategy_position = None
            self.logger.info("策略持仓文件不存在或为空，初始化为空仓。")

    def _reset_position_state(self):
        """重置并清空策略持仓状态"""
        self.strategy_position = None
        if os.path.exists(self.position_file):
            try:
                os.remove(self.position_file)
                self.logger.info(f"已删除本地持仓状态文件: {self.position_file}")
            except OSError as e:
                self.logger.error(f"删除本地持仓文件失败: {e}")

    def run_strategy(self, df: pd.DataFrame):
        """
        运行策略主循环。
        使用传入的、已包含DMR指标的DataFrame。
        """
        try:
            # 外部已完成数据获取和DMR计算
            if df is None or df.empty:
                self.logger.warning("传入的DataFrame为空，跳过策略执行。")
                return

            signal = self.detect_signal(df)
            
            if signal:
                if self.risk_manager.check_risk_limits():
                    current_price = df['close'].iloc[-1]
                    self.execute_signal(signal, current_price)
                else:
                    self.logger.warning("长周期策略：风控限制，跳过交易信号")
                    
        except Exception as e:
            self.logger.error(f"长周期策略运行失败: {e}")