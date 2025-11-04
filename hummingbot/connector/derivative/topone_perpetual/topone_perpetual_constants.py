from hummingbot.core.api_throttler.data_types import LinkedLimitWeightPair, RateLimit

DEFAULT_DOMAIN = "com"

HBOT_ORDER_ID_PREFIX = "x-TOPONE"
MAX_ORDER_ID_LEN = 32

# Base URL
REST_URL = "https://openapi.top.one"
# TopOne 沒有提供 WebSocket API，只有 REST API
WSS_URL = None  # TopOne 不支持 WebSocket

# API versions
PUBLIC_API_VERSION = "v1"
PRIVATE_API_VERSION = "v1"
FUTURES_API_VERSION = "v1"

# Public API endpoints (based on TopOne documentation)
SERVER_TIME_PATH_URL = "/api/v1/server-time"
ASSET_LIST_PATH_URL = "/api/v1/asset"  # 上架資產

# Private API endpoints (錢包 API)
ACCOUNTS_PATH_URL = "/api/v1/balance"  # 資產餘額
DEPOSIT_ADDRESS_PATH_URL = "/api/v1/address"  # 獲取充值地址
TRANSFER_PATH_URL = "/api/v1/asset_transfer"  # 劃轉
TRANSFER_HISTORY_PATH_URL = "/api/v1/transfer_history"  # 劃轉歷史
DEPOSIT_CRYPTO_NETWORK_PATH_URL = "/api/v1/deposit_crypto_network"  # 充提記錄
SMALL_ASSET_WITHDRAWAL_PATH_URL = "/api/v1/small_asset_withdrawal"  # 小額資產提現
ASSET_INTEREST_RECORD_PATH_URL = "/api/v1/asset_interest_record"  # 資產利息記錄

# Note: TopOne 沒有傳統現貨交易 API，主要是錢包管理和合約交易

# Futures API endpoints (合約 API - 基於 TopOne 文檔)
FUTURES_CREATE_ORDER_PATH_URL = "/fapi/v1/create-order"  # 創建訂單
FUTURES_CANCEL_ORDER_PATH_URL = "/fapi/v1/cancel-order"  # 取消訂單
FUTURES_CLOSE_POSITION_PATH_URL = "/fapi/v1/close"  # 平倉
FUTURES_CONTRACT_LIST_PATH_URL = "/fapi/v1/contract-list"  # 合約列表
FUTURES_POSITION_PATH_URL = "/fapi/v1/position"  # 倉位清單
FUTURES_POSITION_HISTORY_PATH_URL = "/fapi/v1/position/history"  # 歷史持倉
FUTURES_CURRENT_ORDERS_PATH_URL = "/fapi/v1/order-page"  # 當前訂單
FUTURES_ORDER_HISTORY_PATH_URL = "/fapi/v1/order-history-page"  # 歷史委託
FUTURES_ORDER_DETAIL_PATH_URL = "/fapi/v1/order-detail"  # 訂單詳情
FUTURES_ADJUST_LEVERAGE_PATH_URL = "/fapi/v1/position/leverage"  # 調整槓桿

# TopOne params
SIDE_BUY = "buy"
SIDE_SELL = "sell"

# Position sides for futures
POSITION_SIDE_LONG = "long"
POSITION_SIDE_SHORT = "short"

# Time in force
TIME_IN_FORCE_GTC = "GTC"  # Good till cancelled
TIME_IN_FORCE_IOC = "IOC"  # Immediate or cancel
TIME_IN_FORCE_FOK = "FOK"  # Fill or kill

# Rate Limit Types
REQUEST_WEIGHT = "REQUEST_WEIGHT"
ORDERS = "ORDERS"

# Rate Limit time intervals
ONE_MINUTE = 60
ONE_SECOND = 1

# TopOne specific rate limits from documentation
# 用户的所有key使用同一个限频：1秒20次
# 下单限频: 2秒20次
GENERAL_RATE_LIMIT = 20
ORDER_RATE_LIMIT = 20
ORDER_RATE_INTERVAL = 2

