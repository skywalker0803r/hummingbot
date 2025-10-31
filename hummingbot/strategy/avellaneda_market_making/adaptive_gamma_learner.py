"""
自適應 Gamma 學習器
使用輕量級的在線學習機制動態調整 Avellaneda-Stoikov 策略中的風險因子 (gamma)
"""

import numpy as np
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from collections import deque
import logging


class OnlineGammaLearner:
    """
    在線 Gamma 學習器
    使用簡單的梯度下降方法來動態調整風險因子
    """
    
    def __init__(self, 
                 initial_gamma: float = 1.0,
                 learning_rate: float = 0.1,
                 gamma_min: float = 0.1,
                 gamma_max: float = 10.0,
                 reward_window: int = 100,
                 update_frequency: int = 10):
        """
        初始化學習器
        
        Args:
            initial_gamma: 初始 gamma 值
            learning_rate: 學習率
            gamma_min: gamma 最小值
            gamma_max: gamma 最大值
            reward_window: 獎勵計算窗口大小
            update_frequency: 更新頻率（每N個tick更新一次）
        """
        self.gamma = initial_gamma
        self.learning_rate = learning_rate
        self.gamma_min = gamma_min
        self.gamma_max = gamma_max
        self.reward_window = reward_window
        self.update_frequency = update_frequency
        
        # 狀態和獎勵歷史
        self.reward_history = deque(maxlen=reward_window)
        self.gamma_history = deque(maxlen=reward_window)
        self.state_history = deque(maxlen=reward_window)
        
        # 內部計數器
        self.tick_counter = 0
        self.last_pnl = 0.0
        self.last_inventory_deviation = 0.0
        
        # 梯度估計參數
        self.gradient_epsilon = 0.01  # 有限差分法的 epsilon
        self.baseline_reward = 0.0  # 基線獎勵
        
        self.logger = logging.getLogger(__name__)
        
    def update(self, 
               current_pnl: float,
               inventory_deviation: float,
               volatility: float,
               spread: float,
               market_state: Optional[Dict] = None) -> Decimal:
        """
        更新 gamma 值
        
        Args:
            current_pnl: 當前 PnL
            inventory_deviation: 庫存偏離目標的程度
            volatility: 市場波動率
            spread: 當前價差
            market_state: 其他市場狀態信息
            
        Returns:
            更新後的 gamma 值
        """
        self.tick_counter += 1
        
        # 計算獎勵信號
        reward = self._calculate_reward(current_pnl, inventory_deviation, volatility, spread)
        
        # 記錄狀態
        state = {
            'volatility': volatility,
            'spread': spread,
            'inventory_deviation': inventory_deviation,
            'pnl': current_pnl
        }
        
        self.reward_history.append(reward)
        self.gamma_history.append(self.gamma)
        self.state_history.append(state)
        
        # 定期更新 gamma
        if self.tick_counter % self.update_frequency == 0 and len(self.reward_history) >= 10:
            self._update_gamma()
            
        return Decimal(str(self.gamma))
    
    def _calculate_reward(self, 
                         current_pnl: float,
                         inventory_deviation: float,
                         volatility: float,
                         spread: float) -> float:
        """
        計算獎勵信號
        結合 PnL 增長和庫存控制
        """
        # PnL 變化獎勵
        pnl_change = current_pnl - self.last_pnl
        pnl_reward = pnl_change
        
        # 庫存偏離懲罰
        inventory_penalty = -abs(inventory_deviation) * 0.1
        
        # 波動率適應獎勵（在高波動時鼓勵較高的 gamma）
        volatility_factor = min(volatility * 10, 1.0)  # 標準化波動率
        
        # 價差效率獎勵（鼓勵適當的價差）
        spread_efficiency = -abs(spread - volatility * 2) * 0.05  # 理想價差約為波動率的2倍
        
        total_reward = pnl_reward + inventory_penalty + spread_efficiency
        
        # 更新歷史
        self.last_pnl = current_pnl
        self.last_inventory_deviation = inventory_deviation
        
        return total_reward
    
    def _update_gamma(self):
        """
        使用梯度估計更新 gamma
        """
        if len(self.reward_history) < 20:
            return
            
        # 計算最近的平均獎勵
        recent_rewards = list(self.reward_history)[-10:]
        current_avg_reward = np.mean(recent_rewards)
        
        # 簡單的梯度估計：比較當前獎勵與基線
        if len(self.reward_history) >= self.reward_window:
            # 使用獎勵的移動平均作為基線
            baseline_rewards = list(self.reward_history)[:-10]
            self.baseline_reward = np.mean(baseline_rewards)
            
            # 估計梯度
            reward_improvement = current_avg_reward - self.baseline_reward
            
            # 簡單的策略梯度：如果獎勵提升，朝著當前方向調整
            if abs(reward_improvement) > 1e-6:  # 避免數值問題
                # 計算 gamma 變化的方向
                recent_gammas = list(self.gamma_history)[-10:]
                gamma_trend = np.mean(np.diff(recent_gammas)) if len(recent_gammas) > 1 else 0
                
                # 如果獎勵提升且 gamma 在增加，繼續增加；反之亦然
                if reward_improvement > 0:
                    gradient_direction = np.sign(gamma_trend) if abs(gamma_trend) > 1e-6 else np.random.choice([-1, 1])
                else:
                    gradient_direction = -np.sign(gamma_trend) if abs(gamma_trend) > 1e-6 else np.random.choice([-1, 1])
                
                # 更新 gamma
                gamma_update = self.learning_rate * reward_improvement * gradient_direction
                self.gamma += gamma_update
                
                # 限制範圍
                self.gamma = np.clip(self.gamma, self.gamma_min, self.gamma_max)
                
                self.logger.info(f"Gamma updated: {self.gamma:.6f}, reward_improvement: {reward_improvement:.6f}")
    
    def get_current_gamma(self) -> Decimal:
        """獲取當前 gamma 值"""
        return Decimal(str(self.gamma))
    
    def reset(self):
        """重置學習器狀態"""
        self.reward_history.clear()
        self.gamma_history.clear()
        self.state_history.clear()
        self.tick_counter = 0
        self.last_pnl = 0.0
        self.last_inventory_deviation = 0.0
        self.baseline_reward = 0.0
        
    def get_statistics(self) -> Dict:
        """獲取學習統計信息"""
        if len(self.reward_history) == 0:
            return {}
            
        return {
            'current_gamma': self.gamma,
            'avg_reward': np.mean(list(self.reward_history)),
            'reward_std': np.std(list(self.reward_history)),
            'gamma_range': (min(self.gamma_history), max(self.gamma_history)) if self.gamma_history else (self.gamma, self.gamma),
            'update_count': self.tick_counter // self.update_frequency
        }


