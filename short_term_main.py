import time
import schedule
import threading
from datetime import datetime
from strategy.short_term.data_fetcher import ShortTermDataFetcher
from strategy.short_term.strategy_engine import ShortTermDMRStrategy
from strategy.short_term.order_executor import ShortTermOrderExecutor
from strategy.short_term.position_manager import ShortTermPositionManager
from strategy.short_term.risk_manager import ShortTermRiskManager
from config.short_term_config import SHORT_TERM_CONFIG
from utils.logger import setup_logger

def run_short_term_strategy():
    """运行短周期策略"""
    logger = setup_logger(
        name='ShortTermMain',
        log_file=SHORT_TERM_CONFIG['log_config']['log_file']
    )
    
    try:
        # 初始化各个模块
        data_fetcher = ShortTermDataFetcher()
        position_manager = ShortTermPositionManager(data_fetcher.exchange)
        order_executor = ShortTermOrderExecutor(data_fetcher.exchange, position_manager)  # 修复：添加position_manager参数
        risk_manager = ShortTermRiskManager(data_fetcher.exchange)
        
        # 获取并保存数据
        df = data_fetcher.get_and_save_data()
        if df is None:
            logger.error("短周期策略数据获取失败，跳过本次执行")
            return
        
        # 初始化策略引擎
        strategy = ShortTermDMRStrategy(
            data_fetcher, order_executor, position_manager, risk_manager
        )
        
        # 启动时状态核对
        strategy.reconcile_state()
        
        # 运行策略，传入已获取和处理好的数据
        strategy.run_strategy(df)
        
        logger.info("短周期策略执行完成")
        
    except Exception as e:
        logger.error(f"短周期策略执行失败: {e}")

def setup_short_term_schedule():
    """设置短周期策略调度"""
    timeframe = SHORT_TERM_CONFIG['timeframe']
    
    if timeframe == '5m':
        for minute in range(0, 60, 5):
            schedule.every().hour.at(f":{minute:02d}").do(run_short_term_strategy)
    elif timeframe == '15m':
        for minute in [0, 15, 30, 45]:
            schedule.every().hour.at(f":{minute:02d}").do(run_short_term_strategy)
    elif timeframe == '30m':
        for minute in [0, 30]:
            schedule.every().hour.at(f":{minute:02d}").do(run_short_term_strategy)
    elif timeframe == '1h':
        schedule.every().hour.at(":00").do(run_short_term_strategy)

def run_scheduler():
    """运行调度器"""
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    """短周期策略主程序"""
    logger = setup_logger(
        name='ShortTermMain',
        log_file=SHORT_TERM_CONFIG['log_config']['log_file']
    )
    
    logger.info("启动短周期DMR26策略系统")
    
    # 设置调度
    setup_short_term_schedule()
    
    # 启动调度器线程
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    logger.info("短周期策略调度器已启动")
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("短周期策略系统已停止")

if __name__ == "__main__":
    main()