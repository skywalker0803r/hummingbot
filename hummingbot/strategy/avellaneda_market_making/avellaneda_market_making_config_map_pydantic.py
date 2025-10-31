from datetime import datetime, time
from decimal import Decimal
from typing import Dict, Optional, Union

from pydantic import ConfigDict, Field, field_validator, model_validator

from hummingbot.client.config.config_data_types import BaseClientModel
from hummingbot.client.config.config_validators import (
    validate_bool,
    validate_datetime_iso_string,
    validate_decimal,
    validate_int,
    validate_time_iso_string,
)
from hummingbot.client.config.strategy_config_data_types import BaseTradingStrategyConfigMap
from hummingbot.client.settings import required_exchanges
from hummingbot.connector.utils import split_hb_trading_pair


class InfiniteModel(BaseClientModel):
    model_config = ConfigDict(title="infinite")


class FromDateToDateModel(BaseClientModel):
    start_datetime: datetime = Field(
        default=...,
        description="The start date and time for date-to-date execution timeframe.",
        json_schema_extra={
            "prompt": "Please enter the start date and time (YYYY-MM-DD HH:MM:SS)", "prompt_on_new": True
        }
    )
    end_datetime: datetime = Field(
        default=...,
        description="The end date and time for date-to-date execution timeframe.",
        json_schema_extra={
            "prompt": "Please enter the end date and time (YYYY-MM-DD HH:MM:SS)", "prompt_on_new": True
        }
    )
    model_config = ConfigDict(title="from_date_to_date")

    @field_validator("start_datetime", "end_datetime", mode="before")
    @classmethod
    def validate_execution_time(cls, v: Union[str, datetime]) -> Optional[str]:
        if not isinstance(v, str):
            v = v.strftime("%Y-%m-%d %H:%M:%S")
        ret = validate_datetime_iso_string(v)
        if ret is not None:
            raise ValueError(ret)
        return v


class DailyBetweenTimesModel(BaseClientModel):
    start_time: time = Field(
        default=...,
        description="The start time for daily-between-times execution timeframe.",
        json_schema_extra={"prompt": "Please enter the start time (HH:MM:SS)", "prompt_on_new": True},
    )
    end_time: time = Field(
        default=...,
        description="The end time for daily-between-times execution timeframe.",
        json_schema_extra={"prompt": "Please enter the end time (HH:MM:SS)", "prompt_on_new": True},
    )
    model_config = ConfigDict(title="daily_between_times")

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def validate_execution_time(cls, v: Union[str, datetime]) -> Optional[str]:
        if not isinstance(v, str):
            v = v.strftime("%H:%M:%S")
        ret = validate_time_iso_string(v)
        if ret is not None:
            raise ValueError(ret)
        return v


EXECUTION_TIMEFRAME_MODELS = {
    InfiniteModel.model_config["title"]: InfiniteModel,
    FromDateToDateModel.model_config["title"]: FromDateToDateModel,
    DailyBetweenTimesModel.model_config["title"]: DailyBetweenTimesModel,
}


class SingleOrderLevelModel(BaseClientModel):
    model_config = ConfigDict(title="single_order_level")


class MultiOrderLevelModel(BaseClientModel):
    order_levels: int = Field(
        default=2,
        description="The number of orders placed on either side of the order book.",
        ge=2,
        json_schema_extra={"prompt": "How many orders do you want to place on both sides?", "prompt_on_new": True},
    )
    level_distances: Decimal = Field(
        default=Decimal("0"),
        description="The spread between order levels, expressed in % of optimal spread.",
        ge=0,
        json_schema_extra={"prompt": "How far apart in % of optimal spread should orders on one side be?", "prompt_on_new": True},
    )
    model_config = ConfigDict(title="multi_order_level")

    @field_validator("order_levels", mode="before")
    @classmethod
    def validate_int_zero_or_above(cls, v: str):
        ret = validate_int(v, min_value=2)
        if ret is not None:
            raise ValueError(ret)
        return v

    @field_validator("level_distances", mode="before")
    @classmethod
    def validate_decimal_zero_or_above(cls, v: str):
        ret = validate_decimal(v, min_value=Decimal("0"), inclusive=True)
        if ret is not None:
            raise ValueError(ret)
        return v


