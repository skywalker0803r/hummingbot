import time
from typing import Any, Callable, Dict, Optional

import aiohttp
from pydantic import SecretStr

from hummingbot.connector.derivative.topone_perpetual import topone_perpetual_constants as CONSTANTS
from hummingbot.connector.derivative.topone_perpetual.topone_perpetual_auth import TopOnePerpetualAuth
from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.connector.utils import TimeSynchronizerRESTPreProcessor
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTMethod
from hummingbot.core.web_assistant.rest_pre_processors import RESTPreProcessorBase
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory

# Bitmart API 端點用於獲取市場數據
BITMART_REST_URL = "https://api-cloud.bitmart.com"
BITMART_PUBLIC_ENDPOINTS = {
    "ticker": f"{BITMART_REST_URL}/contract/public/tickers",
    "depth": f"{BITMART_REST_URL}/contract/public/depth", 
    "trades": f"{BITMART_REST_URL}/contract/public/trades",
    "funding": f"{BITMART_REST_URL}/contract/public/funding-rate",
    "kline": f"{BITMART_REST_URL}/contract/public/kline",
}


def public_rest_url(path_url: str, domain: str = CONSTANTS.DEFAULT_DOMAIN) -> str:
    """
    Creates a full URL for public REST API endpoints
    """
    return f"{CONSTANTS.REST_URL}{path_url}"


def private_rest_url(path_url: str, domain: str = CONSTANTS.DEFAULT_DOMAIN) -> str:
    """
    Creates a full URL for private REST API endpoints
    """
    return f"{CONSTANTS.REST_URL}{path_url}"


def build_api_factory(
        throttler: AsyncThrottler,
        time_synchronizer: TimeSynchronizer,
        domain: str = CONSTANTS.DEFAULT_DOMAIN,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        auth: Optional[AuthBase] = None,
) -> WebAssistantsFactory:
    """
    Factory method to create web assistants for TopOne API
    """
    if api_key is not None:
        if auth is None:
            auth = TopOnePerpetualAuth(
                api_key=api_key,
                secret_key=secret_key,
                time_provider=time_synchronizer,
            )
    
    api_factory = WebAssistantsFactory(
        throttler=throttler,
        auth=auth,
        rest_pre_processors=[
            TimeSynchronizerRESTPreProcessor(synchronizer=time_synchronizer),
        ],
    )
    return api_factory


def build_api_factory_without_time_synchronizer_pre_processor(
        throttler: AsyncThrottler,
        domain: str = CONSTANTS.DEFAULT_DOMAIN,
        auth: Optional[AuthBase] = None,
) -> WebAssistantsFactory:
    """
    Factory method to create web assistants without time synchronizer
    """
    api_factory = WebAssistantsFactory(
        throttler=throttler,
        auth=auth,
    )
    return api_factory


def create_throttler() -> AsyncThrottler:
    """
    Creates an async throttler with TopOne rate limits
    """
    return AsyncThrottler(CONSTANTS.RATE_LIMITS)


async def get_current_server_time(
        throttler: AsyncThrottler,
        domain: str = CONSTANTS.DEFAULT_DOMAIN,
) -> float:
    """
    Get the current server time from TopOne API
    """
    api_factory = build_api_factory_without_time_synchronizer_pre_processor(throttler=throttler, domain=domain)
    rest_assistant = await api_factory.get_rest_assistant()
    
    response = await rest_assistant.execute_request(
        url=public_rest_url(CONSTANTS.SERVER_TIME_PATH_URL, domain),
        method=RESTMethod.GET,
        throttler_limit_id=CONSTANTS.SERVER_TIME_PATH_URL,
    )
    
    # TopOne returns server_time in seconds according to docs
    server_time = response["server_time"]
    return float(server_time)


class TopOneRESTPreProcessor(RESTPreProcessorBase):
    """
    Pre-processor for TopOne REST requests
    """
    
    async def pre_process(self, request):
        """
        Pre-process the request before sending
        """
        # Add any TopOne-specific pre-processing here
        if request.headers is None:
            request.headers = {}
        
        # Ensure Content-Type is set for POST requests
        if request.method == RESTMethod.POST and "Content-Type" not in request.headers:
            request.headers["Content-Type"] = "application/json"
        
        return request


def is_exchange_information_valid(exchange_info: Dict[str, Any]) -> bool:
    """
    Verifies if a trading pair is enabled to operate with based on its exchange information
    """
    return exchange_info.get("status") == "TRADING" or exchange_info.get("pair_status") == 1


def convert_snapshot_message_to_order_book_row(message: Dict[str, Any]):
    """
    TopOne 沒有提供訂單簿數據，返回空列表
    """
    return []


def convert_diff_message_to_order_book_row(message: Dict[str, Any]):
    """
    TopOne 沒有提供訂單簿數據，返回空列表
    """
    return []