class SimpleGammaScheduler:
    """
    簡單的 Gamma 調度器
    根據市場條件使用預定義規則調整 gamma
    """
    
    def __init__(self, base_gamma: float = 1.0):
        self.base_gamma = base_gamma
        
    def get_gamma(self, 
                  volatility: float,
                  inventory_deviation: float,
                  market_trend: Optional[str] = None) -> Decimal:
        """
        根據市場條件調整 gamma
        
        Args:
            volatility: 波動率
            inventory_deviation: 庫存偏離
            market_trend: 市場趨勢 ('bullish', 'bearish', 'neutral')
        """
        gamma = self.base_gamma
        
        # 根據波動率調整
        if volatility > 0.02:  # 高波動
            gamma *= 1.2
        elif volatility < 0.005:  # 低波動
            gamma *= 0.8
            
        # 根據庫存偏離調整
        if abs(inventory_deviation) > 0.3:  # 庫存嚴重偏離
            gamma *= 1.3
        elif abs(inventory_deviation) < 0.1:  # 庫存接近目標
            gamma *= 0.9
            
        # 根據市場趨勢調整
        if market_trend == 'bullish':
            gamma *= 0.9  # 在上漲市場中降低風險厭惡
        elif market_trend == 'bearish':
            gamma *= 1.1  # 在下跌市場中增加風險厭惡
            
        # 限制範圍
        gamma = max(0.1, min(10.0, gamma))
        
        return Decimal(str(gamma))