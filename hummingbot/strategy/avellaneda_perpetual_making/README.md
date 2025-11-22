# Avellaneda Perpetual Market Making Strategy

## 📖 概述

這是一個基於 Avellaneda-Stoikov 數學模型的合約造市策略，專為永續合約交易而設計。該策略將經典的最優造市理論與現代合約交易的槓桿和倉位管理相結合。

## 🧮 數學原理

### Avellaneda-Stoikov 模型

該策略實現了 Avellaneda-Stoikov 論文 "High-frequency trading in a limit order book" 中的數學框架：

**預訂價格 (Reservation Price):**
```
r = S - q * γ * σ * √T
```

**最優價差 (Optimal Spread):**
```
δ = γ * σ * √T + (2/γ) * ln(1 + γ/κ)
```

**參數說明:**
- `S`: 當前中間價
- `q`: 庫存偏離程度 (相對於目標)
- `γ`: 風險厭惡參數 (gamma)
- `σ`: 市場波動率 (sigma)
- `T`: 時間範圍
- `κ`: 訂單簿深度參數 (kappa)
- `α`: 訂單簿強度參數 (alpha)

## 🚀 核心功能

### 1. 智能訂單放置
- **動態價差計算**: 根據市場波動率和流動性自動調整價差
- **庫存感知定價**: 考慮當前倉位偏離目標的程度
- **風險調整**: 基於風險厭惡參數優化買賣價格

### 2. 自適應風險管理
- **自適應 Gamma 學習**: 基於策略表現自動優化風險參數
- **動態止損**: 根據市場波動率調整止損水平
- **槓桿管理**: 智能管理合約槓桿和倉位大小

### 3. 倉位管理
- **獲利了結**: 自動在盈利時平倉
- **止損保護**: 防止過度虧損
- **倉位平衡**: 維持目標庫存分配

## 📊 配置參數

### 核心 Avellaneda 參數

| 參數 | 說明 | 預設值 | 範圍 |
|------|------|--------|------|
| `risk_factor` | 風險厭惡參數 (γ) | 1.0 | 0.1-10.0 |
| `order_amount_shape_factor` | 訂單形狀因子 (η) | 1.0 | 0.5-2.0 |
| `min_spread` | 最小價差百分比 | 0.1% | 0.01-5% |
| `volatility_buffer_size` | 波動率計算緩衝區 | 200 | 50-1000 |
| `trading_intensity_buffer_size` | 交易強度緩衝區 | 200 | 50-1000 |

### 合約交易參數

| 參數 | 說明 | 預設值 | 範圍 |
|------|------|--------|------|
| `leverage` | 槓桿倍數 | 10 | 1-125 |
| `position_mode` | 倉位模式 | One-way | One-way/Hedge |
| `long_profit_taking_spread` | 多頭獲利了結價差 | 3% | 0.5-20% |
| `short_profit_taking_spread` | 空頭獲利了結價差 | 3% | 0.5-20% |
| `stop_loss_spread` | 止損價差 | 10% | 2-50% |

### 自適應學習參數

| 參數 | 說明 | 預設值 | 範圍 |
|------|------|--------|------|
| `adaptive_gamma_enabled` | 啟用自適應學習 | False | True/False |
| `adaptive_gamma_learning_rate` | 學習率 | 0.01 | 0.001-0.1 |
| `adaptive_gamma_min` | 最小 Gamma 值 | 0.1 | 0.01-1.0 |
| `adaptive_gamma_max` | 最大 Gamma 值 | 10.0 | 2.0-100 |

## 🎯 使用方法

### 1. 基本配置

```yaml
strategy: avellaneda_perpetual_making
derivative: kucoin_perpetual
market: ETH-USDT
leverage: 10
position_mode: One-way
risk_factor: 1.0
order_amount: 0.1
```

### 2. 進階配置 (自適應學習)

```yaml
strategy: avellaneda_perpetual_making
derivative: binance_perpetual
market: BTC-USDT
leverage: 5
position_mode: One-way
risk_factor: adaptive
adaptive_gamma_enabled: true
adaptive_gamma_learning_rate: 0.02
adaptive_gamma_min: 0.5
adaptive_gamma_max: 5.0
```

### 3. 保守配置

```yaml
strategy: avellaneda_perpetual_making
derivative: gate_io_perpetual
market: ETH-USDT
leverage: 3
risk_factor: 2.0  # 較高風險厭惡
min_spread: 0.2
stop_loss_spread: 5
```

## 📈 策略優勢

### 1. 理論基礎扎實
- 基於學術研究的數學模型
- 經過市場驗證的最優化方法
- 考慮市場微觀結構

### 2. 適應性強
- 自動適應市場波動
- 動態調整風險參數
- 實時優化價差設置

### 3. 風險可控
- 多層次風險管理
- 智能止損機制
- 倉位大小控制

## ⚠️ 風險提醒

### 1. 市場風險
- 極端市場條件下可能出現較大虧損
- 流動性不足時價差可能過大
- 單邊市場中可能積累倉位

### 2. 技術風險
- 需要穩定的網路連接
- 對API延遲敏感
- 需要足夠的計算資源

### 3. 資金風險
- 需要充足的保證金
- 高槓桿增加風險
- 可能面臨強制平倉

## 🛠️ 最佳實踐

### 1. 參數設置
- 從較保守的參數開始
- 逐步調整風險水平
- 定期回顧和優化

### 2. 監控要點
- 關注庫存偏離程度
- 監控策略PnL
- 觀察價差變化

### 3. 風控建議
- 設置合理的風險限額
- 定期檢查策略表現
- 避免在極端市場條件下運行

## 🔧 故障排除

### 常見問題

**Q: 策略不下單？**
A: 檢查是否完成市場數據收集，確認訂單簿深度足夠

**Q: 價差過大？**
A: 調整 min_spread 參數或檢查市場流動性

**Q: 頻繁觸發止損？**
A: 考慮調整 stop_loss_spread 或降低槓桿

**Q: 自適應學習不收斂？**
A: 調整 learning_rate 或擴大 gamma 範圍

## 📞 支援

如有問題，請參考：
1. Hummingbot 官方文檔
2. 社群討論區
3. GitHub Issues

---

**⚡ 重要提醒**: 這是一個高頻交易策略，建議先在模擬環境中測試，確認理解所有參數後再投入實盤交易。合約交易具有高風險，請謹慎評估自身風險承受能力。