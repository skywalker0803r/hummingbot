from decimal import Decimal
from typing import Any, Dict

from pydantic import ConfigDict, Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

CENTRALIZED = True
EXAMPLE_PAIR = "BTC-USDT"

# TopOne 合約交易手續費 (基於 TopOne 合約 API 文檔)
# 實際手續費從合約列表的 open_fee 和 close_fee 中獲取
DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.0002"),  # 0.02% - 一般合約開倉手續費
    taker_percent_fee_decimal=Decimal("0.0002"),  # 0.02% - 一般合約開倉手續費  
    buy_percent_fee_deducted_from_returns=True
)


def is_exchange_information_valid(exchange_info: Dict[str, Any]) -> bool:
    """
    Verifies if a trading pair is enabled to operate with based on TopOne contract information
    :param exchange_info: the exchange information for a trading pair
    :return: True if the trading pair is enabled, False otherwise
    """
    # TopOne 合約狀態檢查
    status = exchange_info.get("status", 0)
    pair_status = exchange_info.get("pair_status", 0)
    
    # 根據 TopOne 合約列表 API：status=1 表示正常，pair_status=1 表示可交易
    return status == 1 and pair_status == 1


class TopOnePerpetualConfigMap(BaseConnectorConfigMap):
    connector: str = "topone_perpetual"
    topone_perpetual_api_key: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": lambda cm: "Enter your TopOne Perpetual API key",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    topone_perpetual_api_secret: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": lambda cm: "Enter your TopOne Perpetual API secret",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    
    model_config = ConfigDict(title="topone_perpetual")


KEYS = TopOnePerpetualConfigMap.model_construct()

# 這個變量告訴 Hummingbot 如何實例化連接器類
# 必須與實際的類名完全匹配
CONNECTOR_CLASS_NAME = "ToponePerpetualDerivative"


def convert_from_exchange_trading_pair(exchange_trading_pair: str) -> str:
    """
    Converts TopOne trading pair format to Hummingbot format
    TopOne uses format like "BTCUSDT", Hummingbot uses "BTC-USDT"
    """
    if "-" in exchange_trading_pair:
        return exchange_trading_pair
    
    # Common quote currencies for parsing
    quote_currencies = ["USDT", "USDC", "BTC", "ETH", "BNB", "BUSD"]
    
    for quote in quote_currencies:
        if exchange_trading_pair.endswith(quote):
            base = exchange_trading_pair[:-len(quote)]
            return f"{base}-{quote}"
    
    # If no match found, return as-is
    return exchange_trading_pair


def convert_to_exchange_trading_pair(hb_trading_pair: str) -> str:
    """
    Converts Hummingbot trading pair format to TopOne format
    Hummingbot uses "BTC-USDT", TopOne uses "BTCUSDT"
    """
    return hb_trading_pair.replace("-", "")


def get_new_client_order_id(is_buy: bool, trading_pair: str) -> str:
    """
    Creates a client order ID for TopOne
    """
    from hummingbot.connector.exchange.topone.topone_constants import HBOT_ORDER_ID_PREFIX, MAX_ORDER_ID_LEN
    import time
    
    side = "B" if is_buy else "S"
    # Use timestamp to ensure uniqueness
    timestamp = str(int(time.time() * 1000))[-8:]  # Last 8 digits
    base_id = f"{HBOT_ORDER_ID_PREFIX}{side}{timestamp}"
    
    # Ensure it doesn't exceed max length
    if len(base_id) > MAX_ORDER_ID_LEN:
        base_id = base_id[:MAX_ORDER_ID_LEN]
    
    return base_id


def build_api_factory():
    """
    Factory method to create TopOne Perpetual web assistants factory
    """
    from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
    from hummingbot.connector.derivative.topone_perpetual import topone_perpetual_constants as CONSTANTS
    from hummingbot.connector.derivative.topone_perpetual import topone_perpetual_web_utils as web_utils
    
    throttler = AsyncThrottler(CONSTANTS.RATE_LIMITS)
    api_factory = web_utils.build_api_factory_without_time_synchronizer_pre_processor(
        throttler=throttler
    )
    
    return api_factory