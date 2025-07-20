# Binance 真实网络 API 配置
API_KEY = ''
API_SECRET = ''

# === 全局核心参数（唯一数据源）===
# 交易币种参数 - 全局统一配置
TRADE_SYMBOL = 'UXLINK/USDT'

# 交易金额参数 - 全局统一配置
TRADE_AMOUNT = 20  # USDT

# 为了向后兼容，保留原有参数名但指向新的统一参数
SYMBOL = TRADE_SYMBOL
POSITION_SIZE = TRADE_AMOUNT

# === 时间周期配置 ===
# 支持的时间周期: '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d' 等
TIMEFRAME_LONG = '15m'   # 长周期时间框架
TIMEFRAME_SHORT = '5m'   # 短周期时间框架

# === DMR策略核心参数 ===
# DMR周期参数 - 全局统一配置
DMR_LONG_PERIOD = 12    # 长周期DMR周期
DMR_SHORT_PERIOD = 26   # 短周期DMR周期

# 为了向后兼容，保留原有参数名
MA_LONG_PERIOD = DMR_LONG_PERIOD
MA_SHORT_PERIOD = DMR_SHORT_PERIOD

# === 系统配置参数 ===
# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = 'trading_log.txt'

# DMR策略参数
DMR_STRATEGY_CONFIG = {
    'position_size': TRADE_AMOUNT,
    'dmr_period_6': 6,
    'dmr_period_12': DMR_LONG_PERIOD,
    'dmr_period_26': DMR_SHORT_PERIOD,
    'tolerance': 1e-6,
    'timeframe_4h': TIMEFRAME_LONG,
    'timeframe_1h': TIMEFRAME_SHORT,
}

# 策略判断用的周期参数
STRATEGY_LONG_PERIOD = DMR_LONG_PERIOD
STRATEGY_SHORT_PERIOD = DMR_SHORT_PERIOD

# 数据获取配置
DATA_FETCHER_CONFIG = {
    'data_limit': 1000,  # 历史数据获取限制 ，对于26根K线的计算，1000已经足够
    'sync_interval': 300000,  # 时间同步间隔(毫秒)
    'max_retries': 3,  # 最大重试次数
    'recv_window': 10000,  # 接收窗口时间
    'rate_limit': True,  # 启用速率限制
}

# 交易执行配置
ORDER_EXECUTOR_CONFIG = {
    'default_type': 'future',  # 默认交易类型
    'adjust_for_time_diff': True,  # 调整时间差异
    'order_timeout': 30000,  # 订单超时时间(毫秒)
    'slippage_tolerance': 0.001,  # 滑点容忍度
    'open_order_type': 'limit',  # 开仓使用限价单
    'close_order_type': 'market',  # 平仓使用市价单
}

# 系统运行配置
SYSTEM_CONFIG = {
    'main_loop_sleep': 60,  # 主循环睡眠时间(秒)
    'scheduler_sleep': 1,   # 调度器睡眠时间(秒)
    'force_sync_on_startup': True,  # 启动时强制同步时间
}

# 风险管理配置
RISK_MANAGEMENT_CONFIG = {
    'max_position_size': TRADE_AMOUNT * 5,  # 基于交易金额动态计算
    'stop_loss_pct': 0.02,
    'take_profit_pct': 0.05,
    'max_daily_trades': 50,
    'max_drawdown_pct': 0.10,
}

# 监控配置
MONITORING_CONFIG = {
    'account_info_log_interval': '00:00',  # 账户信息记录间隔
    'time_sync_interval': 'hourly',       # 时间同步间隔
    'performance_check_interval': 300,     # 性能检查间隔(秒)
}

