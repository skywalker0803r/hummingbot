# 📊 參數更新機制說明

## 🔄 回答你的兩個問題

### 1. **波動率計算 K線間隔**
✅ **已修正！** 現在預設使用 **1分鐘 K線** 計算波動率，並且用戶可以自由設定：

- 新增配置項：`auto_optimize_kline_interval`
- 可選擇：`1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`
- 預設值：`1m` (1分鐘)
- 用戶在創建策略時會被詢問要使用哪種K線間隔

### 2. **參數更新機制** 
✅ **確認！** 策略會在運行過程中**持續線上更新參數**：

#### 🚀 啟動時
- 立即計算一次最佳參數
- 使用這些參數開始交易

#### 🔄 運行中
- 每個 `tick()` 都會檢查是否需要更新參數
- 根據設定的時間間隔（預設60分鐘）重新計算
- 如果參數有顯著變化，立即更新並記錄日誌

#### 📋 更新流程
```python
def tick(self, timestamp: float):
    # ... 其他邏輯 ...
    
    # 🔄 檢查並更新自動參數優化
    self.update_optimal_params()  # ← 每個tick都會調用
    
    # ... 繼續策略邏輯 ...
```

#### ⏰ 更新條件
```python
def update_optimal_params(self):
    current_time = self.current_timestamp
    if current_time - self._auto_optimize_last_update < self._auto_optimize_update_interval:
        return  # 還沒到更新時間
        
    # 重新計算參數...
    # 更新 bid_spread, ask_spread 等...
    # 記錄變化日誌
```

## 🎯 實際效果

### 例如設定每30分鐘更新一次：
```
10:00 - 策略啟動，計算初始參數 (bid_spread: 0.1%, ask_spread: 0.1%)
10:30 - 重新計算，發現波動率上升，更新參數 (bid_spread: 0.15%, ask_spread: 0.15%) 
11:00 - 重新計算，波動率下降，更新參數 (bid_spread: 0.08%, ask_spread: 0.08%)
... 持續這個過程
```

### 📝 日誌範例：
```
🔄 參數已更新:
   📈 Bid Spread: 0.1000% → 0.1500%
   📉 Ask Spread: 0.1000% → 0.1500%
   💰 Long Profit Taking: 0.2500%
   💰 Short Profit Taking: 0.2500%
   🛑 Stop Loss: 5.2000%
   📊 波動率: 2.85% (使用 1m K線)
```

## ✨ 新增的K線配置

當用戶選擇啟用自動優化時，會看到新的配置選項：

```
K-line interval for volatility calculation (1m/5m/15m/1h/1d) >>> 1m
```

系統會根據選擇的間隔正確計算日化波動率：
- 1m: `std * √(1440)` (1天有1440分鐘)
- 5m: `std * √(288)` (1天有288個5分鐘)  
- 1h: `std * √(24)` (1天有24小時)
- 1d: `std * √(1)` (1天就是1天)

## 🎉 總結

**是的，你的策略會：**
1. ✅ 使用1分鐘K線計算波動率（可設定）
2. ✅ 在運行過程中持續線上更新參數
3. ✅ 根據市場波動率變化自動調整spread
4. ✅ 詳細記錄每次參數變化

這樣讓策略能夠真正**自適應市場變化**，在高波動時期擴大價差保護資金，在低波動時期縮小價差提高成交率！