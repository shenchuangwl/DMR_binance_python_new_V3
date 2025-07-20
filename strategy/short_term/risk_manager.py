import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from config.short_term_config import SHORT_TERM_CONFIG

class ShortTermRiskManager:
    def __init__(self, exchange):
        self.exchange = exchange
        self.config = SHORT_TERM_CONFIG
        self.max_daily_loss = self.config.get('max_daily_loss', 0.03)
        self.max_drawdown = self.config.get('max_drawdown', 0.05)
        self.daily_pnl = 0
        self.total_pnl = 0

    def check_risk_limits(self):
        """检查风险限制"""
        # 检查日损失限制
        if abs(self.daily_pnl) > self.max_daily_loss:
            print(f"短期策略触发日损失限制: {self.daily_pnl:.2%}")
            return False
        
        # 检查最大回撤限制
        if abs(self.total_pnl) > self.max_drawdown:
            print(f"短期策略触发最大回撤限制: {self.total_pnl:.2%}")
            return False
        
        return True

    def update_pnl(self, pnl):
        """更新盈亏"""
        self.daily_pnl += pnl
        self.total_pnl += pnl

    def reset_daily_pnl(self):
        """重置日盈亏"""
        self.daily_pnl = 0

    def calculate_position_risk(self, position_size, current_price):
        """计算仓位风险"""
        position_value = position_size * current_price
        account_balance = self.get_account_balance()
        if account_balance > 0:
            risk_ratio = position_value / account_balance
            return risk_ratio
        return 0

    def get_account_balance(self):
        """获取账户余额"""
        try:
            balance = self.exchange.fetch_balance()
            return balance.get('total', {}).get('USDT', 0)
        except Exception as e:
            print(f"获取账户余额失败: {e}")
            return 0