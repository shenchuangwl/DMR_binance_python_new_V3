import json
import os
from datetime import datetime
from typing import Dict, Optional, Any

class StrategyPositionManager:
    """策略持仓管理器 - 跟踪每个策略的独立持仓"""
    
    def __init__(self, strategy_name: str, symbol: str):
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.position_file = f"/tmp/{strategy_name}_position_{symbol.replace('/', '_')}.json"
        self.position = self._load_position()
    
    def _load_position(self) -> Optional[Dict[str, Any]]:
        """从文件加载策略持仓"""
        try:
            if os.path.exists(self.position_file):
                with open(self.position_file, 'r') as f:
                    return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return None
    
    def _save_position(self):
        """保存策略持仓到文件"""
        try:
            with open(self.position_file, 'w') as f:
                json.dump(self.position, f, default=str, indent=2)
        except Exception as e:
            print(f"保存{self.strategy_name}策略持仓失败: {e}")
    
    def update_position(self, side: str, amount: float, price: float, action: str = 'open'):
        """更新策略持仓"""
        if action == 'open':
            self.position = {
                'side': side,
                'amount': amount,
                'entry_price': price,
                'timestamp': datetime.now().isoformat(),
                'strategy': self.strategy_name
            }
        elif action == 'close':
            self.position = None
        
        self._save_position()
    
    def get_position(self) -> Optional[Dict[str, Any]]:
        """获取策略持仓"""
        return self.position
    
    def has_position(self, side: str = None) -> bool:
        """检查是否有持仓"""
        if not self.position:
            return False
        if side:
            return self.position.get('side') == side
        return True
    
    def clear_position(self):
        """清除策略持仓记录"""
        self.position = None
        if os.path.exists(self.position_file):
            os.remove(self.position_file)