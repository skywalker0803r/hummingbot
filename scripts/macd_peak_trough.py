import os
import asyncio
from decimal import Decimal
from typing import Dict, Set, List, Deque
from collections import deque

import pandas_ta as ta
from pydantic import Field

from hummingbot.client.config.config_data_types import BaseClientModel
from hummingbot.connector.connector_base import ConnectorBase
from hummingbot.core.data_type.common import OrderType, PositionAction, PositionMode, PositionSide, TradeType
from hummingbot.data_feed.candles_feed.candles_factory import CandlesFactory
from hummingbot.data_feed.candles_feed.data_types import CandlesConfig
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase
from hummingbot.strategy_v2.executors.position_executor.data_types import PositionExecutorConfig, TripleBarrierConfig
from hummingbot.strategy_v2.executors.position_executor.position_executor import PositionExecutor


class MACDPeakTroughConfig(BaseClientModel):
    script_file_name: str = Field(default_factory=lambda: os.path.basename(__file__))
    exchange: str = Field("binance_perpetual", json_schema_extra={
        "prompt": "Enter the exchange name (e.g., binance_perpetual)", "prompt_on_new": True})
    trading_pair: str = Field("BTC-USDT", json_schema_extra={
        "prompt": "Enter the trading pair (e.g., BTC-USDT)", "prompt_on_new": True})
    order_amount: Decimal = Field(Decimal("0.001"), json_schema_extra={
        "prompt": "Enter the order amount in base asset", "prompt_on_new": True})
    leverage: int = Field(20, json_schema_extra={
        "prompt": "Enter the leverage (e.g., 20)", "prompt_on_new": True})
    position_mode: str = Field("ONEWAY", json_schema_extra={
        "prompt": "Enter the position mode (ONEWAY/HEDGE)", "prompt_on_new": False})
    candle_interval: str = Field("5m", json_schema_extra={
        "prompt": "Enter the candle interval (e.g., 1m, 5m, 15m, 1h)", "prompt_on_new": True})
    macd_fast: int = Field(12, json_schema_extra={
        "prompt": "Enter MACD fast period", "prompt_on_new": True})
    macd_slow: int = Field(26, json_schema_extra={
        "prompt": "Enter MACD slow period", "prompt_on_new": True})
    macd_signal: int = Field(9, json_schema_extra={
        "prompt": "Enter MACD signal period", "prompt_on_new": True})
    take_profit_pct: Decimal = Field(Decimal("0.002"), json_schema_extra={
        "prompt": "Enter the take profit percentage (e.g., 0.002 for 0.2%)", "prompt_on_new": True})
    stop_loss_pct: Decimal = Field(Decimal("0.02"), json_schema_extra={
        "prompt": "Enter the stop loss percentage (e.g., 0.02 for 2%)", "prompt_on_new": True})


