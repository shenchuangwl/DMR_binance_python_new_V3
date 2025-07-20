import time
import schedule
import threading
from datetime import datetime
from strategy.long_term.data_fetcher import LongTermDataFetcher
from strategy.long_term.strategy_engine import LongTermDMRStrategy
from strategy.long_term.order_executor import LongTermOrderExecutor
from strategy.long_term.position_manager import LongTermPositionManager
from strategy.long_term.risk_manager import LongTermRiskManager
from config.long_term_config import LONG_TERM_CONFIG
from utils.logger import setup_logger

def run_long_term_strategy():
    """运行长周期策略"""
    logger = setup_logger(
        name='LongTermMain',
        log_file=LONG_TERM_CONFIG['log_config']['log_file']
    )
    
    try:
        # 初始化各个模块
        data_fetcher = LongTermDataFetcher()
        position_manager = LongTermPositionManager(data_fetcher.exchange)
        order_executor = LongTermOrderExecutor(data_fetcher.exchange, position_manager)  # 修复：添加position_manager参数
        risk_manager = LongTermRiskManager(data_fetcher.exchange)
        
        # 获取并保存数据
        df = data_fetcher.get_and_save_data()
        if df is None:
            logger.error("长周期策略数据获取失败，跳过本次执行")
            return
        
        # 初始化策略引擎
        strategy = LongTermDMRStrategy(
            data_fetcher, order_executor, position_manager, risk_manager
        )
        
        # 启动时状态核对
        strategy.reconcile_state()
        
        # 运行策略，传入已获取和处理好的数据
        strategy.run_strategy(df)
        
        logger.info("长周期策略执行完成")
        
    except Exception as e:
        logger.error(f"长周期策略执行失败: {e}")

def setup_long_term_schedule():
    """设置长周期策略调度"""
    timeframe = LONG_TERM_CONFIG['timeframe']
    
    if timeframe == '15m':
        for minute in [0, 15, 30, 45]:
            schedule.every().hour.at(f":{minute:02d}").do(run_long_term_strategy)
    elif timeframe == '30m':
        for minute in [0, 30]:
            schedule.every().hour.at(f":{minute:02d}").do(run_long_term_strategy)
    elif timeframe == '1h':
        schedule.every().hour.at(":00").do(run_long_term_strategy)
    elif timeframe == '4h':
        for hour in [0, 4, 8, 12, 16, 20]:
            schedule.every().day.at(f"{hour:02d}:00").do(run_long_term_strategy)

def run_scheduler():
    """运行调度器"""
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    """长周期策略主程序"""
    logger = setup_logger(
        name='LongTermMain',
        log_file=LONG_TERM_CONFIG['log_config']['log_file']
    )
    
    logger.info("启动长周期DMR12策略系统")
    
    # 设置调度
    setup_long_term_schedule()
    
    # 启动调度器线程
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    logger.info("长周期策略调度器已启动")
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("长周期策略系统已停止")

if __name__ == "__main__":
    main()