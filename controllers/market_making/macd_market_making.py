from decimal import Decimal
from typing import List

import pandas_ta as ta
from pydantic import Field

from hummingbot.data_feed.candles_feed.data_types import CandlesConfig
from hummingbot.strategy_v2.controllers.market_making_controller_base import (
    MarketMakingControllerBase,
    MarketMakingControllerConfigBase,
)
from hummingbot.strategy_v2.executors.position_executor.data_types import PositionExecutorConfig


class MACDMarketMakingConfig(MarketMakingControllerConfigBase):
    controller_name: str = "macd_market_making"
    candles_config: List[CandlesConfig] = []
    interval: str = Field(default="3m", json_schema_extra={
        "prompt": "Enter candle interval: ", "prompt_on_new": True})
    macd_fast: int = Field(default=12, json_schema_extra={
        "prompt": "Enter MACD fast: ", "prompt_on_new": True})
    macd_slow: int = Field(default=26, json_schema_extra={
        "prompt": "Enter MACD slow: ", "prompt_on_new": True})
    macd_signal: int = Field(default=9, json_schema_extra={
        "prompt": "Enter MACD signal: ", "prompt_on_new": True})
    volatility_factor: Decimal = Field(default=Decimal("0.01"), json_schema_extra={
        "prompt": "Enter volatility factor: ", "prompt_on_new": True})


class MACDMarketMakingController(MarketMakingControllerBase):
    def __init__(self, config: MACDMarketMakingConfig, *args, **kwargs):
        self.config = config
        self.max_records = max(config.macd_slow, config.macd_fast, config.macd_signal) + 100
        if len(self.config.candles_config) == 0:
            self.config.candles_config = [CandlesConfig(
                connector=config.connector_name,
                trading_pair=config.trading_pair,
                interval=config.interval,
                max_records=self.max_records
            )]
        super().__init__(config, *args, **kwargs)

    async def update_processed_data(self):
        candles = self.market_data_provider.get_candles_df(
            connector_name=self.config.connector_name,
            trading_pair=self.config.trading_pair,
            interval=self.config.interval,
            max_records=self.max_records
        )
        
        macd_output = ta.macd(candles["close"], fast=self.config.macd_fast, 
                             slow=self.config.macd_slow, signal=self.config.macd_signal)
        macd = macd_output[f"MACD_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"]
        macd_signal = -(macd - macd.mean()) / macd.std()
        
        price_multiplier = Decimal(macd_signal.iloc[-1]) * self.config.volatility_factor
        reference_price = Decimal(candles["close"].iloc[-1]) * (Decimal("1") + price_multiplier)
        
        # Calculate NATR for dynamic spread
        natr = ta.natr(candles["high"], candles["low"], candles["close"], length=14) / 100

        self.processed_data = {
            "reference_price": reference_price,
            "spread_multiplier": Decimal(natr.iloc[-1])
        }

    def get_executor_config(self, level_id: str, price: Decimal, amount: Decimal):
        trade_type = self.get_trade_type_from_level_id(level_id)
        return PositionExecutorConfig(
            timestamp=self.market_data_provider.time(),
            level_id=level_id,
            connector_name=self.config.connector_name,
            trading_pair=self.config.trading_pair,
            entry_price=price,
            amount=amount,
            triple_barrier_config=self.config.triple_barrier_config,
            leverage=self.config.leverage,
            side=trade_type,
        )
