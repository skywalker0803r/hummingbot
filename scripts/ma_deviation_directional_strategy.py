import datetime  
import os  
from collections import deque  
from decimal import Decimal  
from typing import Deque, Dict, List  
  
import pandas as pd  
  
from hummingbot import data_path  
from hummingbot.connector.connector_base import ConnectorBase  
from hummingbot.core.data_type.common import OrderType, PositionAction, PositionMode, PositionSide, TradeType  
from hummingbot.data_feed.candles_feed.candles_factory import CandlesFactory  
from hummingbot.data_feed.candles_feed.data_types import CandlesConfig  
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase  
from hummingbot.strategy_v2.executors.position_executor.data_types import PositionExecutorConfig, TripleBarrierConfig  
from hummingbot.strategy_v2.executors.position_executor.position_executor import PositionExecutor  
  
  
class MADeviationDirectionalStrategy(ScriptStrategyBase):  
    """  
    MA 乖離率方向性交易策略  
    - 價格向下偏離 MA 達到閾值時做多,回到均線平倉  
    - 價格向上偏離 MA 達到閾值時做空,回到均線平倉  
    """  
      
    # 定義交易對和交易所  
    trading_pair = "BTC-USDT"  
    exchange = "bitmart_perpetual"  
      
    # 最大執行器數量  
    max_executors = 1  
    active_executors: List[PositionExecutor] = []  
    stored_executors: Deque[PositionExecutor] = deque(maxlen=10)  
      
    # MA 乖離率策略參數  
    ma_period = 20  # MA 週期  
    deviation_threshold = 0.005  # 乖離率閾值 0.5%  
      
    # TP/SL 參數  
    # TP = 進場點到 MA 的價差  
    # SL = 10 倍 TP  
    time_limit = 60 * 55  
      
    # K 線配置  
    candles = CandlesFactory.get_candle(CandlesConfig(  
        connector="bitmart",  # 使用現貨數據源  
        trading_pair=trading_pair,  
        interval="15m",  
        max_records=1000  
    ))  
      
    # 槓桿和下單金額  
    set_leverage_flag = None  
    leverage = 10  
    order_amount_usd = Decimal("15")  
      
    today = datetime.datetime.today()  
    csv_path = data_path() + f"/{exchange}_{trading_pair}_ma_deviation_{today.day:02d}-{today.month:02d}-{today.year}.csv"  
    markets = {exchange: {trading_pair}}  
      
    def __init__(self, connectors: Dict[str, ConnectorBase]):  
        super().__init__(connectors)  
        self.candles.start()  
      
    def get_active_executors(self):  
        return [executor for executor in self.active_executors if not executor.is_closed]  
      
    def get_closed_executors(self):  
        return self.stored_executors  
      
    def on_tick(self):  
        self.check_and_set_leverage()  
        if len(self.get_active_executors()) < self.max_executors and self.candles.ready:  
            signal_value, take_profit, stop_loss, indicators = self.get_signal_tp_and_sl()  
            if self.is_margin_enough() and signal_value != 0:  
                price = self.connectors[self.exchange].get_mid_price(self.trading_pair)  
                self.notify_hb_app_with_timestamp(f"""  
                Creating new position!  
                Price: {price}  
                MA{self.ma_period}: {indicators[0]}  
                Deviation: {indicators[1]:.4f}  
                Signal: {'LONG' if signal_value > 0 else 'SHORT'}  
                """)  
                signal_executor = PositionExecutor(  
                    config=PositionExecutorConfig(  
                        timestamp=self.current_timestamp,  
                        trading_pair=self.trading_pair,  
                        connector_name=self.exchange,  
                        side=TradeType.BUY if signal_value > 0 else TradeType.SELL,  
                        entry_price=price,  
                        amount=self.order_amount_usd / price,  
                        triple_barrier_config=TripleBarrierConfig(  
                            stop_loss=stop_loss,  
                            take_profit=take_profit,  
                            time_limit=self.time_limit,  
                            open_order_type=OrderType.MARKET,  
                            take_profit_order_type=OrderType.LIMIT,  
                            stop_loss_order_type=OrderType.MARKET  
                        ),  
                        leverage=self.leverage  
                    ),  
                    strategy=self,  
                )  
                self.active_executors.append(signal_executor)  
        self.clean_and_store_executors()  
      
    def get_signal_tp_and_sl(self):  
        """  
        計算 MA 乖離率信號和 TP/SL  
        """  
        candles_df = self.candles.candles_df  
          
        # 計算 MA  
        candles_df['ma'] = candles_df['close'].rolling(window=self.ma_period).mean()  
          
        last_candle = candles_df.iloc[-1]  
        current_price = last_candle['close']  
        ma = last_candle['ma']  
          
        # 計算乖離率  
        deviation = (current_price - ma) / ma  
          
        # 判斷信號  
        if deviation <= -self.deviation_threshold:  
            signal_value = 1  # 做多  
        elif deviation >= self.deviation_threshold:  
            signal_value = -1  # 做空  
        else:  
            signal_value = 0  
          
        # 計算 TP 和 SL  
        # TP = 進場點到 MA 的價差  
        take_profit = abs(deviation)  
        # SL = 10 倍 TP  
        stop_loss = take_profit * 10  
          
        indicators = [ma, deviation]  
        return signal_value, take_profit, stop_loss, indicators  
      
    async def on_stop(self):  
        """停止時清理資源"""  
        self.close_open_positions()  
        self.candles.stop()  
      
    def format_status(self) -> str:  
        """顯示策略狀態"""  
        if not self.ready_to_trade:  
            return "Market connectors are not ready."  
        lines = []  
          
        # 顯示已關閉的執行器  
        if len(self.stored_executors) > 0:  
            lines.extend(["\n########## Closed Executors ##########"])  
        for executor in self.stored_executors:  
            lines.extend([f"|Signal id: {executor.timestamp}"])  
            lines.extend(executor.to_format_status())  
            lines.extend(["-------------------------------------------"])  
          
        # 顯示活躍的執行器  
        if len(self.active_executors) > 0:  
            lines.extend(["\n########## Active Executors ##########"])  
        for executor in self.active_executors:  
            lines.extend([f"|Signal id: {executor.timestamp}"])  
            lines.extend(executor.to_format_status())  
          
        # 顯示市場數據  
        if self.candles.ready:  
            lines.extend(["\n########## Market Data ##########\n"])  
            signal, take_profit, stop_loss, indicators = self.get_signal_tp_and_sl()  
            ma, deviation = indicators  
            lines.extend([f"Signal: {signal} | TP: {take_profit:.4f} | SL: {stop_loss:.4f}"])  
            lines.extend([f"MA{self.ma_period}: {ma:.2f} | Deviation: {deviation:.4f}"])  
            lines.extend(["\n-------------------------------------------\n"])  
        else:  
            lines.extend(["", "  No data collected."])  
          
        return "\n".join(lines)  
      
    def check_and_set_leverage(self):  
        """設置槓桿和倉位模式"""  
        if not self.set_leverage_flag:  
            for connector in self.connectors.values():  
                for trading_pair in connector.trading_pairs:  
                    connector.set_position_mode(PositionMode.HEDGE)  
                    connector.set_leverage(trading_pair=trading_pair, leverage=self.leverage)  
            self.set_leverage_flag = True  
      
    def clean_and_store_executors(self):  
        """清理並存儲已關閉的執行器"""  
        executors_to_store = [executor for executor in self.active_executors if executor.is_closed]  
        if not os.path.exists(self.csv_path):  
            df_header = pd.DataFrame([("timestamp",  
                                       "exchange",  
                                       "trading_pair",  
                                       "side",  
                                       "amount",  
                                       "pnl",  
                                       "close_timestamp",  
                                       "entry_price",  
                                       "close_price",  
                                       "last_status",  
                                       "sl",  
                                       "tp",  
                                       "tl",  
                                       "order_type",  
                                       "leverage")])  
            df_header.to_csv(self.csv_path, mode='a', header=False, index=False)  
        for executor in executors_to_store:  
            self.stored_executors.append(executor)  
            df = pd.DataFrame([(executor.config.timestamp,  
                                executor.config.connector_name,  
                                executor.config.trading_pair,  
                                executor.config.side,  
                                executor.config.amount,  
                                executor.trade_pnl_pct,  
                                executor.close_timestamp,  
                                executor.entry_price,  
                                executor.close_price,  
                                executor.status,  
                                executor.config.triple_barrier_config.stop_loss,  
                                executor.config.triple_barrier_config.take_profit,  
                                executor.config.triple_barrier_config.time_limit,  
                                executor.config.triple_barrier_config.open_order_type,  
                                self.leverage)])  
            df.to_csv(self.csv_path, mode='a', header=False, index=False)  
        self.active_executors = [executor for executor in self.active_executors if not executor.is_closed]  
      
    def close_open_positions(self):  
        """關閉所有開倉"""  
        for connector_name, connector in self.connectors.items():  
            for trading_pair, position in connector.account_positions.items():  
                if position.position_side == PositionSide.LONG:  
                    self.sell(connector_name=connector_name,  
                              trading_pair=position.trading_pair,  
                              amount=abs(position.amount),  
                              order_type=OrderType.MARKET,  
                              price=connector.get_mid_price(position.trading_pair),  
                              position_action=PositionAction.CLOSE)  
                elif position.position_side == PositionSide.SHORT:  
                    self.buy(connector_name=connector_name,  
                             trading_pair=position.trading_pair,  
                             amount=abs(position.amount),  
                             order_type=OrderType.MARKET,  
                             price=connector.get_mid_price(position.trading_pair),  
                             position_action=PositionAction.CLOSE)  
      
    def is_margin_enough(self):  
        """檢查保證金是否足夠"""  
        quote_balance = self.connectors[self.exchange].get_available_balance(self.trading_pair.split("-")[-1])  
        if self.order_amount_usd < quote_balance * self.leverage:  
            return True  
        else:  
            self.logger().info("No enough margin to place orders.")  
            return False