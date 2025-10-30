# Avellaneda-Stoikov 自適應 Gamma 實現

## 概述

本實現為 Hummingbot 的 Avellaneda-Stoikov 做市策略添加了自適應風險因子 (gamma) 功能。現在 `risk_factor` 參數不僅支持固定數值，還支持兩種自適應方法。

## 功能特點

### 1. 在線學習模式 (`adaptive`)
- 使用 `OnlineGammaLearner` 類別
- 基於簡單的梯度下降和獎勵信號
- 實時調整 gamma 值以優化策略表現
- 考慮因素：
  - PnL 變化
  - 庫存偏離程度
  - 市場波動率
  - 價差效率

### 2. 簡單自適應模式 (`simple_adaptive`)
- 使用 `SimpleGammaScheduler` 類別
- 基於預定義規則調整 gamma
- 考慮因素：
  - 市場波動率（高波動 → 增加 gamma）
  - 庫存偏離（偏離嚴重 → 增加 gamma）
  - 市場趨勢（牛市 → 降低 gamma，熊市 → 增加 gamma）

### 3. 傳統固定模式
- 保持向後兼容性
- 支持數值輸入（如 `1.5`, `2.0` 等）

## 使用方法

### 配置策略
在創建 Avellaneda 策略時，`risk_factor` 欄位現在支持：

```
Enter risk factor (γ) or adaptive method ('adaptive', 'simple_adaptive'): adaptive
```

或者

```
Enter risk factor (γ) or adaptive method ('adaptive', 'simple_adaptive'): simple_adaptive
```

或者傳統的數值：

```
Enter risk factor (γ) or adaptive method ('adaptive', 'simple_adaptive'): 1.5
```

### 狀態監控
當使用自適應模式時，策略狀態會顯示額外信息：

```
Strategy parameters:
  risk_factor(γ)= 1.234567E+00 (Adaptive Learning)
  order_book_intensity_factor(Α)= 2.345678E-01
  order_book_depth_factor(κ)= 3.456789E+02
  volatility= 1.234%
  inventory_deviation= 0.123
  total_pnl= 0.056789
  gamma_range= (0.5, 2.0)
  avg_reward= 0.012345
```

## 技術實現

### 文件結構
```
hummingbot/strategy/avellaneda_market_making/
├── adaptive_gamma_learner.py          # 新增：學習器實現
├── avellaneda_market_making.pyx       # 修改：主策略文件
├── avellaneda_market_making.pxd       # 修改：Cython 聲明
└── avellaneda_market_making_config_map_pydantic.py  # 修改：配置文件
```

### 核心類別

#### OnlineGammaLearner
```python
class OnlineGammaLearner:
    def __init__(self, initial_gamma=1.0, learning_rate=0.01, ...)
    def update(self, current_pnl, inventory_deviation, volatility, spread)
    def get_current_gamma()
    def get_statistics()
```

#### SimpleGammaScheduler
```python
class SimpleGammaScheduler:
    def __init__(self, base_gamma=1.0)
    def get_gamma(self, volatility, inventory_deviation, market_trend=None)
```

### 學習機制

#### 獎勵函數
```python
reward = pnl_change + inventory_penalty + spread_efficiency
```

其中：
- `pnl_change`: PnL 變化獎勵
- `inventory_penalty`: 庫存偏離懲罰 (-0.1 * |偏離|)
- `spread_efficiency`: 價差效率獎勵

#### 梯度估計
使用簡單的策略梯度方法：
- 比較最近獎勵與歷史基線
- 根據獎勵提升方向調整 gamma
- 限制 gamma 在合理範圍內 (0.1 - 10.0)

## 部署指南

### 1. 代碼更新
```bash
# 在開發環境
git add .
git commit -m "Add adaptive gamma feature to Avellaneda strategy"
git push origin main
```

### 2. GCP VM 部署
```bash
# 在 GCP VM 上
cd /path/to/hummingbot
git pull

# 修改 docker-compose.yml 啟用本地構建
# 取消註釋 build 部分，註釋掉 image 行

# 重新構建並部署
docker compose down
docker compose build
docker compose up -d

# 檢查日誌
docker logs -f hummingbot
```

### 3. 策略配置
```bash
# 連接到容器
docker attach hummingbot

# 創建新策略
create

# 選擇 avellaneda_market_making
# 在 risk_factor 提示時輸入 'adaptive' 或 'simple_adaptive'
```

## 調試和監控

### 啟用調試模式
在策略配置中啟用調試可以看到詳細的 gamma 更新日誌：

```
Adaptive gamma updated: 1.234567, PnL: 0.012345, inventory_deviation: 0.123456, volatility: 0.012345
```

### 監控指標
- `gamma` 值的變化趨勢
- `inventory_deviation` 庫存偏離程度
- `total_pnl` 累積 PnL
- `avg_reward` 平均獎勵信號

## 注意事項

### 1. 學習期間
- 初始階段 gamma 可能變化較大
- 建議先在測試環境運行觀察
- 通常需要 100-500 個 tick 才能穩定

### 2. 參數調整
可以在 `adaptive_gamma_learner.py` 中調整：
- `learning_rate`: 學習率（預設 0.01）
- `gamma_min/max`: gamma 範圍（預設 0.1-10.0）
- `update_frequency`: 更新頻率（預設每 10 個 tick）

### 3. 風險控制
- 自適應 gamma 可能在某些市場條件下表現不佳
- 建議設置適當的停損機制
- 監控 `avg_reward` 指標，如果持續為負數可能需要調整

## 擴展可能性

### 1. 更複雜的學習算法
- 集成 JAX 用於自動微分
- 使用神經網絡替代簡單規則
- 多臂老虎機方法

### 2. 更多狀態信息
- 訂單簿深度
- 成交量模式
- 時間序列特徵

### 3. 多資產學習
- 跨交易對的知識遷移
- 市場狀態分類
- 動態特徵選擇

## 問題排查

### 常見問題
1. **導入錯誤**: 確保所有文件都正確創建且路徑正確
2. **Cython 編譯錯誤**: 檢查 `.pxd` 文件中的變數聲明
3. **配置驗證失敗**: 確保輸入的字符串完全匹配 'adaptive' 或 'simple_adaptive'
4. **學習器未初始化**: 檢查 `_initialize_adaptive_gamma()` 方法是否被正確調用

### 日誌檢查
```bash
# 檢查 Hummingbot 日誌
docker logs hummingbot | grep -i "gamma\|adaptive"

# 檢查錯誤日誌
docker logs hummingbot | grep -i "error"
```

## 聯繫和貢獻

這個實現是基於討論紀錄中的需求開發的。如果遇到問題或有改進建議，請檢查：
1. 程式碼邏輯是否正確
2. 配置是否正確設置
3. 市場數據是否正常

---

*最後更新：2024年*