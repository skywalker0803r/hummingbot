import os  
from decimal import Decimal  
from typing import Dict  
from pydantic import Field  
  
from hummingbot.client.config.config_data_types import BaseClientModel  
from hummingbot.connector.connector_base import ConnectorBase  
from hummingbot.core.data_type.common import OrderType, PositionMode, TradeType  
from hummingbot.data_feed.candles_feed.candles_factory import CandlesFactory  
from hummingbot.data_feed.candles_feed.data_types import CandlesConfig  
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase  
from hummingbot.strategy_v2.executors.position_executor.data_types import (  
    PositionExecutorConfig,  
    TripleBarrierConfig,  
)  
from hummingbot.strategy_v2.executors.position_executor.position_executor import PositionExecutor  
  
  
class MaDeviationConfig(BaseClientModel):  
    """MA 乖離率合約 CTA 策略配置"""  
    script_file_name: str = Field(default_factory=lambda: os.path.basename(__file__))  
      
    # 1. 交易所名稱  
    connector_name: str = Field(  
        "binance_perpetual",  
        json_schema_extra={  
            "prompt": "交易所名稱 (例如 binance_perpetual, bitmart_perpetual)",  
            "prompt_on_new": True  
        }  
    )  
      
    # 2. 交易對  
    trading_pair: str = Field(  
        "BTC-USDT",  
        json_schema_extra={  
            "prompt": "交易對 (例如 BTC-USDT)",  
            "prompt_on_new": True  
        }  
    )  
      
    # 3. K 線週期  
    candles_interval: str = Field(  
        "15m",  
        json_schema_extra={  
            "prompt": "K 線週期 (例如 1m, 5m, 15m, 1h)",  
            "prompt_on_new": True  
        }  
    )  
      
    # 4. MA 週期  
    ma_period: int = Field(  
        20,  
        json_schema_extra={  
            "prompt": "MA 週期 (K 線數量, 例如 20)",  
            "prompt_on_new": True  
        }  
    )  
      
    # 5. 乖離率閾值  
    deviation_threshold: Decimal = Field(  
        Decimal("0.005"),  
        json_schema_extra={  
            "prompt": "乖離率閾值 (例如 0.005 代表 0.5%)",  
            "prompt_on_new": True  
        }  
    )  
      
    # 6. 下單數量  
    order_amount: Decimal = Field(  
        Decimal("0.0001"),  
        json_schema_extra={  
            "prompt": "下單數量 (以基礎資產計, 例如 0.0001 BTC)",  
            "prompt_on_new": True  
        }  
    )  
      
    # 7. 槓桿倍數  
    leverage: int = Field(  
        10,  
        json_schema_extra={  
            "prompt": "槓桿倍數 (例如 10)",  
            "prompt_on_new": True  
        }  
    )  
      
    # 倉位模式  
    position_mode: PositionMode = Field(  
        default=PositionMode.HEDGE,  
        json_schema_extra={  
            "prompt": "倉位模式 (HEDGE/ONEWAY)",  
            "prompt_on_new": True  
        }  
    )  
      
    # 最大同時執行器數量  
    max_executors: int = Field(  
        default=1,  
        json_schema_extra={  
            "prompt": "最大同時倉位數量 (例如 1)",  
            "prompt_on_new": True  
        }  
    )  
  
  
class MaDeviationStrategy(ScriptStrategyBase):  
    """MA 乖離率合約 CTA 策略"""  
      
    @classmethod  
    def init_markets(cls, config: MaDeviationConfig):  
        cls.markets = {config.connector_name: {config.trading_pair}}  
      
    def __init__(self, connectors: Dict[str, ConnectorBase], config: MaDeviationConfig):  
        super().__init__(connectors)  
        self.config = config  
        self.active_executors = []  
          
        # 初始化 K 線數據源  
        self.candles = CandlesFactory.get_candle(CandlesConfig(  
            connector=config.connector_name.replace("_perpetual", ""),  
            trading_pair=config.trading_pair,  
            interval=config.candles_interval,  
            max_records=config.ma_period + 50  
        ))  
        self.candles.start()  
          
        # 設置槓桿和倉位模式  
        self._leverage_set = False  
      
    def on_tick(self):  
        # 設置槓桿 (只執行一次)  
        if not self._leverage_set:  
            connector = self.connectors[self.config.connector_name]  
            connector.set_position_mode(self.config.position_mode)  
            connector.set_leverage(self.config.trading_pair, self.config.leverage)  
            self._leverage_set = True  
          
        # 清理已關閉的執行器  
        self.active_executors = [e for e in self.active_executors if not e.is_closed]  
          
        # 檢查是否可以開新倉  
        if len(self.active_executors) >= self.config.max_executors:  
            return  
          
        # 等待 K 線數據準備好  
        if not self.candles.ready:  
            self.logger().info("等待 K 線數據...")  
            return  
          
        # 獲取 K 線數據  
        df = self.candles.candles_df  
        if len(df) < self.config.ma_period:  
            return  
          
        # 計算 MA 和乖離率  
        ma = df['close'].tail(self.config.ma_period).mean()  
        current_price = df['close'].iloc[-1]  
        deviation = (current_price - ma) / ma  
          
        self.logger().info(  
            f"Price: {current_price:.2f}, MA{self.config.ma_period}: {ma:.2f}, "  
            f"Deviation: {deviation:.4f}"  
        )  
          
        # 判斷交易信號  
        threshold = float(self.config.deviation_threshold)  
        signal = None  
          
        # 做多信號: 價格向下偏離 MA  
        if deviation <= -threshold:  
            signal = TradeType.BUY  
            entry_price = current_price  
            # TP = 進場點到 MA 的價差  
            take_profit = abs(deviation)  
            # SL = 10 倍 TP (反方向)  
            stop_loss = take_profit * 10  
              
        # 做空信號: 價格向上偏離 MA  
        elif deviation >= threshold:  
            signal = TradeType.SELL  
            entry_price = current_price  
            # TP = 進場點到 MA 的價差  
            take_profit = abs(deviation)  
            # SL = 10 倍 TP (反方向)  
            stop_loss = take_profit * 10  
          
        # 創建倉位執行器  
        if signal:  
            self.logger().info(  
                f"開倉信號: {signal.name}, Entry: {entry_price:.2f}, "  
                f"TP: {take_profit:.4f}, SL: {stop_loss:.4f}"  
            )  
              
            executor_config = PositionExecutorConfig(  
                timestamp=self.current_timestamp,  
                connector_name=self.config.connector_name,  
                trading_pair=self.config.trading_pair,  
                side=signal,  
                entry_price=Decimal(str(entry_price)),  
                amount=self.config.order_amount,  
                triple_barrier_config=TripleBarrierConfig(  
                    take_profit=Decimal(str(take_profit)),  
                    stop_loss=Decimal(str(stop_loss)),  
                    open_order_type=OrderType.MARKET,  # 市價進場  
                    take_profit_order_type=OrderType.LIMIT,  # 限價 TP  
                    stop_loss_order_type=OrderType.MARKET,  # 市價 SL  
                ),  
                leverage=self.config.leverage  
            )  
              
            executor = PositionExecutor(  
                strategy=self,  
                config=executor_config  
            )  
            self.active_executors.append(executor)  
      
    async def on_stop(self):  
        """停止時清理資源"""  
        self.candles.stop()  
        # 關閉所有活躍執行器  
        for executor in self.active_executors:  
            if not executor.is_closed:  
                executor.early_stop()