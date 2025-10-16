import os  
from decimal import Decimal  
from typing import Dict, List  
from pydantic import Field  
  
from hummingbot.client.config.config_data_types import BaseClientModel  
from hummingbot.connector.connector_base import ConnectorBase  
from hummingbot.data_feed.candles_feed.data_types import CandlesConfig  
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase  
  
  
class MaDeviationConfig(BaseClientModel):  
    """MA 乖離率策略配置"""  
    script_file_name: str = Field(default_factory=lambda: os.path.basename(__file__))  
      
    connector_name: str = Field(  
        "binance_paper_trade",  
        json_schema_extra={"prompt": "交易所名稱 (例如 binance_paper_trade)", "prompt_on_new": True}  
    )  
      
    trading_pair: str = Field(  
        "BTC-USDT",  
        json_schema_extra={"prompt": "交易對 (例如 BTC-USDT)", "prompt_on_new": True}  
    )  
      
    # K 線週期配置  
    candles_connector: str = Field(  
        "binance",  
        json_schema_extra={"prompt": "K 線數據來源交易所 (例如 binance)", "prompt_on_new": True}  
    )  
      
    candles_trading_pair: str = Field(  
        "BTC-USDT",  
        json_schema_extra={"prompt": "K 線交易對 (例如 BTC-USDT)", "prompt_on_new": True}  
    )  
      
    interval: str = Field(  
        "15m",  
        json_schema_extra={"prompt": "K 線週期 (例如 1m, 5m, 15m, 1h, 1d)", "prompt_on_new": True}  
    )  
      
    lookback: int = Field(  
        20,  
        json_schema_extra={"prompt": "MA 週期 (K 線數量)", "prompt_on_new": True}  
    )  
      
    threshold: Decimal = Field(  
        Decimal("0.005"),  
        json_schema_extra={"prompt": "乖離率閾值 (0.005 = 0.5%)", "prompt_on_new": True}  
    )  
      
    order_size: Decimal = Field(  
        Decimal("0.001"),  
        json_schema_extra={"prompt": "下單數量", "prompt_on_new": True}  
    )  
  
  
class MaDeviationStrategy(ScriptStrategyBase):  
    """基於 K 線的 20MA 乖離率策略"""  
      
    @classmethod  
    def init_markets(cls, config: MaDeviationConfig):  
        cls.markets = {config.connector_name: {config.trading_pair}}  
      
    def __init__(self, connectors: Dict[str, ConnectorBase], config: MaDeviationConfig):  
        super().__init__(connectors)  
        self.config = config  
        self.position = 0  
          
        # 初始化 Candles Feed  
        from hummingbot.data_feed.candles_feed.candles_factory import CandlesFactory  
        self.candles = CandlesFactory.get_candle(CandlesConfig(  
            connector=config.candles_connector,  
            trading_pair=config.candles_trading_pair,  
            interval=config.interval,  
            max_records=config.lookback + 50  # 多保留一些數據  
        ))  
        self.candles.start()  
      
    def on_tick(self):  
        # 檢查 K 線數據是否準備好  
        if not self.candles.ready:  
            self.logger().info("等待 K 線數據...")  
            return  
          
        # 獲取 K 線 DataFrame  
        df = self.candles.candles_df  
        if len(df) < self.config.lookback:  
            return  
          
        # 計算 MA  
        ma = df['close'].tail(self.config.lookback).mean()  
        current_price = df['close'].iloc[-1]  
        deviation = (current_price - ma) / ma  
          
        self.logger().info(  
            f"Price: {current_price:.2f}, MA{self.config.lookback}: {ma:.2f}, "  
            f"Deviation: {deviation:.4f}, Position: {self.position}"  
        )  
          
        # 交易邏輯  
        connector = self.connectors[self.config.connector_name]  
        threshold = float(self.config.threshold)  
          
        if deviation <= -threshold and self.position != 1:  
            self.buy(connector, self.config.trading_pair, float(self.config.order_size))  
            self.position = 1  
        elif deviation >= 0 and self.position == 1:  
            self.sell(connector, self.config.trading_pair, float(self.config.order_size))  
            self.position = 0  
        elif deviation >= threshold and self.position != -1:  
            self.sell(connector, self.config.trading_pair, float(self.config.order_size))  
            self.position = -1  
        elif deviation <= 0 and self.position == -1:  
            self.buy(connector, self.config.trading_pair, float(self.config.order_size))  
            self.position = 0  
      
    async def on_stop(self):  
        """停止時清理 Candles Feed"""  
        self.candles.stop()