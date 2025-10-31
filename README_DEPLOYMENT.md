# 🚀 Hummingbot 自定義鏡像部署指南

## 📋 總覽

您現在有了完整的部署解決方案，包含：
- ✅ 自適應 Gamma 功能
- ✅ Bitget 連接器
- ✅ Docker 鏡像自動化部署

## 🔧 部署流程

### 步驟 1: 準備 Docker Hub

1. 註冊 [Docker Hub](https://hub.docker.com/) 帳號
2. 在本地登入：
```bash
docker login
```

### 步驟 2: 修改部署腳本

編輯 `deploy.sh` 和 `gcp_deploy.sh`，將 `yourusername` 替換為您的 Docker Hub 用戶名：

```bash
DOCKER_USERNAME="skywalker0803r"  # 改為您的用戶名
```

### 步驟 3: 構建並推送鏡像

```bash
# Linux/Mac
chmod +x deploy.sh
./deploy.sh

# Windows (使用 Git Bash 或 WSL)
bash deploy.sh

# 或者手動構建
docker build -t yourusername/hummingbot-adaptive:latest .
docker push yourusername/hummingbot-adaptive:latest
```

### 步驟 4: 在 GCP VM 部署

1. 將 `gcp_deploy.sh` 上傳到 GCP VM
2. 修改其中的 Docker Hub 用戶名
3. 執行部署：

```bash
chmod +x gcp_deploy.sh
./gcp_deploy.sh
```

## 📁 文件說明

| 文件 | 用途 |
|------|------|
| `deploy.sh` | 本地構建和推送腳本 |
| `gcp_deploy.sh` | GCP VM 快速部署腳本 |
| `docker-compose.prod.yml` | 生產環境配置 |
| `tmp_rovodev_docker_deployment_guide.md` | 詳細指南 |

## 🎯 優勢

1. **一次構建，處處運行**: 不需要每次重新編譯
2. **快速部署**: 新 VM 只需 2 分鐘設置
3. **版本控制**: 可以標記和回滾版本
4. **自動重啟**: 容器自動重啟保證穩定性

## 🚀 日常使用

### 更新代碼
```bash
# 1. 修改代碼後推送新版本
./deploy.sh v1.0.1

# 2. 在生產環境更新
docker compose pull
docker compose up -d
```

### 監控服務
```bash
# 查看狀態
docker ps

# 查看日誌
docker logs -f hummingbot

# 進入容器
docker attach hummingbot
```

### 管理服務
```bash
# 重啟
docker compose restart

# 停止
docker compose down

# 完全重新部署
docker compose down
docker compose pull
docker compose up -d
```

## 🔍 故障排除

### 常見問題

1. **權限問題**: 確保用戶在 docker 群組中
```bash
sudo usermod -aG docker $USER
# 然後重新登入
```

2. **鏡像更新問題**: 強制拉取最新版本
```bash
docker compose pull --ignore-buildable
```

3. **容器無法啟動**: 檢查日誌
```bash
docker logs hummingbot
```

## 📞 支援

如有問題，請檢查：
1. Docker 是否正確安裝
2. 網絡連接是否正常
3. 配置文件是否正確
4. 日誌中的錯誤信息

---

*現在您可以享受快速、一致的 Hummingbot 部署體驗！* 🎉