class MACDPeakTroughStrategy(ScriptStrategyBase):
    """
    Strategy that buys on MACD negative peaks and sells on MACD positive peaks, with take profit and stop loss,
    using PositionExecutor to manage trades.
    """
    max_executors = 1

    @classmethod
    def init_markets(cls, config: MACDPeakTroughConfig):
        cls.markets = {config.exchange: {config.trading_pair}}

    def __init__(self, connectors: Dict[str, ConnectorBase], config: MACDPeakTroughConfig):
        super().__init__(connectors)
        self.config = config
        self.candles = CandlesFactory.get_candle(
            CandlesConfig(
                connector=config.exchange,
                trading_pair=config.trading_pair,
                interval=config.candle_interval,
                max_records=200
            )
        )
        self.candles.start()
        self.macd_values = deque(maxlen=3)
        self.last_candle_timestamp = 0
        self.leverage_set = False
        self.active_executors: List[PositionExecutor] = []
        self.stored_executors: Deque[PositionExecutor] = deque(maxlen=10)

    def check_and_set_leverage(self):
        if not self.leverage_set:
            try:
                connector = self.connectors[self.config.exchange]
                if self.config.position_mode == "ONEWAY":
                    connector.set_position_mode(PositionMode.ONEWAY)
                elif self.config.position_mode == "HEDGE":
                    connector.set_position_mode(PositionMode.HEDGE)
                else:
                    self.logger().warning(f"Position mode {self.config.position_mode} is not supported. Using ONEWAY.")
                    connector.set_position_mode(PositionMode.ONEWAY)
                connector.set_leverage(self.config.trading_pair, self.config.leverage)
                self.leverage_set = True
                self.logger().info(f"Leverage set to {self.config.leverage} and position mode to {self.config.position_mode}.")
            except Exception as e:
                self.logger().error(f"Error setting leverage or position mode: {e}")

    def on_tick(self):
        self.check_and_set_leverage()
        self.clean_and_store_executors()

        if len(self.active_executors) < self.max_executors and self.candles.ready:
            df = self.candles.candles_df
            df.ta.macd(fast=self.config.macd_fast, slow=self.config.macd_slow, signal=self.config.macd_signal, append=True)
            macd_col = f"MACD_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"
            
            # Use the timestamp of the latest candle to check for new data
            current_timestamp = df["timestamp"].iloc[-1]
            if current_timestamp > self.last_candle_timestamp:
                self.last_candle_timestamp = current_timestamp
                
                current_macd = df[macd_col].iloc[-1]
                self.macd_values.append(current_macd)
                self.logger().info(f"New MACD value appended: {current_macd:.6f}. Queue: {list(self.macd_values)}")

                if len(self.macd_values) == 3:
                    m1, m2, m3 = self.macd_values[0], self.macd_values[1], self.macd_values[2]
                    self.logger().info(f"MACD values: m1={m1:.6f}, m2={m2:.6f}, m3={m3:.6f}")
                    
                    # Logic to identify peak or trough remains the same
                    is_positive_peak = m1 < m2 and m2 > m3 and m2 > 0
                    is_negative_peak = m1 > m2 and m2 < m3 and m2 < 0
                    self.logger().info(f"Peak detection: is_positive_peak={is_positive_peak}, is_negative_peak={is_negative_peak}")

                    if is_positive_peak or is_negative_peak:
                        price = self.connectors[self.config.exchange].get_mid_price(self.config.trading_pair)
                        side = TradeType.SELL if is_positive_peak else TradeType.BUY
                        
                        executor_config = PositionExecutorConfig(
                            timestamp=self.current_timestamp,
                            trading_pair=self.config.trading_pair,
                            connector_name=self.config.exchange,
                            side=side,
                            entry_price=price,
                            amount=self.config.order_amount,
                            leverage=self.config.leverage,
                            triple_barrier_config=TripleBarrierConfig(
                                stop_loss=self.config.stop_loss_pct,
                                take_profit=self.config.take_profit_pct,
                            )
                        )
                        executor = PositionExecutor(config=executor_config, strategy=self)
                        self.active_executors.append(executor)
                        executor.start()  # Start the executor
                        self.logger().info(f"Created and started new {side.name} position executor.")
                    else:
                        self.logger().info("No peak or trough detected.")

    def clean_and_store_executors(self):
        executors_to_store = [executor for executor in self.active_executors if executor.is_closed]
        for executor in executors_to_store:
            self.stored_executors.append(executor)
        self.active_executors = [executor for executor in self.active_executors if not executor.is_closed]

    async def on_stop(self):
        self.logger().info("Strategy stopped. Closing all open positions...")
        # 1. First, call early_stop() to trigger the closing process
        for executor in self.active_executors:
            if not executor.is_closed:
                executor.early_stop()
        
        # 2. Wait for all executors to be closed (try up to 3 times, waiting 2 seconds each time)
        for i in range(3):
            if all([executor.is_closed for executor in self.active_executors]):
                break
            await asyncio.sleep(2.0)
        
        # 3. Stop the candle feed
        self.candles.stop()

    def format_status(self) -> str:
        if not self.ready_to_trade:
            return "Market connectors are not ready."
        lines = []
        warning_lines = []
        warning_lines.extend(self.network_warning(self.get_market_trading_pair_tuples()))
        lines.extend(warning_lines)
        
        lines.append("\n========== MACD Peak Trough Perpetuals Strategy ==========")
        lines.append(f"Exchange: {self.config.exchange} | Trading Pair: {self.config.trading_pair}")
        
        if self.candles.ready:
            df = self.candles.candles_df
            macd_col = f"MACD_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"
            if macd_col in df.columns:
                current_macd = df[macd_col].iloc[-1]
                lines.append(f"MACD: {current_macd:.6f}")
            else:
                lines.append("MACD not available yet.")
        else:
            lines.append("Waiting for candle data...")

        if len(self.stored_executors) > 0:
            lines.append("\n########################################## Closed Executors ##########################################")
            for executor in self.stored_executors:
                lines.extend([f"|Signal id: {executor.config.timestamp}"])
                lines.extend(executor.to_format_status())
                lines.extend(["-----------------------------------------------------------------------------------------------------------"])

        if len(self.active_executors) > 0:
            lines.append("\n########################################## Active Executors ##########################################")
            for executor in self.active_executors:
                lines.extend([f"|Signal id: {executor.config.timestamp}"])
                lines.extend(executor.to_format_status())
        
        return "\n".join(lines)
