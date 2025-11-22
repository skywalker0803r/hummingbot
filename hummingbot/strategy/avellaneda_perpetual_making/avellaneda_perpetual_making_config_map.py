"""
Configuration Map for Avellaneda Perpetual Market Making Strategy

This module defines all the configuration parameters needed for the
Avellaneda-Stoikov market making strategy adapted for perpetual futures.
"""

from decimal import Decimal
from typing import Optional

from hummingbot.client.config.config_validators import (
    validate_decimal,
    validate_exchange,
    validate_int,
    validate_market_trading_pair,
    validate_bool,
)
from hummingbot.client.config.config_var import ConfigVar
from hummingbot.client.settings import (
    AllConnectorSettings,
    get_connector_settings,
)


def derivative_connector_validator(value: str) -> Optional[str]:
    """Validate that the connector supports derivative trading"""
    connector_settings = get_connector_settings(value)
    if connector_settings is None:
        return f"Invalid connector: {value}"
    
    # Check if the connector supports derivatives
    all_settings = AllConnectorSettings.get_connector_config_keys(value)
    derivative_connectors = [
        "binance_perpetual", "kucoin_perpetual", "bybit_perpetual", 
        "okx_perpetual", "gate_io_perpetual", "bitget_perpetual",
        "hyperliquid_perpetual", "derive_perpetual", "dydx_v4_perpetual"
    ]
    
    if value not in derivative_connectors:
        return f"Connector {value} does not support perpetual futures trading"
    
    return None


def risk_factor_validator(value: str) -> Optional[str]:
    """Validate risk factor parameter"""
    try:
        if value.lower() in ["adaptive", "simple_adaptive"]:
            return None  # Valid adaptive modes
        
        risk_val = Decimal(value)
        if risk_val <= 0:
            return "Risk factor must be positive"
        if risk_val > 100:
            return "Risk factor seems too high (>100). Consider using a smaller value."
        return None
    except Exception:
        return "Risk factor must be a positive number or 'adaptive'/'simple_adaptive'"


def spread_validator(value: str) -> Optional[str]:
    """Validate spread parameters"""
    try:
        spread_val = Decimal(value)
        if spread_val < 0:
            return "Spread must be non-negative"
        if spread_val > 100:
            return "Spread percentage seems too high (>100%)"
        return None
    except Exception:
        return "Spread must be a valid decimal number"


def leverage_validator(value: str) -> Optional[str]:
    """Validate leverage parameter"""
    try:
        lev_val = int(value)
        if lev_val < 1:
            return "Leverage must be at least 1"
        if lev_val > 125:
            return "Leverage too high (>125x). Consider using lower leverage for safety."
        return None
    except Exception:
        return "Leverage must be a positive integer"


def buffer_size_validator(value: str) -> Optional[str]:
    """Validate buffer size parameters"""
    try:
        size_val = int(value)
        if size_val < 10:
            return "Buffer size too small. Minimum recommended: 10"
        if size_val > 1000:
            return "Buffer size too large (>1000). Consider using smaller value."
        return None
    except Exception:
        return "Buffer size must be a positive integer"


