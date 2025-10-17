import os  
from decimal import Decimal  
from typing import Dict  
  
import pandas_ta as ta  
from pydantic import Field  
  
from hummingbot.client.config.config_data_types import BaseClientModel  
from hummingbot.connector.connector_base import ConnectorBase  
from hummingbot.core.data_type.common import OrderType, TradeType  
from hummingbot.data_feed.candles_feed.candles_factory import CandlesFactory  
from hummingbot.data_feed.candles_feed.data_types import CandlesConfig  
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase  
  
  
class MACDCrossoverConfig(BaseClientModel):  
    script_file_name: str = Field(default_factory=lambda: os.path.basename(__file__))  
    exchange: str = Field("binance_paper_trade", json_schema_extra={  
        "prompt": "Enter the exchange name (e.g., binance_paper_trade)", "prompt_on_new": True})  
    trading_pair: str = Field("BTC-USDT", json_schema_extra={  
        "prompt": "Enter the trading pair (e.g., BTC-USDT)", "prompt_on_new": True})  
    order_amount: Decimal = Field(Decimal("0.001"), json_schema_extra={  
        "prompt": "Enter the order amount in base asset", "prompt_on_new": True})  
    candle_interval: str = Field("5m", json_schema_extra={  
        "prompt": "Enter the candle interval (e.g., 1m, 5m, 15m, 1h)", "prompt_on_new": True})  
    macd_fast: int = Field(12, json_schema_extra={  
        "prompt": "Enter MACD fast period", "prompt_on_new": True})  
    macd_slow: int = Field(26, json_schema_extra={  
        "prompt": "Enter MACD slow period", "prompt_on_new": True})  
    macd_signal: int = Field(9, json_schema_extra={  
        "prompt": "Enter MACD signal period", "prompt_on_new": True})  
  
  
class MACDCrossoverStrategy(ScriptStrategyBase):  
    """  
    Simple MACD Golden Cross / Death Cross strategy  
    - Golden Cross: MACD line crosses above signal line -> BUY  
    - Death Cross: MACD line crosses below signal line -> SELL  
    """  
  
    @classmethod  
    def init_markets(cls, config: MACDCrossoverConfig):  
        cls.markets = {config.exchange: {config.trading_pair}}  
  
    def __init__(self, connectors: Dict[str, ConnectorBase], config: MACDCrossoverConfig):  
        super().__init__(connectors)  
        self.config = config  
          
        # Initialize candles feed  
        self.candles = CandlesFactory.get_candle(  
            CandlesConfig(  
                connector=config.exchange,  
                trading_pair=config.trading_pair,  
                interval=config.candle_interval,  
                max_records=200  
            )  
        )  
        self.candles.start()  
          
        # Track previous MACD values to detect crossover  
        self.prev_macd = None  
        self.prev_signal = None  
        self.position = None  # Track current position: 'long', 'short', or None  
  
    def on_tick(self):  
        if not self.candles.ready:  
            return  
          
        # Get candles dataframe and calculate MACD  
        df = self.candles.candles_df  
        df.ta.macd(  
            fast=self.config.macd_fast,  
            slow=self.config.macd_slow,  
            signal=self.config.macd_signal,  
            append=True  
        )  
          
        # Get latest MACD values  
        macd_col = f"MACD_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"  
        signal_col = f"MACDs_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"  
          
        current_macd = df[macd_col].iloc[-1]  
        current_signal = df[signal_col].iloc[-1]  
          
        # Detect crossover  
        if self.prev_macd is not None and self.prev_signal is not None:  
            # Golden Cross: MACD crosses above signal  
            if self.prev_macd <= self.prev_signal and current_macd > current_signal:  
                if self.position != 'long':  
                    self.execute_trade(TradeType.BUY, "Golden Cross detected")  
                    self.position = 'long'  
              
            # Death Cross: MACD crosses below signal  
            elif self.prev_macd >= self.prev_signal and current_macd < current_signal:  
                if self.position != 'short':  
                    self.execute_trade(TradeType.SELL, "Death Cross detected")  
                    self.position = 'short'  
          
        # Update previous values  
        self.prev_macd = current_macd  
        self.prev_signal = current_signal  
  
    def execute_trade(self, trade_type: TradeType, reason: str):  
        """Execute a market order"""  
        connector = self.connectors[self.config.exchange]  
        price = connector.get_mid_price(self.config.trading_pair)  
          
        self.logger().info(f"{reason} - Placing {trade_type.name} order at {price}")  
          
        self.buy(  
            connector_name=self.config.exchange,  
            trading_pair=self.config.trading_pair,  
            amount=self.config.order_amount,  
            order_type=OrderType.MARKET  
        ) if trade_type == TradeType.BUY else self.sell(  
            connector_name=self.config.exchange,  
            trading_pair=self.config.trading_pair,  
            amount=self.config.order_amount,  
            order_type=OrderType.MARKET  
        )  
  
    async def on_stop(self):  
        """Stop the candles feed when strategy stops"""  
        self.candles.stop()  
  
    def format_status(self) -> str:  
        """Display strategy status"""  
        if not self.ready_to_trade:  
            return "Market connectors are not ready."  
          
        lines = ["\n========== MACD Crossover Strategy =========="]  
          
        if self.candles.ready:  
            df = self.candles.candles_df  
            df.ta.macd(  
                fast=self.config.macd_fast,  
                slow=self.config.macd_slow,  
                signal=self.config.macd_signal,  
                append=True  
            )  
              
            macd_col = f"MACD_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"  
            signal_col = f"MACDs_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"  
              
            current_macd = df[macd_col].iloc[-1]  
            current_signal = df[signal_col].iloc[-1]  
              
            lines.append(f"Exchange: {self.config.exchange}")  
            lines.append(f"Trading Pair: {self.config.trading_pair}")  
            lines.append(f"Current Position: {self.position or 'None'}")  
            lines.append(f"MACD: {current_macd:.6f}")  
            lines.append(f"Signal: {current_signal:.6f}")  
            lines.append(f"Histogram: {current_macd - current_signal:.6f}")  
        else:  
            lines.append("Waiting for candle data...")  
          
        return "\n".join(lines)