import os  
from decimal import Decimal  
from typing import Dict  
from collections import deque  
  
import pandas_ta as ta  
from pydantic import Field  
  
from hummingbot.client.config.config_data_types import BaseClientModel  
from hummingbot.connector.connector_base import ConnectorBase  
from hummingbot.core.data_type.common import OrderType, TradeType  
from hummingbot.data_feed.candles_feed.candles_factory import CandlesFactory  
from hummingbot.data_feed.candles_feed.data_types import CandlesConfig  
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase  
  
  
class MACDPeakTroughConfig(BaseClientModel):  
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
  
  
class MACDPeakTroughStrategy(ScriptStrategyBase):  
    """  
    Strategy that buys on MACD negative peaks and sells on MACD positive peaks.  
    - Buys when the MACD line forms a trough in the negative zone.  
    - Sells when the MACD line forms a peak in the positive zone.  
    """  

    @classmethod  
    def init_markets(cls, config: MACDPeakTroughConfig):  
        cls.markets = {config.exchange: {config.trading_pair}}  

    def __init__(self, connectors: Dict[str, ConnectorBase], config: MACDPeakTroughConfig):  
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
          
        # Track previous MACD values to detect peaks  
        self.macd_values = deque(maxlen=3)  
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
          
        # Get latest MACD value  
        macd_col = f"MACD_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"  
        current_macd = df[macd_col].iloc[-1]  

        self.macd_values.append(current_macd)  

        if len(self.macd_values) == 3:  
            m1, m2, m3 = self.macd_values[0], self.macd_values[1], self.macd_values[2]  

            # Sell at positive peak  
            is_positive_peak = m1 < m2 and m2 > m3 and m2 > 0  
            if is_positive_peak and self.position != 'short':  
                self.execute_trade(TradeType.SELL, "MACD positive peak detected")  
                self.position = 'short'  

            # Buy at negative peak  
            is_negative_peak = m1 > m2 and m2 < m3 and m2 < 0  
            if is_negative_peak and self.position != 'long':  
                self.execute_trade(TradeType.BUY, "MACD negative peak detected")  
                self.position = 'long'  

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
          
        lines = ["\n========== MACD Peak Trough Strategy =========="]  
          
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