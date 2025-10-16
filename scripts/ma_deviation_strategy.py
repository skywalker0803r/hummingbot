# scripts/ma_deviation_strategy.py

from hummingbot.strategy.script_strategy_base import ScriptStrategyBase
import pandas as pd

class MaDeviationStrategy(ScriptStrategyBase):
    """
    20MA 乖離率策略：
    - 價格向下偏離 MA20 0.5% 做多，回到均線平多
    - 價格向上偏離 MA20 0.5% 做空，回到均線平空
    """

    def __init__(self):
        super().__init__()
        self.lookback = 20  # MA天數
        self.threshold = 0.005  # 乖離率閾值 0.5%
        self.prices = []
        self.position = 0  # 1 = 多, -1 = 空, 0 = 無
        self.order_size = 0.001  # BTC 下單數量，可修改

    def on_tick(self, market_pair: str, price: float):
        # 保存價格
        self.prices.append(price)
        if len(self.prices) < self.lookback:
            return

        ma20 = pd.Series(self.prices[-self.lookback:]).mean()
        deviation = (price - ma20) / ma20

        # 日誌
        self.log(f"Price: {price:.2f}, MA20: {ma20:.2f}, Deviation: {deviation:.4f}, Position: {self.position}")

        # 做多邏輯
        if deviation <= -self.threshold:
            if self.position != 1:
                self.buy(market_pair, self.order_size, price)
                self.position = 1
        elif deviation >= 0 and self.position == 1:
            self.sell(market_pair, self.order_size, price)
            self.position = 0

        # 做空邏輯
        if deviation >= self.threshold:
            if self.position != -1:
                self.sell(market_pair, self.order_size, price)
                self.position = -1
        elif deviation <= 0 and self.position == -1:
            self.buy(market_pair, self.order_size, price)
            self.position = 0

    # 下面函數會呼叫 Hummingbot API 下單
    def buy(self, market_pair: str, amount: float, price: float):
        self.logger().info(f"[LONG] Buy {amount} {market_pair} at {price}")
        self.market_buy(market_pair, amount, order_type="market")

    def sell(self, market_pair: str, amount: float, price: float):
        self.logger().info(f"[SHORT/平倉] Sell {amount} {market_pair} at {price}")
        self.market_sell(market_pair, amount, order_type="market")
