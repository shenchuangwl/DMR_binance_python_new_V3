# 长周期策略独立配置
# 从主配置文件同步核心参数 - 实现参数统一管理
from config.config import (
    API_KEY, 
    API_SECRET, 
    TRADE_SYMBOL,      # 统一交易币种参数
    TRADE_AMOUNT,      # 统一交易金额参数
    DMR_LONG_PERIOD,   # 长周期DMR周期
    TIMEFRAME_LONG     # 长周期时间框架
)

# 长周期策略专用配置
LONG_TERM_CONFIG = {
    # === 策略基础信息 ===
    'strategy_name': 'LongTerm_DMR12_Strategy',
    'strategy_version': '2.0.0',
    'strategy_type': 'long_term',
    
    # === 核心交易参数（自动同步自config.py）===
    'symbol': TRADE_SYMBOL,           # 自动同步交易币种
    'position_size': TRADE_AMOUNT,    # 自动同步交易金额
    'dmr_period': DMR_LONG_PERIOD,    # 自动同步DMR周期
    'timeframe': TIMEFRAME_LONG,      # 自动同步时间框架
    
    # === API配置（自动同步）===
    'api_key': API_KEY,
    'api_secret': API_SECRET,
    
    # === 策略专用配置 ===
    'data_config': {
        'data_limit': 1000,
        'sync_interval': 300000,
        'max_retries': 3,
        'recv_window': 10000,
        'rate_limit': True,
        'cache_enabled': True,
        'cache_ttl': 300,  # 缓存生存时间（秒）
    },
    
    'order_config': {
        'open_order_type': 'limit',
        'close_order_type': 'market', 
        'order_timeout': 30000,
        'slippage_tolerance': 0.001,
        'retry_attempts': 3,
        'retry_delay': 1000,  # 重试延迟（毫秒）
    },
    
    'risk_config': {
        'max_position_size': TRADE_AMOUNT * 5,  # 基于统一交易金额动态计算
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.05,
        'max_daily_trades': 25,
        'max_drawdown_pct': 0.10,
        'position_limit_check': True,
    },
    
    'log_config': {
        'log_file': 'long_term_strategy.log',
        'log_level': 'INFO',
        'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'max_file_size': 10485760,  # 10MB
        'backup_count': 5,
    },
    
    # === 策略特定参数 ===
    'signal_config': {
        'signal_threshold': 1e-6,
        'confirmation_periods': 1,
        'signal_timeout': 3600,  # 信号超时时间（秒）
    },
    
    'performance_config': {
        'benchmark_symbol': 'BTC/USDT',
        'performance_window': 30,  # 性能评估窗口（天）
        'report_interval': 86400,  # 报告间隔（秒）
    }
}

# === 配置验证函数 ===
def validate_long_term_config():
    """验证长周期策略配置"""
    config = LONG_TERM_CONFIG
    
    # 验证核心参数同步
    assert config['symbol'] == TRADE_SYMBOL, f"交易币种参数同步失败: {config['symbol']} != {TRADE_SYMBOL}"
    assert config['position_size'] == TRADE_AMOUNT, f"交易金额参数同步失败: {config['position_size']} != {TRADE_AMOUNT}"
    assert config['dmr_period'] == DMR_LONG_PERIOD, f"DMR周期参数同步失败: {config['dmr_period']} != {DMR_LONG_PERIOD}"
    assert config['timeframe'] == TIMEFRAME_LONG, f"时间框架参数同步失败: {config['timeframe']} != {TIMEFRAME_LONG}"
    
    print("长周期策略配置验证通过")
    return True

def get_long_term_config():
    """获取长周期策略配置（支持热更新）"""
    # 重新导入以支持热更新
    import importlib
    import config.config
    importlib.reload(config.config)
    
    from config.config import TRADE_SYMBOL, TRADE_AMOUNT, DMR_LONG_PERIOD, TIMEFRAME_LONG
    
    # 更新配置中的核心参数
    LONG_TERM_CONFIG.update({
        'symbol': TRADE_SYMBOL,
        'position_size': TRADE_AMOUNT,
        'dmr_period': DMR_LONG_PERIOD,
        'timeframe': TIMEFRAME_LONG,
    })
    
    return LONG_TERM_CONFIG

# 执行验证
if __name__ == "__main__":
    validate_long_term_config()
    print("长周期策略配置摘要:", {
        'symbol': LONG_TERM_CONFIG['symbol'],
        'position_size': LONG_TERM_CONFIG['position_size'],
        'dmr_period': LONG_TERM_CONFIG['dmr_period'],
        'timeframe': LONG_TERM_CONFIG['timeframe']
    })