# Configuration Variables
avellaneda_perpetual_making_config_map = {
    "strategy": ConfigVar(
        key="strategy",
        prompt="",
        default="avellaneda_perpetual_making"
    ),
    "derivative": ConfigVar(
        key="derivative",
        prompt="Enter the derivative exchange name >>> ",
        validator=derivative_connector_validator,
    ),
    "market": ConfigVar(
        key="market",
        prompt="Enter the token trading pair you would like to trade on {derivative} >>> ",
        validator=validate_market_trading_pair,
    ),
    "leverage": ConfigVar(
        key="leverage",
        prompt="How much leverage would you like to use? (1-125) >>> ",
        type_str="int",
        validator=leverage_validator,
        default=10,
    ),
    "position_mode": ConfigVar(
        key="position_mode",
        prompt="Which position mode would you like to use? (One-way/Hedge) >>> ",
        validator=lambda v: None if v in ["One-way", "Hedge"] else 
                   "Invalid position mode. Choose 'One-way' or 'Hedge'",
        default="One-way",
    ),
    
    # Avellaneda Model Parameters
    "risk_factor": ConfigVar(
        key="risk_factor",
        prompt="Enter risk factor (γ - gamma) or 'adaptive' for automatic learning >>> ",
        validator=risk_factor_validator,
        default="1.0",
    ),
    "order_amount_shape_factor": ConfigVar(
        key="order_amount_shape_factor",
        prompt="Enter order amount shape factor (η - eta) >>> ",
        type_str="decimal",
        validator=validate_decimal,
        default=Decimal("1.0"),
    ),
    "min_spread": ConfigVar(
        key="min_spread",
        prompt="Enter minimum spread percentage >>> ",
        type_str="decimal",
        validator=spread_validator,
        default=Decimal("0.1"),
    ),
    "order_amount": ConfigVar(
        key="order_amount",
        prompt="Enter the order amount >>> ",
        type_str="decimal",
        validator=validate_decimal,
        default=Decimal("1.0"),
    ),
    "inventory_target_base_pct": ConfigVar(
        key="inventory_target_base_pct",
        prompt="Enter target base asset percentage (0-100%) >>> ",
        type_str="decimal",
        validator=lambda v: None if Decimal("0") <= Decimal(v) <= Decimal("100") 
                           else "Target percentage must be between 0 and 100",
        default=Decimal("50"),
    ),
    
    # Market Data Parameters
    "volatility_buffer_size": ConfigVar(
        key="volatility_buffer_size",
        prompt="Enter volatility buffer size (number of price ticks) >>> ",
        type_str="int",
        validator=buffer_size_validator,
        default=200,
    ),
    "trading_intensity_buffer_size": ConfigVar(
        key="trading_intensity_buffer_size",
        prompt="Enter trading intensity buffer size (number of ticks) >>> ",
        type_str="int",
        validator=buffer_size_validator,
        default=200,
    ),
    
    # Order Management
    "order_refresh_time": ConfigVar(
        key="order_refresh_time",
        prompt="Enter order refresh time in seconds >>> ",
        type_str="float",
        validator=lambda v: None if float(v) > 0 else "Order refresh time must be positive",
        default=30.0,
    ),
    "order_refresh_tolerance_pct": ConfigVar(
        key="order_refresh_tolerance_pct",
        prompt="Enter order refresh tolerance percentage >>> ",
        type_str="decimal",
        validator=validate_decimal,
        default=Decimal("1.0"),
    ),
    "filled_order_delay": ConfigVar(
        key="filled_order_delay",
        prompt="Enter filled order delay in seconds >>> ",
        type_str="float",
        validator=lambda v: None if float(v) >= 0 else "Filled order delay must be non-negative",
        default=15.0,
    ),
    
    # Position Management
    "long_profit_taking_spread": ConfigVar(
        key="long_profit_taking_spread",
        prompt="Enter profit taking spread for long positions (percentage) >>> ",
        type_str="decimal",
        validator=spread_validator,
        default=Decimal("3.0"),
    ),
    "short_profit_taking_spread": ConfigVar(
        key="short_profit_taking_spread",
        prompt="Enter profit taking spread for short positions (percentage) >>> ",
        type_str="decimal",
        validator=spread_validator,
        default=Decimal("3.0"),
    ),
    "stop_loss_spread": ConfigVar(
        key="stop_loss_spread",
        prompt="Enter stop loss spread (percentage) >>> ",
        type_str="decimal",
        validator=spread_validator,
        default=Decimal("10.0"),
    ),
    "time_between_stop_loss_orders": ConfigVar(
        key="time_between_stop_loss_orders",
        prompt="Enter time between stop loss orders in seconds >>> ",
        type_str="float",
        validator=lambda v: None if float(v) > 0 else "Time between stop loss orders must be positive",
        default=60.0,
    ),
    "stop_loss_slippage_buffer": ConfigVar(
        key="stop_loss_slippage_buffer",
        prompt="Enter stop loss slippage buffer (percentage) >>> ",
        type_str="decimal",
        validator=spread_validator,
        default=Decimal("0.5"),
    ),
    
    # Adaptive Gamma Parameters (optional)
    "adaptive_gamma_enabled": ConfigVar(
        key="adaptive_gamma_enabled",
        prompt="Enable adaptive gamma learning? (Yes/No) >>> ",
        type_str="bool",
        validator=validate_bool,
        default=False,
    ),
    "adaptive_gamma_initial": ConfigVar(
        key="adaptive_gamma_initial",
        prompt="Enter initial gamma value for adaptive learning >>> ",
        type_str="decimal",
        validator=validate_decimal,
        default=Decimal("1.0"),
        required_if=lambda: avellaneda_perpetual_making_config_map.get("adaptive_gamma_enabled").value,
    ),
    "adaptive_gamma_learning_rate": ConfigVar(
        key="adaptive_gamma_learning_rate",
        prompt="Enter learning rate for adaptive gamma (0.001-0.1) >>> ",
        type_str="decimal",
        validator=lambda v: None if Decimal("0.001") <= Decimal(v) <= Decimal("0.1") 
                           else "Learning rate must be between 0.001 and 0.1",
        default=Decimal("0.01"),
        required_if=lambda: avellaneda_perpetual_making_config_map.get("adaptive_gamma_enabled").value,
    ),
    "adaptive_gamma_min": ConfigVar(
        key="adaptive_gamma_min",
        prompt="Enter minimum gamma value >>> ",
        type_str="decimal",
        validator=lambda v: None if Decimal(v) > 0 else "Minimum gamma must be positive",
        default=Decimal("0.1"),
        required_if=lambda: avellaneda_perpetual_making_config_map.get("adaptive_gamma_enabled").value,
    ),
    "adaptive_gamma_max": ConfigVar(
        key="adaptive_gamma_max",
        prompt="Enter maximum gamma value >>> ",
        type_str="decimal",
        validator=lambda v: None if Decimal(v) > avellaneda_perpetual_making_config_map.get("adaptive_gamma_min").value 
                           else "Maximum gamma must be greater than minimum gamma",
        default=Decimal("10.0"),
        required_if=lambda: avellaneda_perpetual_making_config_map.get("adaptive_gamma_enabled").value,
    ),
    "adaptive_gamma_reward_window": ConfigVar(
        key="adaptive_gamma_reward_window",
        prompt="Enter reward window size for adaptive learning >>> ",
        type_str="int",
        validator=lambda v: None if int(v) > 0 else "Reward window must be positive",
        default=100,
        required_if=lambda: avellaneda_perpetual_making_config_map.get("adaptive_gamma_enabled").value,
    ),
    "adaptive_gamma_update_frequency": ConfigVar(
        key="adaptive_gamma_update_frequency",
        prompt="Enter update frequency for adaptive gamma >>> ",
        type_str="int",
        validator=lambda v: None if int(v) > 0 else "Update frequency must be positive",
        default=10,
        required_if=lambda: avellaneda_perpetual_making_config_map.get("adaptive_gamma_enabled").value,
    ),
}