ORDER_LEVEL_MODELS = {
    SingleOrderLevelModel.model_config["title"]: SingleOrderLevelModel,
    MultiOrderLevelModel.model_config["title"]: MultiOrderLevelModel,
}


class TrackHangingOrdersModel(BaseClientModel):
    hanging_orders_cancel_pct: Decimal = Field(
        default=Decimal("10"),
        description="The spread percentage at which hanging orders will be cancelled.",
        gt=0,
        lt=100,
        json_schema_extra={
            "prompt": "At what spread percentage (from mid price) will hanging orders be canceled? (Enter 1 to indicate 1%)",
        }
    )
    model_config = ConfigDict(title="track_hanging_orders")

    @field_validator("hanging_orders_cancel_pct", mode="before")
    @classmethod
    def validate_pct_exclusive(cls, v: str):
        ret = validate_decimal(v, min_value=Decimal("0"), max_value=Decimal("100"), inclusive=False)
        if ret is not None:
            raise ValueError(ret)
        return v


class IgnoreHangingOrdersModel(BaseClientModel):
    model_config = ConfigDict(title="ignore_hanging_orders")


HANGING_ORDER_MODELS = {
    TrackHangingOrdersModel.model_config["title"]: TrackHangingOrdersModel,
    IgnoreHangingOrdersModel.model_config["title"]: IgnoreHangingOrdersModel,
}


