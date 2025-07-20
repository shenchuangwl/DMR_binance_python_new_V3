from config.testnet_config import TESTNET_API_KEY, TESTNET_API_SECRET
import ccxt
import time

class TestnetOrderExecutor:
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': TESTNET_API_KEY,
            'secret': TESTNET_API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True,
                'testnet': True
            }
        })
        # 初始化时设置双向持仓模式
        try:
            self.exchange.fapiPrivatePostPositionSideDual({'dualSidePosition': True})
            print("Successfully set dual position mode")
        except Exception as e:
            print(f"Error setting position mode: {e}")

    def initialize_trading_config(self, symbol):
        """初始化交易配置"""
        try:
            # 设置杠杆倍数为5倍
            self.exchange.fapiPrivatePostLeverage({
                'symbol': symbol.replace('/', ''),
                'leverage': 5
            })
            
            # 设置保证金模式为全仓模式
            self.exchange.fapiPrivatePostMarginType({
                'symbol': symbol.replace('/', ''),
                'marginType': 'CROSSED'  # 将 'ISOLATED' 改为 'CROSSED'
            })
            print(f"Trading configuration initialized for {symbol}")
        except Exception as e:
            print(f"Error initializing trading config: {e}")

    def get_position_info(self, symbol):
        """获取当前持仓信息"""
        try:
            positions = self.exchange.fetch_positions([symbol])
            position_info = {}
            for pos in positions:
                if pos['positionSide'] == 'LONG':
                    position_info['long'] = float(pos['contracts'])
                elif pos['positionSide'] == 'SHORT':
                    position_info['short'] = float(pos['contracts'])
            return position_info
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return {'long': 0, 'short': 0}

    def open_long(self, symbol, amount):
        """开多仓"""
        try:
            # 确保交易配置已初始化
            self.initialize_trading_config(symbol)
            
            # 获取最新价格并计算数量
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker['last']
            quantity = round(amount / price, 3)  # 将100USDT转换为对应的数量
            
            # 确保下单金额正确
            if amount != POSITION_SIZE:
                print(f"Warning: Order amount adjusted to {POSITION_SIZE} USDT")
                amount = POSITION_SIZE
                quantity = round(amount / price, 3)
            
            order = self.exchange.create_market_order(
                symbol=symbol,
                side='BUY',
                amount=quantity,
                params={
                    'positionSide': 'LONG',
                    'type': 'MARKET'
                }
            )
            print(f"Successfully opened long position: Amount={amount}USDT, Quantity={quantity}, Price={price}")
            return order
        except Exception as e:
            print(f"Error opening long position: {e}")
            return None

    def open_short(self, symbol, amount):
        """开空仓"""
        try:
            # 确保交易配置已初始化
            self.initialize_trading_config(symbol)
            
            # 获取最新价格并计算数量
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker['last']
            quantity = round(amount / price, 3)  # 将100USDT转换为对应的数量
            
            # 确保下单金额正确
            if amount != POSITION_SIZE:
                print(f"Warning: Order amount adjusted to {POSITION_SIZE} USDT")
                amount = POSITION_SIZE
                quantity = round(amount / price, 3)
            
            order = self.exchange.create_market_order(
                symbol=symbol,
                side='SELL',
                amount=quantity,
                params={
                    'positionSide': 'SHORT',
                    'type': 'MARKET'
                }
            )
            print(f"Successfully opened short position: Amount={amount}USDT, Quantity={quantity}, Price={price}")
            return order
        except Exception as e:
            print(f"Error opening short position: {e}")
            return None

    def close_position(self, symbol, position_side):
        """平掉指定方向的仓位"""
        try:
            positions = self.exchange.fetch_positions([symbol])
            for position in positions:
                if position['positionSide'] == position_side and float(position['contracts']) != 0:
                    side = 'SELL' if position_side == 'LONG' else 'BUY'
                    self.exchange.create_market_order(
                        symbol=symbol,
                        side=side,
                        amount=abs(float(position['contracts'])),
                        params={
                            'positionSide': position_side,
                            'type': 'MARKET',
                            'reduceOnly': True
                        }
                    )
            print(f"Successfully closed {position_side} position for {symbol}")
        except Exception as e:
            print(f"Error closing {position_side} position: {e}")

    def close_all_positions(self, symbol):
        """平掉所有仓位"""
        try:
            # 分别平掉多头和空头仓位
            self.close_position(symbol, 'LONG')
            time.sleep(1)  # 添加延时，避免请求过快
            self.close_position(symbol, 'SHORT')
            print(f"Successfully closed all positions for {symbol}")
        except Exception as e:
            print(f"Error closing positions: {e}")

    def execute(self, results):
        """执行策略结果"""
        # 这里可以根据策略结果执行具体的交易
        pass