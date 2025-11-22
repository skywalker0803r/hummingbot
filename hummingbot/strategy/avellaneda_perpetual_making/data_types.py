"""
Data types for Avellaneda Perpetual Market Making Strategy

This module defines the data structures and types used by the
Avellaneda-Stoikov perpetual market making strategy.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, NamedTuple

from hummingbot.core.data_type.common import PositionSide


@dataclass
class PriceSize:
    """Represents a price-size pair for order proposals"""
    price: Decimal
    size: Decimal
    is_market_order: bool = False
    
    def __post_init__(self):
        """Ensure decimal types"""
        if not isinstance(self.price, Decimal):
            self.price = Decimal(str(self.price))
        if not isinstance(self.size, Decimal):
            self.size = Decimal(str(self.size))
    
    def __str__(self):
        order_type = "Market" if self.is_market_order else "Limit"
        return f"{order_type}({self.price:.6f} x {self.size:.6f})"


@dataclass
class Proposal:
    """Order proposal containing buy and sell orders"""
    buys: List[PriceSize]
    sells: List[PriceSize]
    
    def __post_init__(self):
        """Ensure list types"""
        if not isinstance(self.buys, list):
            self.buys = list(self.buys) if self.buys else []
        if not isinstance(self.sells, list):
            self.sells = list(self.sells) if self.sells else []
    
    @property
    def total_orders(self) -> int:
        """Total number of orders in proposal"""
        return len(self.buys) + len(self.sells)
    
    def __str__(self):
        return f"Proposal(buys={len(self.buys)}, sells={len(self.sells)})"


class AvellanedaParams(NamedTuple):
    """Parameters for Avellaneda model calculation"""
    risk_factor: Decimal  # γ (gamma)
    volatility: Decimal  # σ (sigma)
    order_book_intensity: Decimal  # α (alpha)
    order_book_depth: Decimal  # κ (kappa)
    time_horizon: Decimal  # T
    inventory_deviation: Decimal  # q


@dataclass
class MarketState:
    """Current market state snapshot"""
    mid_price: Decimal
    bid_price: Decimal
    ask_price: Decimal
    volatility: Decimal
    timestamp: float
    
    @property
    def spread(self) -> Decimal:
        """Current bid-ask spread"""
        return self.ask_price - self.bid_price
    
    @property
    def spread_pct(self) -> Decimal:
        """Current spread as percentage of mid price"""
        if self.mid_price > 0:
            return (self.spread / self.mid_price) * Decimal('100')
        return Decimal('0')


@dataclass
class PositionInfo:
    """Position information for strategy"""
    trading_pair: str
    side: PositionSide
    amount: Decimal
    entry_price: Decimal
    unrealized_pnl: Decimal
    leverage: int
    
    @property
    def is_long(self) -> bool:
        """Check if position is long"""
        return self.amount > 0
    
    @property
    def is_short(self) -> bool:
        """Check if position is short"""
        return self.amount < 0
    
    @property
    def notional_value(self) -> Decimal:
        """Notional value of position"""
        return abs(self.amount) * self.entry_price
    
    def profit_pct(self, current_price: Decimal) -> Decimal:
        """Calculate profit percentage"""
        if self.entry_price == 0:
            return Decimal('0')
        
        if self.is_long:
            return ((current_price - self.entry_price) / self.entry_price) * Decimal('100')
        else:
            return ((self.entry_price - current_price) / self.entry_price) * Decimal('100')


@dataclass 
class OptimalPrices:
    """Calculated optimal prices from Avellaneda model"""
    reservation_price: Decimal
    optimal_bid: Decimal
    optimal_ask: Decimal
    optimal_spread: Decimal
    timestamp: float
    
    @property
    def mid_price(self) -> Decimal:
        """Calculated mid price"""
        return (self.optimal_bid + self.optimal_ask) / Decimal('2')
    
    @property
    def bid_spread_pct(self) -> Decimal:
        """Bid spread as percentage"""
        if self.reservation_price > 0:
            return abs(self.reservation_price - self.optimal_bid) / self.reservation_price * Decimal('100')
        return Decimal('0')
    
    @property
    def ask_spread_pct(self) -> Decimal:
        """Ask spread as percentage"""
        if self.reservation_price > 0:
            return abs(self.optimal_ask - self.reservation_price) / self.reservation_price * Decimal('100')
        return Decimal('0')


@dataclass
class StrategyMetrics:
    """Strategy performance metrics"""
    total_trades: int = 0
    profitable_trades: int = 0
    total_pnl: Decimal = Decimal('0')
    total_volume: Decimal = Decimal('0')
    max_inventory_deviation: Decimal = Decimal('0')
    avg_spread: Decimal = Decimal('0')
    current_gamma: Decimal = Decimal('1')
    uptime_seconds: float = 0
    
    @property
    def win_rate(self) -> Decimal:
        """Win rate percentage"""
        if self.total_trades > 0:
            return Decimal(str(self.profitable_trades)) / Decimal(str(self.total_trades)) * Decimal('100')
        return Decimal('0')
    
    @property
    def avg_pnl_per_trade(self) -> Decimal:
        """Average PnL per trade"""
        if self.total_trades > 0:
            return self.total_pnl / Decimal(str(self.total_trades))
        return Decimal('0')
    
    @property
    def sharpe_ratio_estimate(self) -> Decimal:
        """Rough Sharpe ratio estimate"""
        if self.uptime_seconds > 0:
            # Annualized return estimate
            annual_return = self.total_pnl * Decimal(str(365.25 * 24 * 3600)) / Decimal(str(self.uptime_seconds))
            # Simplified Sharpe (assuming volatility = avg_spread)
            if self.avg_spread > 0:
                return annual_return / self.avg_spread
        return Decimal('0')


class RiskLimits(NamedTuple):
    """Risk management limits"""
    max_position_size: Decimal
    max_leverage: int
    max_loss_pct: Decimal
    max_inventory_deviation: Decimal
    max_spread_pct: Decimal
    min_spread_pct: Decimal


@dataclass
class OrderExecutionResult:
    """Result of order execution"""
    success: bool
    order_id: Optional[str] = None
    error_message: Optional[str] = None
    executed_price: Optional[Decimal] = None
    executed_amount: Optional[Decimal] = None
    timestamp: Optional[float] = None
    
    def __bool__(self):
        return self.success


# Enums for strategy states
class StrategyState:
    """Strategy operational states"""
    INITIALIZING = "INITIALIZING"
    COLLECTING_DATA = "COLLECTING_DATA"
    READY = "READY"
    ACTIVE_MM = "ACTIVE_MM"  # Active market making
    POSITION_MGMT = "POSITION_MGMT"  # Managing positions
    ERROR = "ERROR"
    STOPPED = "STOPPED"


class AdaptiveGammaState:
    """Adaptive gamma learning states"""
    DISABLED = "DISABLED"
    LEARNING = "LEARNING"
    CONVERGED = "CONVERGED"
    ADJUSTING = "ADJUSTING"


# Type aliases for clarity
Price = Decimal
Amount = Decimal
Percentage = Decimal
Timestamp = float
Volatility = Decimal
Gamma = Decimal