import os
from decimal import Decimal
from typing import Dict, Set
from collections import deque

import pandas_ta as ta
from pydantic import Field

from hummingbot.client.config.config_data_types import BaseClientModel
from hummingbot.connector.connector_base import ConnectorBase
from hummingbot.core.data_type.common import OrderType, PositionAction, PositionMode, PositionSide, TradeType
from hummingbot.core.event.events import OrderFilledEvent
from hummingbot.data_feed.candles_feed.candles_factory import CandlesFactory
from hummingbot.data_feed.candles_feed.data_types import CandlesConfig
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase


class MACDPeakTroughConfig(BaseClientModel):
    script_file_name: str = Field(default_factory=lambda: os.path.basename(__file__))
    exchange: str = Field("binance_perpetual", json_schema_extra={
        "prompt": "Enter the exchange name (e.g., binance_perpetual)", "prompt_on_new": True})
    trading_pair: str = Field("BTC-USDT", json_schema_extra={
        "prompt": "Enter the trading pair (e.g., BTC-USDT)", "prompt_on_new": True})
    order_amount: Decimal = Field(Decimal("0.001"), json_schema_extra={
        "prompt": "Enter the order amount in base asset", "prompt_on_new": True})
    leverage: int = Field(20, json_schema_extra={
        "prompt": "Enter the leverage (e.g., 20)", "prompt_on_new": True})
    position_mode: str = Field("ONEWAY", json_schema_extra={
        "prompt": "Enter the position mode (ONEWAY/HEDGE)", "prompt_on_new": False})
    candle_interval: str = Field("5m", json_schema_extra={
        "prompt": "Enter the candle interval (e.g., 1m, 5m, 15m, 1h)", "prompt_on_new": True})
    macd_fast: int = Field(12, json_schema_extra={
        "prompt": "Enter MACD fast period", "prompt_on_new": True})
    macd_slow: int = Field(26, json_schema_extra={
        "prompt": "Enter MACD slow period", "prompt_on_new": True})
    macd_signal: int = Field(9, json_schema_extra={
        "prompt": "Enter MACD signal period", "prompt_on_new": True})
    take_profit_pct: Decimal = Field(Decimal("0.002"), json_schema_extra={
        "prompt": "Enter the take profit percentage (e.g., 0.002 for 0.2%)", "prompt_on_new": True})
    stop_loss_pct: Decimal = Field(Decimal("0.02"), json_schema_extra={
        "prompt": "Enter the stop loss percentage (e.g., 0.02 for 2%)", "prompt_on_new": True})


