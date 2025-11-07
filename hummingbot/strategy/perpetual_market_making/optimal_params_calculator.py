"""
最優造市參數計算器
基於 GBM 波動率模型計算最優造市策略參數
"""

import requests
import pandas as pd
import numpy as np
from scipy.stats import norm
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import logging
from typing import Dict, Optional, Union
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

# --- 常數定義 ---
DAYS_PER_YEAR = 365.25
SECONDS_PER_DAY = 24 * 3600


class OptimalParamsCalculator:
    """最優造市參數計算器"""

    def __init__(self):
        self._session = None
    
    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def get_gateio_kline_async(self, currency_pair: str, interval: str = "1h", limit: int = 720) -> pd.DataFrame:
        """
        異步從 Gate.io API 取得歷史 K 線資料
        """
        base_url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            "currency_pair": currency_pair.upper(),
            "interval": interval,
            "limit": limit
        }

        try:
            async with self._session.get(base_url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

            # API 回傳格式: [[timestamp, volume_quote, close, high, low, open, volume_base, closed], ...]
            df = pd.DataFrame(data, columns=[
                "timestamp", "volume_quote", "close", "high", "low", "open", "volume_base", "closed"
            ])

            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit="s", utc=True)
            df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)

            # 依時間排序（API 回傳通常是最新在前）
            df = df.sort_values("timestamp").reset_index(drop=True)
            return df[["timestamp", "open", "high", "low", "close"]]
        
        except Exception as e:
            logger.error(f"Failed to fetch market data from Gate.io: {e}")
            raise

    def get_gateio_kline(self, currency_pair: str, interval: str = "1h", limit: int = 720) -> pd.DataFrame:
        """
        同步版本，從 Gate.io API 取得歷史 K 線資料
        """
        base_url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            "currency_pair": currency_pair.upper(),
            "interval": interval,
            "limit": limit
        }

        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # API 回傳格式: [[timestamp, volume_quote, close, high, low, open, volume_base, closed], ...]
            df = pd.DataFrame(data, columns=[
                "timestamp", "volume_quote", "close", "high", "low", "open", "volume_base", "closed"
            ])

            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit="s", utc=True)
            df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)

            # 依時間排序（API 回傳通常是最新在前）
            df = df.sort_values("timestamp").reset_index(drop=True)
            return df[["timestamp", "open", "high", "low", "close"]]
        
        except Exception as e:
            logger.error(f"Failed to fetch market data from Gate.io: {e}")
            raise

    def calculate_optimal_market_making_params(
        self,
        asset: str,
        mid_price: float,
        daily_volatility_pct: float,
        target_order_fill_prob: float = 0.25,
        order_refresh_time_sec: int = 15,
        stop_loss_risk_prob: float = 0.01,
        max_holding_time_days: float = 1.0,
        profit_factor: float = 2.5
    ) -> Dict[str, Union[str, float, Decimal]]:
        """
        根據 GBM 波動率模型，計算最優造市參數
        
        Args:
            asset: 資產名稱
            mid_price: 當前中間價
            daily_volatility_pct: 日化波動率（百分比）
            target_order_fill_prob: 目標訂單成交機率
            order_refresh_time_sec: 訂單刷新時間（秒）
            stop_loss_risk_prob: 止損風險機率
            max_holding_time_days: 最大持倉時間（天）
            profit_factor: 止盈倍數
            
        Returns:
            包含最優參數的字典
        """
        try:
            daily_volatility = daily_volatility_pct / 100.0
            annual_volatility = daily_volatility * np.sqrt(DAYS_PER_YEAR)
            dt_order = order_refresh_time_sec / (DAYS_PER_YEAR * SECONDS_PER_DAY)
            dt_loss = max_holding_time_days / DAYS_PER_YEAR

            # 基礎掛單價差
            p_half_order = target_order_fill_prob / 2.0
            Z_order = norm.ppf(p_half_order)
            base_spread_pct = (annual_volatility * np.sqrt(dt_order) * np.abs(Z_order)) * 100

            # 止盈與止損
            profit_taking_spread_pct = base_spread_pct * profit_factor
            p_half_loss = stop_loss_risk_prob / 2.0
            Z_loss = norm.ppf(p_half_loss)
            stop_loss_spread_pct = (annual_volatility * np.sqrt(dt_loss) * np.abs(Z_loss)) * 100

            return {
                "asset": asset,
                "current_mid_price": mid_price,
                "order_refresh_time_sec": order_refresh_time_sec,
                "bid_spread": Decimal(str(round(base_spread_pct, 4))),
                "ask_spread": Decimal(str(round(base_spread_pct, 4))),
                "long_profit_taking_spread": Decimal(str(round(profit_taking_spread_pct, 4))),
                "short_profit_taking_spread": Decimal(str(round(profit_taking_spread_pct, 4))),
                "stop_loss_spread": Decimal(str(round(stop_loss_spread_pct, 4))),
                "daily_volatility_pct": daily_volatility_pct,
                "Z_score_order": round(np.abs(Z_order), 4),
                "Z_score_stop_loss": round(np.abs(Z_loss), 4)
            }
        except Exception as e:
            logger.error(f"Failed to calculate optimal parameters: {e}")
            raise

    def calculate_from_gateio(
        self, 
        currency_pair: str, 
        interval: str = "1m",
        **kwargs
    ) -> Dict[str, Union[str, float, Decimal]]:
        """
        從 Gate.io 取得歷史資料，自動估算波動率並計算造市策略參數
        
        Args:
            currency_pair: 交易對，例如 "BTC_USDT"
            interval: K線間隔，預設 "1m"
            **kwargs: 其他參數傳遞給 calculate_optimal_market_making_params
            
        Returns:
            包含最優參數的字典
        """
        try:
            # 取得歷史數據
            df = self.get_gateio_kline(currency_pair, interval=interval, limit=720)
            
            if df.empty:
                raise ValueError(f"No market data found for {currency_pair}")

            # 計算對數報酬率
            df["log_return"] = np.log(df["close"] / df["close"].shift(1))
            interval_vol = df["log_return"].std()

            # 換算成日化波動率
            # 計算每日的時間段數量，然後開根號
            intervals_per_day = {
                "1m": 24 * 60,      # 1440 minutes per day
                "5m": 24 * 12,      # 288 five-minute intervals per day
                "15m": 24 * 4,      # 96 fifteen-minute intervals per day
                "30m": 24 * 2,      # 48 thirty-minute intervals per day
                "1h": 24,           # 24 hours per day
                "4h": 6,            # 6 four-hour intervals per day
                "1d": 1             # 1 day per day
            }
            
            multiplier = intervals_per_day.get(interval, 1440)  # 預設按分鐘處理
            daily_vol = interval_vol * np.sqrt(multiplier)

            logger.info(f"📊 {currency_pair} 日化波動率估計值: {daily_vol*100:.2f}%")

            # 設置預設參數
            params = {
                "asset": currency_pair,
                "mid_price": float(df["close"].iloc[-1]),
                "daily_volatility_pct": daily_vol * 100,
                "target_order_fill_prob": 0.25,
                "order_refresh_time_sec": 15,
                "stop_loss_risk_prob": 0.01,
                "max_holding_time_days": 1,
                "profit_factor": 2.5
            }
            
            # 更新用戶提供的參數
            params.update(kwargs)

            result = self.calculate_optimal_market_making_params(**params)

            logger.info("🔬 最優造市參數計算完成")
            for key, value in result.items():
                if "_spread" in key or "time_sec" in key:
                    unit = "%" if "spread" in key else "秒"
                    logger.info(f"{key:<30}: {value} {unit}")
                elif key == "current_mid_price":
                    logger.info(f"{key:<30}: {value} USDT")
                elif key == "asset":
                    logger.info(f"{key:<30}: {value}")

            return result
            
        except Exception as e:
            logger.error(f"Failed to calculate parameters from Gate.io data: {e}")
            raise

    async def calculate_from_gateio_async(
        self, 
        currency_pair: str, 
        interval: str = "1m",
        **kwargs
    ) -> Dict[str, Union[str, float, Decimal]]:
        """
        異步版本：從 Gate.io 取得歷史資料，自動估算波動率並計算造市策略參數
        """
        try:
            # 取得歷史數據
            df = await self.get_gateio_kline_async(currency_pair, interval=interval, limit=720)
            
            if df.empty:
                raise ValueError(f"No market data found for {currency_pair}")

            # 計算對數報酬率
            df["log_return"] = np.log(df["close"] / df["close"].shift(1))
            interval_vol = df["log_return"].std()

            # 換算成日化波動率
            # 計算每日的時間段數量，然後開根號
            intervals_per_day = {
                "1m": 24 * 60,      # 1440 minutes per day
                "5m": 24 * 12,      # 288 five-minute intervals per day
                "15m": 24 * 4,      # 96 fifteen-minute intervals per day
                "30m": 24 * 2,      # 48 thirty-minute intervals per day
                "1h": 24,           # 24 hours per day
                "4h": 6,            # 6 four-hour intervals per day
                "1d": 1             # 1 day per day
            }
            
            multiplier = intervals_per_day.get(interval, 1440)  # 預設按分鐘處理
            daily_vol = interval_vol * np.sqrt(multiplier)

            logger.info(f"📊 {currency_pair} 日化波動率估計值: {daily_vol*100:.2f}%")

            # 設置預設參數
            params = {
                "asset": currency_pair,
                "mid_price": float(df["close"].iloc[-1]),
                "daily_volatility_pct": daily_vol * 100,
                "target_order_fill_prob": 0.25,
                "order_refresh_time_sec": 15,
                "stop_loss_risk_prob": 0.01,
                "max_holding_time_days": 1,
                "profit_factor": 2.5
            }
            
            # 更新用戶提供的參數
            params.update(kwargs)

            result = self.calculate_optimal_market_making_params(**params)

            logger.info("🔬 最優造市參數計算完成")
            return result
            
        except Exception as e:
            logger.error(f"Failed to calculate parameters from Gate.io data: {e}")
            raise


# 便利函數，用於向後兼容
def calculate_optimal_params_for_pair(currency_pair: str, **kwargs) -> Dict[str, Union[str, float, Decimal]]:
    """
    便利函數：為指定交易對計算最優參數
    """
    calculator = OptimalParamsCalculator()
    return calculator.calculate_from_gateio(currency_pair, **kwargs)