def get_config_map():
    """Get the configuration map"""
    return avellaneda_perpetual_making_config_map


# Helper functions for configuration validation
def validate_config():
    """Validate the entire configuration"""
    config = avellaneda_perpetual_making_config_map
    errors = []
    
    # Cross-validation checks
    try:
        if config["adaptive_gamma_enabled"].value:
            min_gamma = config["adaptive_gamma_min"].value
            max_gamma = config["adaptive_gamma_max"].value
            initial_gamma = config["adaptive_gamma_initial"].value
            
            if not (min_gamma <= initial_gamma <= max_gamma):
                errors.append("Initial gamma must be between min and max gamma values")
        
        # Validate spread relationships
        min_spread = config["min_spread"].value
        profit_long = config["long_profit_taking_spread"].value
        profit_short = config["short_profit_taking_spread"].value
        stop_loss = config["stop_loss_spread"].value
        
        if profit_long <= min_spread:
            errors.append("Long profit taking spread should be greater than min spread")
        if profit_short <= min_spread:
            errors.append("Short profit taking spread should be greater than min spread")
        if stop_loss <= max(profit_long, profit_short):
            errors.append("Stop loss spread should be greater than profit taking spreads")
            
    except Exception as e:
        errors.append(f"Configuration validation error: {e}")
    
    return errors


def display_config_summary():
    """Display a summary of the current configuration"""
    config = avellaneda_perpetual_making_config_map
    
    print("\n" + "="*60)
    print("🎯 AVELLANEDA PERPETUAL MAKING STRATEGY CONFIG SUMMARY")
    print("="*60)
    print(f"📊 Exchange: {config['derivative'].value}")
    print(f"💱 Trading Pair: {config['market'].value}")
    print(f"📈 Leverage: {config['leverage'].value}x")
    print(f"🔄 Position Mode: {config['position_mode'].value}")
    print()
    print("🧮 Avellaneda Model Parameters:")
    print(f"   Risk Factor (γ): {config['risk_factor'].value}")
    print(f"   Shape Factor (η): {config['order_amount_shape_factor'].value}")
    print(f"   Min Spread: {config['min_spread'].value}%")
    print(f"   Order Amount: {config['order_amount'].value}")
    print(f"   Target Inventory: {config['inventory_target_base_pct'].value}%")
    print()
    print("📈 Position Management:")
    print(f"   Long Profit Taking: {config['long_profit_taking_spread'].value}%")
    print(f"   Short Profit Taking: {config['short_profit_taking_spread'].value}%")
    print(f"   Stop Loss: {config['stop_loss_spread'].value}%")
    print()
    if config["adaptive_gamma_enabled"].value:
        print("🧠 Adaptive Gamma Learning: ENABLED")
        print(f"   Initial: {config['adaptive_gamma_initial'].value}")
        print(f"   Range: [{config['adaptive_gamma_min'].value}, {config['adaptive_gamma_max'].value}]")
        print(f"   Learning Rate: {config['adaptive_gamma_learning_rate'].value}")
    else:
        print("🧠 Adaptive Gamma Learning: DISABLED")
    print("="*60)