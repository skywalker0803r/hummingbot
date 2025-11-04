import logging
from typing import Dict, List, Optional

from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.order_book_message import OrderBookMessage
from hummingbot.logger import HummingbotLogger


class TopOnePerpetualOrderBook(OrderBook):
    """
    Order book implementation for TopOne exchange
    """
    
    _logger: Optional[HummingbotLogger] = None
    
    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger
    
    @classmethod
    def snapshot_message_from_exchange(cls,
                                     msg: Dict[str, any],
                                     timestamp: float,
                                     metadata: Optional[Dict] = None) -> OrderBookMessage:
        """
        Create a snapshot message from TopOne exchange data
        """
        if metadata:
            msg.update(metadata)
            
        return OrderBookMessage(
            OrderBookMessage.MessageType.SNAPSHOT,
            {
                "trading_pair": msg["trading_pair"],
                "update_id": msg.get("lastUpdateId", timestamp),
                "bids": msg.get("bids", []),
                "asks": msg.get("asks", []),
            },
            timestamp=timestamp
        )
    
    @classmethod  
    def diff_message_from_exchange(cls,
                                 msg: Dict[str, any], 
                                 timestamp: float,
                                 metadata: Optional[Dict] = None) -> OrderBookMessage:
        """
        Create a diff message from TopOne exchange data
        """
        if metadata:
            msg.update(metadata)
            
        return OrderBookMessage(
            OrderBookMessage.MessageType.DIFF,
            {
                "trading_pair": msg["trading_pair"],
                "update_id": msg.get("u", timestamp),
                "bids": msg.get("b", []),
                "asks": msg.get("a", []),
                "first_update_id": msg.get("U", None),
            },
            timestamp=timestamp
        )
    
    @classmethod
    def trade_message_from_exchange(cls,
                                  msg: Dict[str, any],
                                  timestamp: float,
                                  metadata: Optional[Dict] = None) -> OrderBookMessage:
        """
        Create a trade message from TopOne exchange data
        """
        if metadata:
            msg.update(metadata)
            
        return OrderBookMessage(
            OrderBookMessage.MessageType.TRADE,
            {
                "trading_pair": msg["trading_pair"],
                "trade_type": float(msg.get("m", 0)),  # 1 for buy, 0 for sell
                "amount": float(msg.get("q", 0)),
                "price": float(msg.get("p", 0)),
                "update_id": msg.get("t", timestamp),
            },
            timestamp=timestamp
        )