# Order States mapping from TopOne to Hummingbot
# This will be used in the exchange class where OrderState is properly imported
TOPONE_ORDER_STATUS = {
    1: "OPEN",        # 委托中
    2: "FILLED",      # 成交
    3: "CANCELED",    # 取消
    4: "FAILED",      # 异常
    "1": "OPEN",
    "2": "FILLED",
    "3": "CANCELED",
    "4": "FAILED",
}

# WebSocket event types (to be confirmed)
DIFF_EVENT_TYPE = "depthUpdate"
TRADE_EVENT_TYPE = "trade"
USER_DATA_EVENT_TYPE = "outboundAccountPosition"

# Rate limits based on TopOne API documentation
RATE_LIMITS = [
    # General API rate limit: 20 requests per second
    RateLimit(limit_id=REQUEST_WEIGHT, limit=GENERAL_RATE_LIMIT, time_interval=ONE_SECOND),
    # Order rate limit: 20 orders per 2 seconds
    RateLimit(limit_id=ORDERS, limit=ORDER_RATE_LIMIT, time_interval=ORDER_RATE_INTERVAL),
    
    # Specific endpoint limits (using general limit as base)
    RateLimit(limit_id=SERVER_TIME_PATH_URL, limit=GENERAL_RATE_LIMIT, time_interval=ONE_SECOND,
              linked_limits=[LinkedLimitWeightPair(REQUEST_WEIGHT, 1)]),
    RateLimit(limit_id=ACCOUNTS_PATH_URL, limit=GENERAL_RATE_LIMIT, time_interval=ONE_SECOND,
              linked_limits=[LinkedLimitWeightPair(REQUEST_WEIGHT, 1)]),
    RateLimit(limit_id=FUTURES_CREATE_ORDER_PATH_URL, limit=ORDER_RATE_LIMIT, time_interval=ORDER_RATE_INTERVAL,
              linked_limits=[LinkedLimitWeightPair(ORDERS, 1)]),
    RateLimit(limit_id=FUTURES_CANCEL_ORDER_PATH_URL, limit=ORDER_RATE_LIMIT, time_interval=ORDER_RATE_INTERVAL,
              linked_limits=[LinkedLimitWeightPair(ORDERS, 1)]),
    RateLimit(limit_id=FUTURES_CONTRACT_LIST_PATH_URL, limit=GENERAL_RATE_LIMIT, time_interval=ONE_SECOND,
              linked_limits=[LinkedLimitWeightPair(REQUEST_WEIGHT, 1)]),
]

# Error codes from TopOne API documentation
OPENAPI_KEY_NOT_EXIST_ERROR_CODE = 1001
REQUEST_TIMEOUT_ERROR_CODE = 1002
INSUFFICIENT_PERMISSIONS_ERROR_CODE = 1003
IP_ACCESS_RESTRICTED_ERROR_CODE = 1004
SIGNATURE_VALIDATION_FAILED_ERROR_CODE = 1005
ACCOUNT_BANNED_ERROR_CODE = 1006

# Error messages
ERROR_CODE_MESSAGES = {
    OPENAPI_KEY_NOT_EXIST_ERROR_CODE: "openapi key not exist",
    REQUEST_TIMEOUT_ERROR_CODE: "request timeout",
    INSUFFICIENT_PERMISSIONS_ERROR_CODE: "insufficient permissions",
    IP_ACCESS_RESTRICTED_ERROR_CODE: "IP access restricted",
    SIGNATURE_VALIDATION_FAILED_ERROR_CODE: "signature validation failed",
    ACCOUNT_BANNED_ERROR_CODE: "account has been banned",
}

# Order not found errors (for compatibility with base class)
ORDER_NOT_EXIST_ERROR_CODE = "ORDER_NOT_FOUND"
ORDER_NOT_EXIST_MESSAGE = "Order not found"
UNKNOWN_ORDER_ERROR_CODE = "UNKNOWN_ORDER"
UNKNOWN_ORDER_MESSAGE = "Unknown order"