"""
Startup module for Avellaneda Perpetual Market Making Strategy

This module handles the initialization and startup of the Avellaneda-Stoikov
market making strategy for perpetual futures trading.
"""

import os.path
from decimal import Decimal
from typing import List, Tuple

import pandas as pd

from hummingbot import data_path
from hummingbot.client.hummingbot_application import HummingbotApplication
from hummingbot.strategy.avellaneda_perpetual_making.avellaneda_perpetual_making import AvellanedaPerpetualMakingStrategy
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple


async def start(self):
    """
    Start the Avellaneda Perpetual Market Making strategy
    """
    try:
        # Get configuration
        c_map = self.strategy_config_map
        derivative_name = c_map.derivative
        raw_trading_pair = c_map.market
        
        # Parse trading pair
        trading_pair: str = raw_trading_pair
        base, quote = trading_pair.split("-")
        maker_assets: Tuple[str, str] = (base, quote)
        
        # Initialize markets
        market_names: List[Tuple[str, List[str]]] = [(derivative_name, [trading_pair])]
        await self.initialize_markets(market_names)
        
        # Create market trading pair tuple
        maker_data = [self.markets[derivative_name], trading_pair] + list(maker_assets)
        market_info = MarketTradingPairTuple(*maker_data)
        
        # Strategy logging options
        strategy_logging_options = AvellanedaPerpetualMakingStrategy.OPTION_LOG_ALL
        
        # Create debug CSV path for performance tracking
        debug_csv_path = os.path.join(
            data_path(),
            HummingbotApplication.main_application().strategy_file_name.rsplit('.', 1)[0] +
            f"_{pd.Timestamp.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        )
        
        # Initialize strategy
        strategy = AvellanedaPerpetualMakingStrategy()
        
        # Get configuration parameters
        risk_factor = c_map.risk_factor
        if isinstance(risk_factor, str) and risk_factor.lower() in ["adaptive", "simple_adaptive"]:
            adaptive_gamma_enabled = True
            if risk_factor.lower() == "adaptive":
                # Use provided adaptive parameters or defaults
                adaptive_gamma_initial = getattr(c_map, 'adaptive_gamma_initial', 1.0)
                adaptive_gamma_learning_rate = getattr(c_map, 'adaptive_gamma_learning_rate', 0.01)
                adaptive_gamma_min = getattr(c_map, 'adaptive_gamma_min', 0.1)
                adaptive_gamma_max = getattr(c_map, 'adaptive_gamma_max', 10.0)
                adaptive_gamma_reward_window = getattr(c_map, 'adaptive_gamma_reward_window', 100)
                adaptive_gamma_update_frequency = getattr(c_map, 'adaptive_gamma_update_frequency', 10)
            else:  # simple_adaptive
                adaptive_gamma_initial = 1.0
                adaptive_gamma_learning_rate = 0.01
                adaptive_gamma_min = 0.1
                adaptive_gamma_max = 10.0
                adaptive_gamma_reward_window = 50
                adaptive_gamma_update_frequency = 5
            risk_factor_value = adaptive_gamma_initial
        else:
            adaptive_gamma_enabled = getattr(c_map, 'adaptive_gamma_enabled', False)
            adaptive_gamma_initial = getattr(c_map, 'adaptive_gamma_initial', 1.0)
            adaptive_gamma_learning_rate = getattr(c_map, 'adaptive_gamma_learning_rate', 0.01)
            adaptive_gamma_min = getattr(c_map, 'adaptive_gamma_min', 0.1)
            adaptive_gamma_max = getattr(c_map, 'adaptive_gamma_max', 10.0)
            adaptive_gamma_reward_window = getattr(c_map, 'adaptive_gamma_reward_window', 100)
            adaptive_gamma_update_frequency = getattr(c_map, 'adaptive_gamma_update_frequency', 10)
            risk_factor_value = risk_factor if hasattr(risk_factor, 'quantize') else Decimal(str(risk_factor))
        
        # Initialize strategy parameters
        strategy.init_params(
            market_info=market_info,
            risk_factor=risk_factor_value,
            order_amount_shape_factor=c_map.order_amount_shape_factor,
            min_spread=c_map.min_spread,
            order_amount=c_map.order_amount,
            inventory_target_base_pct=c_map.inventory_target_base_pct,
            volatility_buffer_size=c_map.volatility_buffer_size,
            trading_intensity_buffer_size=c_map.trading_intensity_buffer_size,
            order_refresh_time=c_map.order_refresh_time,
            order_refresh_tolerance_pct=c_map.order_refresh_tolerance_pct,
            filled_order_delay=c_map.filled_order_delay,
            leverage=c_map.leverage,
            position_mode=c_map.position_mode,
            long_profit_taking_spread=c_map.long_profit_taking_spread / 100,  # Convert percentage to decimal
            short_profit_taking_spread=c_map.short_profit_taking_spread / 100,
            stop_loss_spread=c_map.stop_loss_spread / 100,
            time_between_stop_loss_orders=c_map.time_between_stop_loss_orders,
            stop_loss_slippage_buffer=c_map.stop_loss_slippage_buffer / 100,
            adaptive_gamma_enabled=adaptive_gamma_enabled,
            adaptive_gamma_initial=adaptive_gamma_initial,
            adaptive_gamma_learning_rate=adaptive_gamma_learning_rate,
            adaptive_gamma_min=adaptive_gamma_min,
            adaptive_gamma_max=adaptive_gamma_max,
            adaptive_gamma_reward_window=adaptive_gamma_reward_window,
            adaptive_gamma_update_frequency=adaptive_gamma_update_frequency,
            logging_options=strategy_logging_options,
            status_report_interval=900,  # 15 minutes
            hb_app_notification=True
        )
        
        # Set strategy
        self.strategy = strategy
        
        # Success message
        self.notify("✅ Avellaneda Perpetual Market Making strategy initialized successfully!")
        self.logger().info("🎯 Strategy Configuration:")
        self.logger().info(f"   📊 Exchange: {derivative_name}")
        self.logger().info(f"   💱 Trading Pair: {trading_pair}")
        self.logger().info(f"   📈 Leverage: {c_map.leverage}x")
        self.logger().info(f"   🔄 Position Mode: {c_map.position_mode}")
        self.logger().info(f"   🎲 Risk Factor: {risk_factor}")
        self.logger().info(f"   💰 Order Amount: {c_map.order_amount}")
        self.logger().info(f"   🎯 Target Inventory: {c_map.inventory_target_base_pct}%")
        
        if adaptive_gamma_enabled:
            self.logger().info("🧠 Adaptive Gamma Learning: ENABLED")
            self.logger().info(f"   📈 Initial Gamma: {adaptive_gamma_initial}")
            self.logger().info(f"   📊 Gamma Range: [{adaptive_gamma_min}, {adaptive_gamma_max}]")
            self.logger().info(f"   🎓 Learning Rate: {adaptive_gamma_learning_rate}")
        else:
            self.logger().info("🧠 Adaptive Gamma Learning: DISABLED")
        
        self.logger().info("📋 Position Management:")
        self.logger().info(f"   💚 Long Profit Taking: {c_map.long_profit_taking_spread}%")
        self.logger().info(f"   💛 Short Profit Taking: {c_map.short_profit_taking_spread}%") 
        self.logger().info(f"   ❌ Stop Loss: {c_map.stop_loss_spread}%")
        
        self.logger().info("🚀 Strategy ready to start trading!")
        
    except Exception as e:
        self.notify(f"❌ Error initializing Avellaneda Perpetual Making strategy: {str(e)}")
        self.logger().error("Unknown error during initialization.", exc_info=True)


def validate_market_trading_pair(market_info):
    """
    Validate the trading pair format for perpetual futures
    """
    try:
        trading_pair = market_info.trading_pair
        base, quote = trading_pair.split("-")
        
        # Basic validation
        if len(base) == 0 or len(quote) == 0:
            return False
            
        # Common quote currencies for perpetual futures
        valid_quotes = ["USDT", "USD", "BUSD", "USDC", "BTC", "ETH"]
        if quote not in valid_quotes:
            print(f"⚠️  Warning: {quote} is not a common quote currency for perpetual futures")
            
        return True
    except ValueError:
        return False


def get_strategy_config_validation_errors(config_map) -> List[str]:
    """
    Validate strategy configuration and return list of errors
    """
    errors = []
    
    try:
        # Validate derivative connector
        derivative = config_map.get("derivative")
        if derivative and derivative.value:
            # Check if connector supports derivatives
            derivative_connectors = [
                "binance_perpetual", "kucoin_perpetual", "bybit_perpetual", 
                "okx_perpetual", "gate_io_perpetual", "bitget_perpetual",
                "hyperliquid_perpetual", "derive_perpetual", "dydx_v4_perpetual"
            ]
            if derivative.value not in derivative_connectors:
                errors.append(f"Connector {derivative.value} does not support perpetual futures")
        
        # Validate trading pair format
        market = config_map.get("market")
        if market and market.value:
            try:
                base, quote = market.value.split("-")
                if not base or not quote:
                    errors.append("Invalid trading pair format. Use BASE-QUOTE format (e.g., BTC-USDT)")
            except ValueError:
                errors.append("Invalid trading pair format. Use BASE-QUOTE format (e.g., BTC-USDT)")
        
        # Validate leverage
        leverage = config_map.get("leverage")
        if leverage and leverage.value:
            if leverage.value < 1 or leverage.value > 125:
                errors.append("Leverage must be between 1 and 125")
        
        # Validate risk factor
        risk_factor = config_map.get("risk_factor")
        if risk_factor and risk_factor.value:
            if isinstance(risk_factor.value, str):
                if risk_factor.value.lower() not in ["adaptive", "simple_adaptive"]:
                    try:
                        float_val = float(risk_factor.value)
                        if float_val <= 0:
                            errors.append("Risk factor must be positive")
                    except ValueError:
                        errors.append("Risk factor must be a positive number or 'adaptive'")
        
        # Validate spread parameters
        spread_params = [
            ("min_spread", "Minimum spread"),
            ("long_profit_taking_spread", "Long profit taking spread"),
            ("short_profit_taking_spread", "Short profit taking spread"),
            ("stop_loss_spread", "Stop loss spread")
        ]
        
        for param_name, param_display in spread_params:
            param = config_map.get(param_name)
            if param and param.value:
                if param.value < 0:
                    errors.append(f"{param_display} must be non-negative")
                elif param.value > 100:
                    errors.append(f"{param_display} seems too high (>{param.value}%)")
        
        # Cross-validation of spreads
        min_spread = config_map.get("min_spread")
        long_profit = config_map.get("long_profit_taking_spread")
        short_profit = config_map.get("short_profit_taking_spread")
        stop_loss = config_map.get("stop_loss_spread")
        
        if all(p and p.value for p in [min_spread, long_profit, short_profit, stop_loss]):
            if long_profit.value <= min_spread.value:
                errors.append("Long profit spread should be greater than minimum spread")
            if short_profit.value <= min_spread.value:
                errors.append("Short profit spread should be greater than minimum spread")
            if stop_loss.value <= max(long_profit.value, short_profit.value):
                errors.append("Stop loss spread should be greater than profit taking spreads")
        
        # Validate adaptive gamma parameters if enabled
        adaptive_enabled = config_map.get("adaptive_gamma_enabled")
        if adaptive_enabled and adaptive_enabled.value:
            gamma_min = config_map.get("adaptive_gamma_min")
            gamma_max = config_map.get("adaptive_gamma_max")
            gamma_initial = config_map.get("adaptive_gamma_initial")
            
            if all(g and g.value for g in [gamma_min, gamma_max, gamma_initial]):
                if gamma_min.value >= gamma_max.value:
                    errors.append("Minimum gamma must be less than maximum gamma")
                if not (gamma_min.value <= gamma_initial.value <= gamma_max.value):
                    errors.append("Initial gamma must be between minimum and maximum gamma")
    
    except Exception as e:
        errors.append(f"Configuration validation error: {str(e)}")
    
    return errors


def format_status() -> str:
    """
    Format strategy status for display
    """
    return """
🎯 Avellaneda Perpetual Market Making Strategy

📚 Theory:
  Based on the Avellaneda-Stoikov optimal market making model
  Adapted for perpetual futures with position management
  
🧮 Mathematical Framework:
  • Reservation Price: r = S - q*γ*σ*√T
  • Optimal Spread: δ = γ*σ*√T + (2/γ)*ln(1 + γ/κ)
  • Dynamic risk adjustment based on inventory deviation
  
🔧 Key Features:
  • Optimal bid/ask placement using volatility and liquidity
  • Position-aware pricing with leverage considerations
  • Adaptive gamma learning for risk optimization
  • Integrated profit-taking and stop-loss mechanisms
  
📈 Risk Management:
  • Leverage-aware position sizing
  • Dynamic stop-loss based on market volatility
  • Inventory deviation monitoring
  • Adaptive risk parameter learning
"""