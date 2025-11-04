import asyncio
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from hummingbot.connector.constants import s_decimal_NaN
from hummingbot.connector.derivative.topone_perpetual import (
    topone_perpetual_constants as CONSTANTS,
    topone_perpetual_web_utils as web_utils,
)
from hummingbot.connector.derivative.topone_perpetual.topone_perpetual_auth import TopOnePerpetualAuth
from hummingbot.connector.derivative.position import Position
from hummingbot.connector.perpetual_derivative_py_base import PerpetualDerivativePyBase
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.core.data_type.common import OrderType, PositionAction, PositionMode, PositionSide, TradeType
from hummingbot.core.data_type.in_flight_order import InFlightOrder, OrderState, OrderUpdate, TradeUpdate
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.data_type.trade_fee import TokenAmount, TradeFeeBase
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.utils.estimate_fee import build_perpetual_trade_fee
from hummingbot.core.web_assistant.connections.data_types import RESTMethod
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory


class ToponePerpetualDerivative(PerpetualDerivativePyBase):
    """
    TopOne Perpetual Derivative connector for Hummingbot
    """
    
    web_utils = web_utils
    SHORT_POLL_INTERVAL = 5.0
    UPDATE_ORDER_STATUS_MIN_INTERVAL = 10.0
    LONG_POLL_INTERVAL = 120.0
    
        def __init__(self,
                     topone_perpetual_api_key: str,
                     topone_perpetual_api_secret: str,
                     trading_pairs: Optional[List[str]] = None,
                     trading_required: bool = True,
                     domain: str = CONSTANTS.DEFAULT_DOMAIN,
                     balance_asset_limit: Optional[Dict[str, Dict[str, Decimal]]] = None,
                     rate_limits_share_pct: Decimal = Decimal("100"),
                     **kwargs):
    
            self.api_key = topone_perpetual_api_key
            self.secret_key = topone_perpetual_api_secret
            self._domain = domain
            self._trading_required = trading_required
            self._trading_pairs = trading_pairs
            self._last_trades_poll_topone_timestamp = 1.0
            self._position_mode = None
            self._leverage = {}
            self._funding_info = {}
            self._balance_asset_limit = balance_asset_limit
    
            super().__init__(balance_asset_limit=balance_asset_limit, rate_limits_share_pct=rate_limits_share_pct, **kwargs)    
    @staticmethod
    def topone_order_type(order_type: OrderType) -> str:
        """Convert Hummingbot order type to TopOne order type"""
        return order_type.name.upper()
    
    @staticmethod
    def to_hb_order_type(topone_type: str) -> OrderType:
        """Convert TopOne order type to Hummingbot order type"""
        return OrderType[topone_type]
    
    @property
    def authenticator(self) -> TopOnePerpetualAuth:
        return TopOnePerpetualAuth(
            api_key=self.api_key,
            secret_key=self.secret_key,
            time_provider=self._time_synchronizer,
        )
    
    @property
    def name(self) -> str:
        return "topone_perpetual"
    
    @property
    def rate_limits_rules(self):
        return CONSTANTS.RATE_LIMITS
    
    @property
    def domain(self):
        return self._domain
    
    @property
    def client_order_id_max_length(self):
        return CONSTANTS.MAX_ORDER_ID_LEN
    
    @property
    def client_order_id_prefix(self):
        return CONSTANTS.HBOT_ORDER_ID_PREFIX
    
    @property
    def trading_rules_request_path(self):
        return CONSTANTS.FUTURES_CONTRACT_LIST_PATH_URL
    
    @property
    def trading_pairs_request_path(self):
        return CONSTANTS.FUTURES_CONTRACT_LIST_PATH_URL
    
    @property
    def check_network_request_path(self):
        return CONSTANTS.SERVER_TIME_PATH_URL
    
    @property
    def trading_pairs(self):
        return list(self._trading_pairs or [])
    
    @property
    def is_cancel_request_in_exchange_synchronous(self) -> bool:
        return True
    
    @property
    def is_trading_required(self) -> bool:
        return self._trading_required
    
    def supported_order_types(self):
        return [OrderType.LIMIT, OrderType.MARKET]
    
    def supported_position_modes(self):
        return [PositionMode.HEDGE, PositionMode.ONEWAY]
    
    @property
    def funding_info(self) -> Dict[str, Any]:
        return self._funding_info.copy()
    
    @property
    def funding_fee_poll_interval(self) -> int:
        """
        Funding fee poll interval in seconds
        TopOne 沒有提供 funding fee API，設定為較長間隔
        """
        return 3600  # 1 小時
    
    def _is_request_exception_related_to_time_synchronizer(self, request_exception: Exception):
        error_description = str(request_exception)
        is_time_synchronizer_related = ("timestamp" in error_description.lower()
                                      or "recvwindow" in error_description.lower()
                                      or "-1021" in error_description
                                      or "-1022" in error_description)
        return is_time_synchronizer_related
    
    def _is_order_not_found_during_status_update_error(self, status_update_exception: Exception) -> bool:
        error_description = str(status_update_exception)
        return (CONSTANTS.ORDER_NOT_EXIST_ERROR_CODE in error_description or
                CONSTANTS.UNKNOWN_ORDER_ERROR_CODE in error_description or
                "order not found" in error_description.lower())
    
    def _is_order_not_found_during_cancelation_error(self, cancelation_exception: Exception) -> bool:
        error_description = str(cancelation_exception)
        return (CONSTANTS.ORDER_NOT_EXIST_ERROR_CODE in error_description or
                CONSTANTS.UNKNOWN_ORDER_ERROR_CODE in error_description or
                "order not found" in error_description.lower())
    
    def _create_web_assistants_factory(self) -> WebAssistantsFactory:
        return web_utils.build_api_factory(
            throttler=self._throttler,
            time_synchronizer=self._time_synchronizer,
            domain=self._domain,
            api_key=self.api_key,
            secret_key=self.secret_key,
        )
    
    def _create_order_book_data_source(self) -> OrderBookTrackerDataSource:
        # Import here to avoid circular import
        from hummingbot.connector.derivative.topone_perpetual.topone_perpetual_api_order_book_data_source import TopOnePerpetualAPIOrderBookDataSource
        return TopOnePerpetualAPIOrderBookDataSource(
            trading_pairs=self._trading_pairs,
            connector=self,
            domain=self._domain,
            api_factory=self._web_assistants_factory,
        )
    
    def _create_user_stream_data_source(self) -> UserStreamTrackerDataSource:
        # TopOne does not support user stream. Returning None to force polling.
        return None
    
    def _get_fee(self,
                 base_currency: str,
                 quote_currency: str,
                 order_type: OrderType,
                 order_side: TradeType,
                 amount: Decimal,
                 price: Decimal = s_decimal_NaN,
                 is_maker: Optional[bool] = None) -> TradeFeeBase:
        """
        Calculate the fee for a trade
        """
        is_maker = is_maker or (order_type is OrderType.LIMIT_MAKER)
        trading_pair = combine_to_hb_trading_pair(base=base_currency, quote=quote_currency)
        if trading_pair in self._trading_fees:
            fees_data = self._trading_fees[trading_pair]
            fee_value = Decimal(fees_data["maker"]) if is_maker else Decimal(fees_data["taker"])
        else:
            # Use default fee from constants
            fee_value = Decimal("0.0002")  # 0.02% default fee
        fee = build_perpetual_trade_fee(
            self.name,
            is_maker,
            position_action=PositionAction.OPEN,  # Default to OPEN
            base_currency=base_currency,
            quote_currency=quote_currency,
            order_type=order_type,
            order_side=order_side,
            amount=amount,
            price=price,
        )
        return fee
    
    async def _place_order(self,
                          order_id: str,
                          trading_pair: str,
                          amount: Decimal,
                          trade_type: TradeType,
                          order_type: OrderType,
                          price: Decimal,
                          **kwargs) -> Tuple[str, float]:
        """
        Place an order on TopOne exchange
        Based on TopOne API documentation for creating orders
        """
        # For spot trading, use spot API endpoint
        # For futures, we'll use the futures endpoint
        is_futures = kwargs.get("is_futures", False)
        
        # TopOne 只支持合約交易，沒有現貨交易
        # 所有訂單都使用合約 API
        data = {
            "pair": trading_pair.replace("-", ""),  # TopOne uses concatenated pairs like BTCUSDT
            "side": CONSTANTS.SIDE_BUY if trade_type is TradeType.BUY else CONSTANTS.SIDE_SELL,
            "position_side": kwargs.get("position_side", CONSTANTS.POSITION_SIDE_LONG),
            "leverage": kwargs.get("leverage", 1),
            "quantity": str(amount),
            "margin_mode": kwargs.get("margin_mode", 1),  # 1: isolated, 2: cross
            "is_simulate": kwargs.get("is_simulate", False),
        }
        
        # Add price for limit orders
        if order_type is OrderType.LIMIT:
            data["price"] = str(price)
        
        # Optional stop loss and take profit
        if kwargs.get("stop_loss_price"):
            data["stop_loss_price"] = str(kwargs["stop_loss_price"])
        if kwargs.get("take_profit_price"):
            data["take_profit_price"] = str(kwargs["take_profit_price"])
        
        # Optional margin for opening cost
        if kwargs.get("margin"):
            data["margin"] = str(kwargs["margin"])
        
        path_url = CONSTANTS.FUTURES_CREATE_ORDER_PATH_URL
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        response = await self._api_post(
            path_url=path_url,
            data=data,
            is_auth_required=True,
            trading_pair=trading_pair,
        )
        
        # Extract order ID from response
        exchange_order_id = response.get("order_id", str(response))
        
        return str(exchange_order_id), self.current_timestamp
    
    async def _place_cancel(self, order_id: str, tracked_order: InFlightOrder):
        """
        Cancel an order on TopOne exchange
        TopOne 只支持合約交易，使用 POST /fapi/v1/cancel-order
        """
        data = {
            "order_id": tracked_order.exchange_order_id,
        }
        
        cancel_result = await self._api_post(
            path_url=CONSTANTS.FUTURES_CANCEL_ORDER_PATH_URL,
            data=data,
            is_auth_required=True,
        )
        
        return cancel_result
    
    async def _format_trading_rules(self, exchange_info_dict: Dict[str, Any]) -> List[TradingRule]:
        """
        Format trading rules from TopOne exchange info
        Based on TopOne's contract list API response
        """
        trading_rules = []
        
        # Handle both spot and futures trading rules
        contracts = exchange_info_dict.get("data", {}).get("list", [])
        
        for contract_info in contracts:
            try:
                trading_pair = contract_info.get("pair", "")
                if not trading_pair:
                    continue
                
                # Convert to Hummingbot format (e.g., BTCUSDT -> BTC-USDT)
                hb_trading_pair = self._get_hummingbot_trading_pair(trading_pair)
                
                # Extract trading rules from contract info
                min_order_size = Decimal(contract_info.get("min_order_book_quantity", "0"))
                max_order_size = Decimal(contract_info.get("max_order_book_quantity", "999999999"))
                min_price_increment = Decimal("0.1") ** contract_info.get("price_scale", 8)
                min_base_amount_increment = Decimal("0.1") ** contract_info.get("qauntity_scale", 8)
                
                # Check if trading is enabled
                status = contract_info.get("status", 0)
                pair_status = contract_info.get("pair_status", 0)
                is_active = status == 1 or pair_status == 1
                
                if is_active:
                    trading_rule = TradingRule(
                        trading_pair=hb_trading_pair,
                        min_order_size=min_order_size,
                        max_order_size=max_order_size,
                        min_price_increment=min_price_increment,
                        min_base_amount_increment=min_base_amount_increment,
                        min_notional_size=min_order_size,
                    )
                    trading_rules.append(trading_rule)
                    
            except Exception as e:
                self.logger().error(f"Error parsing trading rule for {contract_info}: {e}")
                continue
        
        return trading_rules
    
    async def _update_trading_fees(self):
        """
        Update trading fees from TopOne contract list
        """
        try:
            response = await self._api_get(
                path_url=CONSTANTS.FUTURES_CONTRACT_LIST_PATH_URL,
                is_auth_required=False,
            )
            
            contracts = response.get("data", {}).get("list", [])
            trading_fees = {}
            
            for contract in contracts:
                pair = contract.get("pair", "")
                if pair:
                    hb_pair = self._get_hummingbot_trading_pair(pair)
                    
                    # 從合約信息中提取手續費
                    contract_info = contract.get("contract", {})
                    if contract_info:
                        open_fee = contract_info.get("open_fee", "0.0002")  # 開倉手續費
                        close_fee = contract_info.get("close_fee", "0.0002")  # 平倉手續費
                        
                        # 使用開倉手續費作為 maker/taker 費率
                        trading_fees[hb_pair] = {
                            "maker": open_fee,
                            "taker": open_fee,
                            "close_fee": close_fee
                        }
            
            self._trading_fees = trading_fees
            
        except Exception as e:
            self.logger().error(f"Error updating trading fees: {e}")
            # 使用默認手續費
            pass
    
    async def _user_stream_event_listener(self):
        """
        Listen to user stream events
        """
        async for event_message in self._iter_user_event_queue():
            try:
                event_type = event_message.get("type")
                event_data = event_message.get("data", {})
                
                if event_type == "order_update":
                    self._process_user_stream_order_update(event_data)
                elif event_type == "trade_update":
                    self._process_user_stream_trade_update(event_data)
                elif event_type == "account_update":
                    self._process_user_stream_account_update(event_data)
                    
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger().error(f"Unexpected error in user stream listener: {e}", exc_info=True)
    
    def _process_user_stream_order_update(self, order_data: Dict[str, Any]):
        """Process order update from user stream"""
        # Implementation will be added when user stream is fully implemented
        pass
    
    def _process_user_stream_trade_update(self, trade_data: Dict[str, Any]):
        """Process trade update from user stream"""
        # Implementation will be added when user stream is fully implemented
        pass
    
    def _process_user_stream_account_update(self, account_data: Dict[str, Any]):
        """Process account update from user stream"""
        # Implementation will be added when user stream is fully implemented
        pass
    
    async def _update_order_status(self):
        """
        Update order status from TopOne
        """
        last_tick = int(self._last_poll_timestamp / self.UPDATE_ORDER_STATUS_MIN_INTERVAL)
        current_tick = int(self.current_timestamp / self.UPDATE_ORDER_STATUS_MIN_INTERVAL)

        if current_tick > last_tick and len(self._order_tracker.active_orders) > 0:
            tracked_orders = list(self._order_tracker.active_orders.values())
            
            # Query order status for active orders
            tasks = []
            for tracked_order in tracked_orders:
                order_id = tracked_order.exchange_order_id
                if order_id:
                    tasks.append(self._get_order_status(tracked_order))
            
            if tasks:
                try:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for tracked_order, result in zip(tracked_orders, results):
                        if isinstance(result, Exception):
                            self.logger().network(
                                f"Error fetching status update for order {tracked_order.client_order_id}: {result}",
                                app_warning_msg=f"Failed to fetch status update for order {tracked_order.client_order_id}."
                            )
                        else:
                            self._process_order_status_update(tracked_order, result)
                except Exception as e:
                    self.logger().error(f"Error updating order status: {e}")
    
    async def _get_order_status(self, tracked_order: InFlightOrder) -> Dict[str, Any]:
        """
        Get order status from TopOne API
        使用 GET /fapi/v1/order-page 查詢當前訂單狀態
        """
        params = {
            "order_id": tracked_order.exchange_order_id,
            "start_time": int((self.current_timestamp - 86400) * 1000),  # Last 24 hours
            "end_time": int(self.current_timestamp * 1000),
        }
        
        response = await self._api_get(
            path_url=CONSTANTS.FUTURES_CURRENT_ORDERS_PATH_URL,
            params=params,
            is_auth_required=True,
        )
        
        return response
    
    def _process_order_status_update(self, tracked_order: InFlightOrder, order_data: Dict[str, Any]):
        """
        Process order status update from TopOne API response
        """
        try:
            # Extract order info from response
            orders_list = order_data.get("data", {}).get("list", [])
            
            for order_info in orders_list:
                if order_info.get("order_id") == tracked_order.exchange_order_id:
                    # Map TopOne status to Hummingbot status
                    topone_status = order_info.get("status")
                    new_state = self._map_topone_order_status(topone_status)
                    
                    if new_state != tracked_order.current_state:
                        # Update order state
                        order_update = OrderUpdate(
                            client_order_id=tracked_order.client_order_id,
                            exchange_order_id=tracked_order.exchange_order_id,
                            trading_pair=tracked_order.trading_pair,
                            update_timestamp=self.current_timestamp,
                            new_state=new_state,
                        )
                        self._order_tracker.process_order_update(order_update)
                    
                    # Check for trade updates
                    filled_amount = Decimal(str(order_info.get("quantity", 0)))
                    if filled_amount > tracked_order.executed_amount_base:
                        # Create trade update
                        price = Decimal(str(order_info.get("price", 0)))
                        fee_amount = Decimal(str(order_info.get("fee", 0)))
                        
                        trade_update = TradeUpdate(
                            trade_id=f"{tracked_order.exchange_order_id}_{int(self.current_timestamp)}",
                            client_order_id=tracked_order.client_order_id,
                            exchange_order_id=tracked_order.exchange_order_id,
                            trading_pair=tracked_order.trading_pair,
                            fee=TokenAmount(token=tracked_order.quote_asset, amount=fee_amount),
                            fill_base_amount=filled_amount - tracked_order.executed_amount_base,
                            fill_quote_amount=(filled_amount - tracked_order.executed_amount_base) * price,
                            fill_price=price,
                            fill_timestamp=self.current_timestamp,
                        )
                        self._order_tracker.process_trade_update(trade_update)
                    break
                    
        except Exception as e:
            self.logger().error(f"Error processing order status update: {e}")
    
    def _map_topone_order_status(self, topone_status: Any) -> OrderState:
        """
        Map TopOne order status to Hummingbot OrderState
        Based on TopOne API docs:
        1: 委托中 (OPEN)
        2: 成交 (FILLED)  
        3: 取消 (CANCELED)
        4: 异常 (FAILED)
        """
        status_mapping = {
            1: OrderState.OPEN,
            2: OrderState.FILLED,
            3: OrderState.CANCELED,
            4: OrderState.FAILED,
            "1": OrderState.OPEN,
            "2": OrderState.FILLED,
            "3": OrderState.CANCELED,
            "4": OrderState.FAILED,
        }
        return status_mapping.get(topone_status, OrderState.OPEN)
    
    async def _all_trade_updates_for_order(self, order: InFlightOrder) -> List[TradeUpdate]:
        """
        Get all trade updates for a specific order
        """
        try:
            # 查詢訂單詳情
            params = {
                "order_id": order.exchange_order_id
            }
            
            response = await self._api_get(
                path_url=CONSTANTS.FUTURES_ORDER_DETAIL_PATH_URL,
                params=params,
                is_auth_required=True,
            )
            
            trade_updates = []
            order_info = response.get("data", {})
            
            if order_info:
                # 如果訂單已執行，創建 trade update
                filled_amount = Decimal(str(order_info.get("quantity", 0)))
                if filled_amount > 0:
                    trade_update = TradeUpdate(
                        trade_id=f"{order.exchange_order_id}_{int(self.current_timestamp)}",
                        client_order_id=order.client_order_id,
                        exchange_order_id=order.exchange_order_id,
                        trading_pair=order.trading_pair,
                        fee=TokenAmount(token=order.quote_asset, amount=Decimal(str(order_info.get("fee", 0)))),
                        fill_base_amount=filled_amount,
                        fill_quote_amount=filled_amount * Decimal(str(order_info.get("price", 0))),
                        fill_price=Decimal(str(order_info.get("price", 0))),
                        fill_timestamp=self.current_timestamp,
                    )
                    trade_updates.append(trade_update)
            
            return trade_updates
            
        except Exception as e:
            self.logger().error(f"Error getting trade updates for order {order.client_order_id}: {e}")
            return []
    
    async def _fetch_last_fee_payment(self, trading_pair: str) -> Tuple[int, Decimal, Decimal]:
        """
        Fetch last funding fee payment
        TopOne 沒有提供 funding fee API，返回默認值
        """
        self.logger().warning(f"TopOne 不支持 funding fee API: {trading_pair}")
        return int(self.current_timestamp), Decimal("0"), Decimal("0")
    
    async def _initialize_trading_pair_symbols_from_exchange_info(self, domain: str = None):
        """
        Initialize trading pair symbols from exchange info
        """
        try:
            response = await self._api_get(
                path_url=CONSTANTS.FUTURES_CONTRACT_LIST_PATH_URL,
                is_auth_required=False,
            )
            
            self._exchange_trading_pairs = set()
            contracts = response.get("data", {}).get("list", [])
            
            for contract in contracts:
                if contract.get("status") == 1 and contract.get("pair_status") == 1:
                    exchange_pair = contract.get("pair", "")
                    if exchange_pair:
                        self._exchange_trading_pairs.add(exchange_pair)
            
            self.logger().info(f"Initialized {len(self._exchange_trading_pairs)} trading pairs from TopOne")
            
        except Exception as e:
            self.logger().error(f"Error initializing trading pairs: {e}")
            self._exchange_trading_pairs = set()
    
    async def _request_order_status(self, tracked_order: InFlightOrder) -> OrderUpdate:
        """
        Request order status for a tracked order
        """
        try:
            response = await self._get_order_status(tracked_order)
            
            # 處理響應並創建 OrderUpdate
            orders_list = response.get("data", {}).get("list", [])
            
            for order_info in orders_list:
                if order_info.get("order_id") == tracked_order.exchange_order_id:
                    # 映射訂單狀態
                    topone_status = order_info.get("status")
                    new_state = self._map_topone_order_status(topone_status)
                    
                    return OrderUpdate(
                        client_order_id=tracked_order.client_order_id,
                        exchange_order_id=tracked_order.exchange_order_id,
                        trading_pair=tracked_order.trading_pair,
                        update_timestamp=self.current_timestamp,
                        new_state=new_state,
                    )
            
            # 如果沒有找到訂單，可能已經取消或完成
            return OrderUpdate(
                client_order_id=tracked_order.client_order_id,
                exchange_order_id=tracked_order.exchange_order_id,
                trading_pair=tracked_order.trading_pair,
                update_timestamp=self.current_timestamp,
                new_state=OrderState.CANCELED,
            )
            
        except Exception as e:
            self.logger().error(f"Error requesting order status for {tracked_order.client_order_id}: {e}")
            # 返回原狀態
            return OrderUpdate(
                client_order_id=tracked_order.client_order_id,
                exchange_order_id=tracked_order.exchange_order_id,
                trading_pair=tracked_order.trading_pair,
                update_timestamp=self.current_timestamp,
                new_state=tracked_order.current_state,
            )
    
    def _get_exchange_trading_pair(self, trading_pair: str) -> str:
        """Convert Hummingbot trading pair to TopOne format"""
        return trading_pair.replace("-", "")
    
    def _get_hummingbot_trading_pair(self, exchange_trading_pair: str) -> str:
        """Convert TopOne trading pair to Hummingbot format"""
        # TopOne uses concatenated format like "BTCUSDT"
        # Need to convert to "BTC-USDT" format
        
        # Common quote currencies to help with parsing
        quote_currencies = ["USDT", "USDC", "BTC", "ETH", "BNB", "BUSD"]
        
        for quote in quote_currencies:
            if exchange_trading_pair.endswith(quote):
                base = exchange_trading_pair[:-len(quote)]
                return f"{base}-{quote}"
        
        # If no match found, return as-is (might need manual mapping)
        return exchange_trading_pair
    
    async def exchange_symbol_associated_to_pair(self, trading_pair: str) -> str:
        # Required by the BitMart data source
        return trading_pair.replace("-", "_")

    async def trading_pair_associated_to_exchange_symbol(self, symbol: str) -> str:
        # Required by the BitMart data source
        return symbol.replace("_", "-")
    
    # 添加 perpetual derivative 必需的方法
    async def _update_positions(self):
        """Update positions from TopOne API"""
        try:
            response = await self._api_get(
                path_url=CONSTANTS.FUTURES_POSITION_PATH_URL,
                is_auth_required=True,
            )
            
            positions = response.get("data", {}).get("list", [])
            account_positions = {}
            
            for position_data in positions:
                if position_data.get("status") == 1:  # Open position
                    trading_pair = self._get_hummingbot_trading_pair(position_data.get("pair", ""))
                    position_side = PositionSide.LONG if position_data.get("side") == "long" else PositionSide.SHORT
                    position_key = f"{trading_pair}_{position_side}"
                    
                    position = Position(
                        trading_pair=trading_pair,
                        position_side=position_side,
                        unrealized_pnl=Decimal(str(position_data.get("unrealized_profit_and_loss", 0))),
                        entry_price=Decimal(str(position_data.get("avg_price", 0))),
                        amount=Decimal(str(position_data.get("quantity", 0))),
                        leverage=Decimal(str(position_data.get("leverage", 1))),
                    )
                    account_positions[position_key] = position
            
            self._account_positions = account_positions
            
        except Exception as e:
            self.logger().error(f"Error updating positions: {e}")
    
    def get_buy_collateral_token(self, trading_pair: str) -> str:
        """Get collateral token for buy orders"""
        return trading_pair.split("-")[1]  # Quote asset (e.g., USDT from BTC-USDT)
    
    def get_sell_collateral_token(self, trading_pair: str) -> str:
        """Get collateral token for sell orders"""
        return trading_pair.split("-")[1]  # Quote asset (e.g., USDT from BTC-USDT)
    
    async def _set_trading_pair_leverage(self, trading_pair: str, leverage: int) -> Tuple[bool, str]:
        """Set leverage for a trading pair"""
        try:
            data = {
                "pair": self._get_exchange_trading_pair(trading_pair),
                "leverage": leverage,
                "margin_mode": 1,  # Default to isolated
                "is_simulate": False,
            }
            
            response = await self._api_put(
                path_url=CONSTANTS.FUTURES_ADJUST_LEVERAGE_PATH_URL,
                data=data,
                is_auth_required=True,
            )
            
            self._leverage[trading_pair] = leverage
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    async def _trading_pair_position_mode_set(self, mode: PositionMode, trading_pair: str) -> Tuple[bool, str]:
        """Set position mode for trading pair"""
        # TopOne doesn't seem to have a separate position mode API
        # Default to hedge mode for perpetual contracts
        self._position_mode = mode
        return True, ""
    
    async def _set_position_mode(self, position_mode: PositionMode) -> Tuple[bool, str]:
        """Set position mode"""
        self._position_mode = position_mode
        return True, ""

    async def _api_get(self, path_url: str, params: Dict[str, Any] = None, is_auth_required: bool = False) -> Dict[str, Any]:
        """Execute GET request to TopOne API"""
        rest_assistant = await self._web_assistants_factory.get_rest_assistant()
        # GET requests should use private_rest_url if auth is required
        url = web_utils.private_rest_url(path_url, self._domain) if is_auth_required else web_utils.public_rest_url(path_url, self._domain)
        
        response = await rest_assistant.execute_request(
            url=url,
            throttler_limit_id=path_url,
            method=RESTMethod.GET,
            params=params,
            is_auth_required=is_auth_required,
        )
        
        return response

    async def _api_post(self, path_url: str, data: Dict[str, Any], is_auth_required: bool = False, **kwargs) -> Dict[str, Any]:
        """Execute POST request to TopOne API"""
        rest_assistant = await self._web_assistants_factory.get_rest_assistant()
        
        url = web_utils.private_rest_url(path_url, self._domain)
        
        response = await rest_assistant.execute_request(
            url=url,
            throttler_limit_id=path_url,
            method=RESTMethod.POST,
            data=data,
            is_auth_required=is_auth_required,
            **kwargs,
        )
        
        return response
    
    async def _api_put(self, path_url: str, data: Dict[str, Any], is_auth_required: bool = False) -> Dict[str, Any]:
        """Execute PUT request to TopOne API"""
        rest_assistant = await self._web_assistants_factory.get_rest_assistant()
        
        url = web_utils.private_rest_url(path_url, self._domain)
        
        response = await rest_assistant.execute_request(
            url=url,
            throttler_limit_id=path_url,
            method=RESTMethod.PUT,
            data=data,
            is_auth_required=is_auth_required,
        )
        
        return response
    
    async def _get_position_information(self) -> Dict[str, Any]:
        """Get position information from TopOne API"""
        try:
            response = await self._api_get(
                path_url=CONSTANTS.FUTURES_POSITION_PATH_URL,
                is_auth_required=True,
            )
            return response
        except Exception as e:
            self.logger().error(f"Error getting position information: {e}")
            return {}
    
    async def _update_balances(self):
        """Update account balances"""
        try:
            response = await self._api_get(
                path_url=CONSTANTS.ACCOUNTS_PATH_URL,
                is_auth_required=True,
            )
            
            # Process trading account balances
            trading_balances = response.get("trading", [])
            balances = {}
            
            for balance_data in trading_balances:
                asset = balance_data.get("code", "")
                available = Decimal(str(balance_data.get("available", 0)))
                total = available + Decimal(str(balance_data.get("unavailable", {}).get("freeze", 0)))
                
                if asset:
                    balances[asset] = {
                        "total": total,
                        "available": available,
                        "locked": total - available,
                    }
            
            self._account_balances = balances
            
        except Exception as e:
            self.logger().error(f"Error updating balances: {e}")
    
    async def _update_funding_fees(self):
        """Update funding fees information"""
        # TopOne doesn't seem to have a dedicated funding fee API
        # This would need to be implemented if the API becomes available
        pass