# 四象限配置
QUADRANT_CONFIG = {
    "T1": {
        "name": "多头趋势",
        "description": f"长周期 DMR({DMR_LONG_PERIOD}) > 0 且 短周期 DMR({DMR_SHORT_PERIOD}) > 0",
        "actions": {
            "4h_neg_to_pos": {
                "action": "buy",
                "position": "Long_4H_T1",
                "comment": "T1-长周期开多"
            },
            "4h_pos_to_neg": {
                "action": "close",
                "position": "Long_4H_T1",
                "comment": "T1-长周期平多"
            },
            "1h_neg_to_pos": {
                "action": "buy",
                "position": "Long_1H_T1",
                "comment": "T1-短周期开多"
            },
            "1h_pos_to_neg": {
                "action": "close",
                "position": "Long_1H_T1",
                "comment": "T1-短周期平多"
            }
        }
    },
    "T2": {
        "name": "空头趋势",
        "description": f"长周期 DMR({DMR_LONG_PERIOD}) < 0 且 短周期 DMR({DMR_SHORT_PERIOD}) < 0",
        "actions": {
            "4h_pos_to_neg": {
                "action": "sell",
                "position": "Short_4H_T2",
                "comment": "T2-长周期开空"
            },
            "4h_neg_to_pos": {
                "action": "close",
                "position": "Short_4H_T2",
                "comment": "T2-长周期平空"
            },
            "1h_pos_to_neg": {
                "action": "sell",
                "position": "Short_1H_T2",
                "comment": "T2-短周期开空"
            },
            "1h_neg_to_pos": {
                "action": "close",
                "position": "Short_1H_T2",
                "comment": "T2-短周期平空"
            }
        }
    },
    "R1": {
        "name": "高位震荡",
        "description": f"长周期 DMR({DMR_LONG_PERIOD}) > 0 且 短周期 DMR({DMR_SHORT_PERIOD}) < 0",
        "actions": {
            "4h_neg_to_pos": {
                "action": "buy",
                "position": "Long_4H_R1",
                "comment": "R1-长周期开多"
            },
            "4h_pos_to_neg": {
                "action": "close",
                "position": "Long_4H_R1",
                "comment": "R1-长周期平多"
            },
            "1h_pos_to_neg": {
                "action": "sell",
                "position": "Short_1H_R1",
                "comment": "R1-短周期开空"
            },
            "1h_neg_to_pos": {
                "action": "close",
                "position": "Short_1H_R1",
                "comment": "R1-短周期平空"
            }
        }
    },
    "R2": {
        "name": "低位震荡",
        "description": f"长周期 DMR({DMR_LONG_PERIOD}) < 0 且 短周期 DMR({DMR_SHORT_PERIOD}) > 0",
        "actions": {
            "4h_pos_to_neg": {
                "action": "sell",
                "position": "Short_4H_R2",
                "comment": "R2-长周期开空"
            },
            "4h_neg_to_pos": {
                "action": "close",
                "position": "Short_4H_R2",
                "comment": "R2-长周期平空"
            },
            "1h_neg_to_pos": {
                "action": "buy",
                "position": "Long_1H_R2",
                "comment": "R2-短周期开多"
            },
            "1h_pos_to_neg": {
                "action": "close",
                "position": "Long_1H_R2",
                "comment": "R2-短周期平多"
            }
        }
    }
}

# === 配置验证与热更新支持 ===
def validate_config():
    """验证配置参数的有效性"""
    valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
    
    if TIMEFRAME_LONG not in valid_timeframes:
        raise ValueError(f"无效的长周期时间框架: {TIMEFRAME_LONG}")
    
    if TIMEFRAME_SHORT not in valid_timeframes:
        raise ValueError(f"无效的短周期时间框架: {TIMEFRAME_SHORT}")
    
    # 确保长周期大于短周期
    timeframe_minutes = {
        '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480, '12h': 720,
        '1d': 1440, '3d': 4320, '1w': 10080, '1M': 43200
    }
    
    if timeframe_minutes[TIMEFRAME_LONG] <= timeframe_minutes[TIMEFRAME_SHORT]:
        raise ValueError(f"长周期({TIMEFRAME_LONG})必须大于短周期({TIMEFRAME_SHORT})")
    
    # 验证交易参数
    if TRADE_AMOUNT <= 0:
        raise ValueError(f"交易金额必须大于0: {TRADE_AMOUNT}")
    
    if not TRADE_SYMBOL or '/' not in TRADE_SYMBOL:
        raise ValueError(f"无效的交易币种格式: {TRADE_SYMBOL}")
    
    print("配置验证通过")
    return True

def get_config_summary():
    """获取配置摘要信息"""
    return {
        'trade_symbol': TRADE_SYMBOL,
        'trade_amount': TRADE_AMOUNT,
        'dmr_long_period': DMR_LONG_PERIOD,
        'dmr_short_period': DMR_SHORT_PERIOD,
        'timeframe_long': TIMEFRAME_LONG,
        'timeframe_short': TIMEFRAME_SHORT,
        'config_version': '2.0.0'
    }

# 执行验证
if __name__ == "__main__":
    validate_config()
    print("配置摘要:", get_config_summary())
