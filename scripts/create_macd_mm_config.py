import os
import yaml
from decimal import Decimal
from typing import Dict, List

from pydantic import Field

from hummingbot.client.config.config_data_types import BaseClientModel
from hummingbot.connector.connector_base import ConnectorBase
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase


class GenConfig(BaseClientModel):
    script_file_name: str = Field(default_factory=lambda: os.path.basename(__file__))
    
    # Controller settings
    controller_name: str = "macd_market_making"
    controller_type: str = "market_making"

    # Exchange and market settings
    connector_name: str = Field(default="binance_perpetual", json_schema_extra={"prompt": "Enter the exchange name: "})
    trading_pair: str = Field(default="ENSO-USDT", json_schema_extra={"prompt": "Enter the trading pair: "})

    # Market making parameters
    total_amount_quote: Decimal = Field(default=Decimal("1000.0"), json_schema_extra={"prompt": "Enter the total amount in quote asset: "})
    buy_spreads: List[Decimal] = Field(default=[Decimal("0.01"), Decimal("0.02")], json_schema_extra={"prompt": "Enter a comma-separated list of buy spreads (e.g., 0.01,0.02): "})
    sell_spreads: List[Decimal] = Field(default=[Decimal("0.01"), Decimal("0.02")], json_schema_extra={"prompt": "Enter a comma-separated list of sell spreads (e.g., 0.01,0.02): "})
    buy_amounts_pct: List[Decimal] = Field(default=[Decimal("0.5"), Decimal("0.5")], json_schema_extra={"prompt": "Enter a comma-separated list of buy amount percentages (e.g., 0.5,0.5): "})
    sell_amounts_pct: List[Decimal] = Field(default=[Decimal("0.5"), Decimal("0.5")], json_schema_extra={"prompt": "Enter a comma-separated list of sell amount percentages (e.g., 0.5,0.5): "})
    executor_refresh_time: int = Field(default=30, json_schema_extra={"prompt": "Enter the order refresh time in seconds: "})

    # Perpetual contract settings
    leverage: int = Field(default=20, json_schema_extra={"prompt": "Enter the leverage: "})
    position_mode: str = Field(default="HEDGE", json_schema_extra={"prompt": "Enter the position mode (ONEWAY/HEDGE): "})

    # MACD and candle settings
    interval: str = Field(default="1m", json_schema_extra={"prompt": "Enter the candle interval: "})
    macd_fast: int = Field(default=12, json_schema_extra={"prompt": "Enter the MACD fast period: "})
    macd_slow: int = Field(default=26, json_schema_extra={"prompt": "Enter the MACD slow period: "})
    macd_signal: int = Field(default=9, json_schema_extra={"prompt": "Enter the MACD signal period: "})
    volatility_factor: Decimal = Field(default=Decimal("0.01"), json_schema_extra={"prompt": "Enter the volatility factor: "})

    # Triple barrier config
    stop_loss: Decimal = Field(default=Decimal("0.02"), json_schema_extra={"prompt": "Enter the stop loss percentage: "})
    take_profit: Decimal = Field(default=Decimal("0.01"), json_schema_extra={"prompt": "Enter the take profit percentage: "})
    time_limit: int = Field(default=600, json_schema_extra={"prompt": "Enter the time limit in seconds: "})


class CreateMACDMMConfig(ScriptStrategyBase):
    @classmethod
    def init_markets(cls, config: GenConfig):
        cls.markets = {}

    def __init__(self, connectors: Dict[str, ConnectorBase], config: GenConfig):
        super().__init__(connectors)
        self.config = config

    def on_tick(self):
        config_dict = {
            "controller_name": self.config.controller_name,
            "controller_type": self.config.controller_type,
            "connector_name": self.config.connector_name,
            "trading_pair": self.config.trading_pair,
            "total_amount_quote": float(self.config.total_amount_quote),
            "buy_spreads": [float(s) for s in self.config.buy_spreads],
            "sell_spreads": [float(s) for s in self.config.sell_spreads],
            "buy_amounts_pct": [float(a) for a in self.config.buy_amounts_pct],
            "sell_amounts_pct": [float(a) for a in self.config.sell_amounts_pct],
            "executor_refresh_time": self.config.executor_refresh_time,
            "leverage": self.config.leverage,
            "position_mode": self.config.position_mode,
            "interval": self.config.interval,
            "macd_fast": self.config.macd_fast,
            "macd_slow": self.config.macd_slow,
            "macd_signal": self.config.macd_signal,
            "volatility_factor": float(self.config.volatility_factor),
            "stop_loss": float(self.config.stop_loss),
            "take_profit": float(self.config.take_profit),
            "time_limit": self.config.time_limit,
        }

        yaml_string = yaml.dump(config_dict)

        file_path = "conf/controllers/macd_market_making_1.yml"
        with open(file_path, "w") as f:
            f.write(yaml_string)

        self.notify(f"Successfully created configuration file: {file_path}")
        self.stop()