class MACDPeakTroughStrategy(ScriptStrategyBase):
    """
    Strategy that buys on MACD negative peaks and sells on MACD positive peaks, with take profit and stop loss.
    """

    @classmethod
    def init_markets(cls, config: MACDPeakTroughConfig):
        cls.markets = {config.exchange: {config.trading_pair}}

    def __init__(self, connectors: Dict[str, ConnectorBase], config: MACDPeakTroughConfig):
        super().__init__(connectors)
        self.config = config
        self.candles = CandlesFactory.get_candle(
            CandlesConfig(
                connector=config.exchange,
                trading_pair=config.trading_pair,
                interval=config.candle_interval,
                max_records=200
            )
        )
        self.candles.start()
        self.macd_values = deque(maxlen=3)
        self.leverage_set = False
        self.active_tp_sl_orders = {}

    def check_and_set_leverage(self):
        if not self.leverage_set:
            try:
                connector = self.connectors[self.config.exchange]
                if self.config.position_mode == "ONEWAY":
                    connector.set_position_mode(PositionMode.ONEWAY)
                elif self.config.position_mode == "HEDGE":
                    connector.set_position_mode(PositionMode.HEDGE)
                else:
                    self.logger().warning(f"Position mode {self.config.position_mode} is not supported. Using ONEWAY.")
                    connector.set_position_mode(PositionMode.ONEWAY)
                connector.set_leverage(self.config.trading_pair, self.config.leverage)
                self.leverage_set = True
                self.logger().info(f"Leverage set to {self.config.leverage} and position mode to {self.config.position_mode}.")
            except Exception as e:
                self.logger().error(f"Error setting leverage or position mode: {e}")

    def on_tick(self):
        self.check_and_set_leverage()
        if not self.candles.ready:
            return

        df = self.candles.candles_df
        df.ta.macd(fast=self.config.macd_fast, slow=self.config.macd_slow, signal=self.config.macd_signal, append=True)
        macd_col = f"MACD_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"
        current_macd = df[macd_col].iloc[-1]
        self.macd_values.append(current_macd)

        active_position = self.get_active_position()

        if active_position:
            if active_position.trading_pair not in self.active_tp_sl_orders:
                self.place_tp_sl_orders(active_position)
        else:
            if self.config.trading_pair in self.active_tp_sl_orders:
                self.cancel_tp_sl_orders(self.config.trading_pair)

        if len(self.macd_values) == 3:
            m1, m2, m3 = self.macd_values[0], self.macd_values[1], self.macd_values[2]
            is_positive_peak = m1 < m2 and m2 > m3 and m2 > 0
            is_negative_peak = m1 > m2 and m2 < m3 and m2 < 0

            if active_position:
                if is_positive_peak and active_position.position_side == PositionSide.LONG:
                    self.execute_trade(TradeType.SELL, "Closing long on reversal", abs(active_position.amount), PositionAction.CLOSE)
                    return
                if is_negative_peak and active_position.position_side == PositionSide.SHORT:
                    self.execute_trade(TradeType.BUY, "Closing short on reversal", abs(active_position.amount), PositionAction.CLOSE)
                    return
            else:
                if is_positive_peak:
                    self.execute_trade(TradeType.SELL, "Opening short position", self.config.order_amount, PositionAction.OPEN)
                elif is_negative_peak:
                    self.execute_trade(TradeType.BUY, "Opening long position", self.config.order_amount, PositionAction.OPEN)

    def did_fill_order(self, order_filled_event: OrderFilledEvent):
        """
        An event handler for when an order is filled.
        """
        order_id = order_filled_event.order_id
        trading_pair = f"{order_filled_event.base_asset}-{order_filled_event.quote_asset}"

        if trading_pair in self.active_tp_sl_orders:
            active_orders = self.active_tp_sl_orders[trading_pair]
            if order_id == active_orders["tp"]:
                self.logger().info(f"Take profit order {order_id} filled. Cancelling stop loss order {active_orders['sl']}.")
                try:
                    self.cancel(self.config.exchange, trading_pair, active_orders["sl"])
                except Exception as e:
                    self.logger().error(f"Failed to cancel order {active_orders['sl']}: {e}", exc_info=True)
                del self.active_tp_sl_orders[trading_pair]
            elif order_id == active_orders["sl"]:
                self.logger().info(f"Stop loss order {order_id} filled. Cancelling take profit order {active_orders['tp']}.")
                try:
                    self.cancel(self.config.exchange, trading_pair, active_orders["tp"])
                except Exception as e:
                    self.logger().error(f"Failed to cancel order {active_orders['tp']}: {e}", exc_info=True)
                del self.active_tp_sl_orders[trading_pair]

    def place_tp_sl_orders(self, position):
        if position.trading_pair in self.active_tp_sl_orders:
            return

        price = position.entry_price
        amount = position.amount

        try:
            if position.position_side == PositionSide.LONG:
                tp_price = price * (1 + self.config.take_profit_pct)
                sl_price = price * (1 - self.config.stop_loss_pct)
                self.logger().info(f"Placing TP/SL for LONG. TP: {tp_price}, SL: {sl_price}")
                tp_id = self.sell(self.config.exchange, self.config.trading_pair, abs(amount), OrderType.LIMIT, tp_price, PositionAction.CLOSE)
                sl_id = self.sell(self.config.exchange, self.config.trading_pair, abs(amount), OrderType.MARKET, sl_price, stop_price=sl_price, position_action=PositionAction.CLOSE)
            else:  # SHORT
                tp_price = price * (1 - self.config.take_profit_pct)
                sl_price = price * (1 + self.config.stop_loss_pct)
                self.logger().info(f"Placing TP/SL for SHORT. TP: {tp_price}, SL: {sl_price}")
                tp_id = self.buy(self.config.exchange, self.config.trading_pair, abs(amount), OrderType.LIMIT, tp_price, PositionAction.CLOSE)
                sl_id = self.buy(self.config.exchange, self.config.trading_pair, abs(amount), OrderType.MARKET, sl_price, stop_price=sl_price, position_action=PositionAction.CLOSE)
            
            self.active_tp_sl_orders[position.trading_pair] = {"tp": tp_id, "sl": sl_id}
        except Exception as e:
            self.logger().error(f"Error placing TP/SL orders: {e}")

    def cancel_tp_sl_orders(self, trading_pair: str):
        if trading_pair in self.active_tp_sl_orders:
            order_ids = self.active_tp_sl_orders.pop(trading_pair)
            self.logger().info(f"Cancelling TP/SL orders for {trading_pair}: {order_ids.values()}")
            for order_id in order_ids.values():
                try:
                    self.cancel(self.config.exchange, trading_pair, order_id)
                except Exception as e:
                    self.logger().error(f"Failed to cancel order {order_id}: {e}", exc_info=True)

    def get_active_position(self):
        connector = self.connectors[self.config.exchange]
        positions = connector.account_positions
        for position in positions.values():
            if position.trading_pair == self.config.trading_pair and position.amount != 0:
                return position
        return None

    def execute_trade(self, trade_type: TradeType, reason: str, amount: Decimal, position_action: PositionAction):
        connector = self.connectors[self.config.exchange]
        price = connector.get_mid_price(self.config.trading_pair)
        self.logger().info(f"{reason} - Placing {trade_type.name} order for {amount} {self.config.trading_pair.split('-')[0]} at ~{price}")
        try:
            if trade_type == TradeType.BUY:
                self.buy(self.config.exchange, self.config.trading_pair, amount, OrderType.MARKET, position_action=position_action)
            else:
                self.sell(self.config.exchange, self.config.trading_pair, amount, OrderType.MARKET, position_action=position_action)
        except Exception as e:
            self.logger().error(f"Error executing trade: {e}")

    async def on_stop(self):
        self.logger().info("Strategy stopped. Closing all open positions...")
        self.cancel_tp_sl_orders(self.config.trading_pair)
        await self.close_open_positions()
        self.candles.stop()

    async def close_open_positions(self):
        connector = self.connectors[self.config.exchange]
        for trading_pair, position in connector.account_positions.items():
            if position.amount != 0:
                self.logger().info(f"Closing {position.position_side.name} position for {trading_pair}. Amount: {position.amount}")
                if position.position_side == PositionSide.LONG:
                    await self.sell(self.config.exchange, trading_pair, abs(position.amount), OrderType.MARKET, PositionAction.CLOSE)
                elif position.position_side == PositionSide.SHORT:
                    await self.buy(self.config.exchange, trading_pair, abs(position.amount), OrderType.MARKET, PositionAction.CLOSE)

    def format_status(self) -> str:
        if not self.ready_to_trade:
            return "Market connectors are not ready."
        lines = []
        warning_lines = []
        warning_lines.extend(self.network_warning(self.get_market_trading_pair_tuples()))
        lines.extend(warning_lines)
        lines.append("\n========== MACD Peak Trough Perpetuals Strategy ==========")
        lines.append(f"Exchange: {self.config.exchange} | Trading Pair: {self.config.trading_pair}")
        balance_df = self.get_balance_df()
        lines.extend(["", "  Balances:"] + ["    " + line for line in balance_df.to_string(index=False).split("\n")] )
        try:
            active_orders_df = self.active_orders_df()
            lines.extend(["", "  Active Orders:"] + ["    " + line for line in active_orders_df.to_string(index=False).split("\n")] )
        except ValueError:
            lines.extend(["", "  Active Orders: None"])
        lines.extend(["", "  Position:"])
        active_position = self.get_active_position()
        if active_position:
            lines.append(f"    Side: {active_position.position_side.name}")
            lines.append(f"    Amount: {active_position.amount:.6f} {active_position.trading_pair.split('-')[0]}")
            lines.append(f"    Entry Price: {active_position.entry_price:.6f}")
            lines.append(f"    Unrealized PnL: {active_position.unrealized_pnl:.6f} {active_position.trading_pair.split('-')[1]}")
        else:
            lines.append("    None")
        lines.extend(["", "  MACD Info:"])
        if self.candles.ready:
            df = self.candles.candles_df
            df.ta.macd(fast=self.config.macd_fast, slow=self.config.macd_slow, signal=self.config.macd_signal, append=True)
            macd_col = f"MACD_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"
            current_macd = df[macd_col].iloc[-1]
            lines.append(f"    MACD: {current_macd:.6f}")
        else:
            lines.append("    Waiting for candle data...")
        return "\n".join(lines)