class AvellanedaMarketMakingConfigMap(BaseTradingStrategyConfigMap):
    strategy: str = Field(default="avellaneda_market_making")
    execution_timeframe_mode: Union[InfiniteModel, FromDateToDateModel, DailyBetweenTimesModel] = Field(
        default=...,
        description="The execution timeframe.",
        json_schema_extra={
            "prompt": f"Select the execution timeframe ({'/'.join(EXECUTION_TIMEFRAME_MODELS.keys())})",
            "prompt_on_new": True,
        }
    )
    order_amount: Decimal = Field(
        default=...,
        description="The strategy order amount.",
        gt=0,
        json_schema_extra={
            "prompt": lambda mi: AvellanedaMarketMakingConfigMap.order_amount_prompt(mi),
            "prompt_on_new": True,
        }
    )
    order_optimization_enabled: bool = Field(
        default=True,
        description=(
            "Allows the bid and ask order prices to be adjusted based on"
            " the current top bid and ask prices in the market."
        ),
        json_schema_extra={"prompt": "Do you want to enable order optimization? (Yes/No)"}
    )
    risk_factor: Union[Decimal, str] = Field(
        default=Decimal("1"),
        description="The risk factor (\u03B3) or adaptive method ('adaptive', 'simple_adaptive').",
        json_schema_extra={"prompt": "Enter risk factor (\u03B3) or adaptive method ('adaptive', 'simple_adaptive')", "prompt_on_new": True},
    )
    order_amount_shape_factor: Decimal = Field(
        default=Decimal("0"),
        description="The amount shape factor (\u03b7)",
        ge=0,
        le=1,
        json_schema_extra={"prompt": "Enter order amount shape factor (\u03B7)"},
    )
    min_spread: Decimal = Field(
        default=Decimal("0"),
        description="The minimum spread limit as percentage of the mid price.",
        ge=0,
        json_schema_extra={"prompt": "Enter minimum spread limit (as % of mid price)"},
    )
    order_refresh_time: float = Field(
        default=...,
        description="The frequency at which the orders' spreads will be re-evaluated.",
        gt=0.,
        json_schema_extra={"prompt": "How often do you want to refresh orders (in seconds)?", "prompt_on_new": True},
    )
    max_order_age: float = Field(
        default=1800.,
        description="A given order's maximum lifetime irrespective of spread.",
        gt=0.,
        json_schema_extra={"prompt": "How long do you want to cancel and replace bids and asks with the same price (in seconds)?"}
    )
    order_refresh_tolerance_pct: Decimal = Field(
        default=Decimal("0"),
        description="The range of spreads tolerated on refresh cycles. Orders over that range are cancelled and re-submitted.",
        ge=-10, le=10,
        json_schema_extra={"prompt": "Enter the percent change in price needed to refresh orders at each cycle (Enter 1 to indicate 1%)"},
    )
    filled_order_delay: float = Field(
        default=60.,
        description="The delay before placing a new order after an order fill.",
        gt=0.,
        json_schema_extra={"prompt": "How long do you want to wait before placing the next order if your order gets filled (in seconds)"},
    )
    inventory_target_base_pct: Decimal = Field(
        default=Decimal("50"),
        description="Defines the inventory target for the base asset.",
        ge=0,
        le=100,
        json_schema_extra={"prompt": "Enter the inventory target for the base asset (Enter 50 for 50%)", "prompt_on_new": True},
    )
    add_transaction_costs: bool = Field(
        default=False,
        description="If activated, transaction costs will be added to order prices.",
        json_schema_extra={"prompt": "Do you want to add transaction costs automatically to order prices? (Yes/No)"},
    )
    volatility_buffer_size: int = Field(
        default=200,
        description="The number of ticks that will be stored to calculate volatility.",
        ge=1,
        le=10_000,
        json_schema_extra={"prompt": "Enter amount of ticks that will be stored to estimate order book liquidity"},
    )
    trading_intensity_buffer_size: int = Field(
        default=200,
        description="The number of ticks that will be stored to calculate order book liquidity.",
        ge=1,
        le=10_000,
        json_schema_extra={"prompt": "Enter amount of ticks that will be stored to estimate order book liquidity"},
    )
    order_levels_mode: Union[SingleOrderLevelModel, MultiOrderLevelModel] = Field(
        default=SingleOrderLevelModel.model_construct(),
        description="Allows activating multi-order levels.",
        json_schema_extra={"prompt": f"Select the order levels mode ({'/'.join(list(ORDER_LEVEL_MODELS.keys()))})"},
    )
    order_override: Optional[Dict] = Field(
        default=None,
        description="Allows custom specification of the order levels and their spreads and amounts.",
    )
    hanging_orders_mode: Union[IgnoreHangingOrdersModel, TrackHangingOrdersModel] = Field(
        default=IgnoreHangingOrdersModel(),
        description="When tracking hanging orders, the orders on the side opposite to the filled orders remain active.",
        json_schema_extra={"prompt": f"Select the hanging orders mode ({'/'.join(list(HANGING_ORDER_MODELS.keys()))})"},
    )
    should_wait_order_cancel_confirmation: bool = Field(
        default=True,
        description="If activated, the strategy will await cancellation confirmation from the exchange before placing a new order.",
        json_schema_extra={
            "prompt": "Should the strategy wait to receive a confirmation for orders cancellation before creating a new set of orders? (Yes/No)",
        }
    )
    # Adaptive Gamma Learner Parameters
    adaptive_gamma_learning_rate: Decimal = Field(
        default=Decimal("0.01"),
        description="Learning rate for the adaptive gamma learner.",
        gt=0,
        le=1,
        json_schema_extra={"prompt": "Enter the learning rate for adaptive gamma (0.001 to 1.0)"},
    )
    adaptive_gamma_min: Decimal = Field(
        default=Decimal("0.1"),
        description="Minimum gamma value for the adaptive learner.",
        gt=0,
        json_schema_extra={"prompt": "Enter the minimum gamma value for adaptive learning"},
    )
    adaptive_gamma_max: Decimal = Field(
        default=Decimal("10.0"),
        description="Maximum gamma value for the adaptive learner.",
        gt=0,
        json_schema_extra={"prompt": "Enter the maximum gamma value for adaptive learning"},
    )
    adaptive_gamma_initial: Decimal = Field(
        default=Decimal("1.0"),
        description="Initial gamma value for the adaptive learner.",
        gt=0,
        json_schema_extra={"prompt": "Enter the initial gamma value for adaptive learning"},
    )
    adaptive_gamma_reward_window: int = Field(
        default=100,
        description="The number of ticks used for reward calculation in adaptive gamma learning.",
        ge=10,
        le=1000,
        json_schema_extra={"prompt": "Enter the reward window size for adaptive gamma learning (10-1000)"},
    )
    adaptive_gamma_update_frequency: int = Field(
        default=10,
        description="How often (in ticks) to update the gamma value in adaptive learning.",
        ge=1,
        le=100,
        json_schema_extra={"prompt": "Enter the update frequency for adaptive gamma learning (1-100 ticks)"},
    )
    model_config = ConfigDict(title="avellaneda_market_making")

    # === prompts ===

    @classmethod
    def order_amount_prompt(cls, model_instance: 'AvellanedaMarketMakingConfigMap') -> str:
        trading_pair = model_instance.market
        base_asset, quote_asset = split_hb_trading_pair(trading_pair)
        return f"What is the amount of {base_asset} per order?"

    # === specific validations ===

    @field_validator("execution_timeframe_mode", mode="before")
    @classmethod
    def validate_execution_timeframe(
        cls, v: Union[str, InfiniteModel, FromDateToDateModel, DailyBetweenTimesModel]
    ):
        if isinstance(v, (InfiniteModel, FromDateToDateModel, DailyBetweenTimesModel, Dict)):
            sub_model = v
        elif v not in EXECUTION_TIMEFRAME_MODELS:
            raise ValueError(
                f"Invalid timeframe, please choose value from {list(EXECUTION_TIMEFRAME_MODELS.keys())}"
            )
        else:
            sub_model = EXECUTION_TIMEFRAME_MODELS[v].model_construct()
        return sub_model

    @field_validator("order_refresh_tolerance_pct", mode="before")
    @classmethod
    def validate_order_refresh_tolerance_pct(cls, v: str):
        """Used for client-friendly error output."""
        ret = validate_decimal(v, min_value=Decimal("-10"), max_value=Decimal("10"), inclusive=True)
        if ret is not None:
            raise ValueError(ret)
        return v

    @field_validator("volatility_buffer_size", "trading_intensity_buffer_size", mode="before")
    @classmethod
    def validate_buffer_size(cls, v: str):
        """Used for client-friendly error output."""
        ret = validate_int(v, 1, 10_000)
        if ret is not None:
            raise ValueError(ret)
        return v

    @field_validator("order_levels_mode", mode="before")
    @classmethod
    def validate_order_levels_mode(cls, v: Union[str, SingleOrderLevelModel, MultiOrderLevelModel]):
        if isinstance(v, (SingleOrderLevelModel, MultiOrderLevelModel, Dict)):
            sub_model = v
        elif v not in ORDER_LEVEL_MODELS:
            raise ValueError(
                f"Invalid order levels mode, please choose value from {list(ORDER_LEVEL_MODELS.keys())}."
            )
        else:
            sub_model = ORDER_LEVEL_MODELS[v].model_construct()
        return sub_model

    @field_validator("hanging_orders_mode", mode="before")
    @classmethod
    def validate_hanging_orders_mode(cls, v: Union[str, IgnoreHangingOrdersModel, TrackHangingOrdersModel]):
        if isinstance(v, (TrackHangingOrdersModel, IgnoreHangingOrdersModel, Dict)):
            sub_model = v
        elif v not in HANGING_ORDER_MODELS:
            raise ValueError(
                f"Invalid hanging order mode, please choose value from {list(HANGING_ORDER_MODELS.keys())}."
            )
        else:
            sub_model = HANGING_ORDER_MODELS[v].model_construct()
        return sub_model

    # === generic validations ===

    @field_validator(
        "order_optimization_enabled",
        "add_transaction_costs",
        "should_wait_order_cancel_confirmation",
        mode="before")
    @classmethod
    def validate_bool(cls, v: str):
        """Used for client-friendly error output."""
        if isinstance(v, str):
            ret = validate_bool(v)
            if ret is not None:
                raise ValueError(ret)
        return v

    @field_validator("order_amount_shape_factor", mode="before")
    @classmethod
    def validate_decimal_from_zero_to_one(cls, v: str):
        """Used for client-friendly error output."""
        ret = validate_decimal(v, min_value=Decimal("0"), max_value=Decimal("1"), inclusive=True)
        if ret is not None:
            raise ValueError(ret)
        return v

    @field_validator(
        "order_amount",
        "order_refresh_time",
        "max_order_age",
        "filled_order_delay",
        mode="before")
    @classmethod
    def validate_decimal_above_zero(cls, v: str):
        """Used for client-friendly error output."""
        ret = validate_decimal(v, min_value=Decimal("0"), inclusive=False)
        if ret is not None:
            raise ValueError(ret)
        return v

    @field_validator("risk_factor", mode="before")
    @classmethod
    def validate_risk_factor(cls, v):
        """Validate risk factor - can be decimal or adaptive method string."""
        if isinstance(v, str):
            valid_methods = ["adaptive", "simple_adaptive"]
            if v.lower() in valid_methods:
                return v.lower()
            else:
                # Try to parse as decimal
                try:
                    decimal_v = Decimal(v)
                    if decimal_v <= 0:
                        raise ValueError("Risk factor must be greater than 0")
                    return decimal_v
                except:
                    raise ValueError(f"Invalid risk factor. Use a positive number or one of: {valid_methods}")
        else:
            # Handle Decimal or numeric input
            if isinstance(v, (int, float)):
                v = Decimal(str(v))
            if v <= 0:
                raise ValueError("Risk factor must be greater than 0")
            return v

    @field_validator("min_spread", mode="before")
    @classmethod
    def validate_decimal_zero_or_above(cls, v: str):
        """Used for client-friendly error output."""
        ret = validate_decimal(v, min_value=Decimal("0"), inclusive=True)
        if ret is not None:
            raise ValueError(ret)
        return v

    @field_validator("inventory_target_base_pct", mode="before")
    @classmethod
    def validate_pct_inclusive(cls, v: str):
        """Used for client-friendly error output."""
        ret = validate_decimal(v, min_value=Decimal("0"), max_value=Decimal("100"), inclusive=True)
        if ret is not None:
            raise ValueError(ret)
        return v

    @field_validator("adaptive_gamma_learning_rate", mode="before")
    @classmethod
    def validate_learning_rate(cls, v: str):
        """Used for client-friendly error output."""
        ret = validate_decimal(v, min_value=Decimal("0"), max_value=Decimal("1"), inclusive=False)
        if ret is not None:
            raise ValueError(ret)
        return v

    @field_validator(
        "adaptive_gamma_min",
        "adaptive_gamma_max", 
        "adaptive_gamma_initial",
        mode="before")
    @classmethod
    def validate_gamma_values(cls, v: str):
        """Used for client-friendly error output."""
        ret = validate_decimal(v, min_value=Decimal("0"), inclusive=False)
        if ret is not None:
            raise ValueError(ret)
        return v

    @field_validator("adaptive_gamma_reward_window", mode="before")
    @classmethod
    def validate_reward_window(cls, v: str):
        """Used for client-friendly error output."""
        ret = validate_int(v, min_value=10, max_value=1000)
        if ret is not None:
            raise ValueError(ret)
        return v

    @field_validator("adaptive_gamma_update_frequency", mode="before")
    @classmethod
    def validate_update_frequency(cls, v: str):
        """Used for client-friendly error output."""
        ret = validate_int(v, min_value=1, max_value=100)
        if ret is not None:
            raise ValueError(ret)
        return v

    # === post-validations ===

    @model_validator(mode="after")
    def post_validations(self):
        required_exchanges.add(self.exchange)
        
        # Validate gamma parameter relationships
        if self.adaptive_gamma_min >= self.adaptive_gamma_max:
            raise ValueError("adaptive_gamma_min must be less than adaptive_gamma_max")
        
        if not (self.adaptive_gamma_min <= self.adaptive_gamma_initial <= self.adaptive_gamma_max):
            raise ValueError("adaptive_gamma_initial must be between adaptive_gamma_min and adaptive_gamma_max")
        
        return self
