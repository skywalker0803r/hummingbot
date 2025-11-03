#!/bin/bash

# GCP VM 快速部署腳本
# 在 GCP VM 上運行此腳本來部署 Hummingbot

set -e

DOCKER_USERNAME="skywalker0803r"  # 替換為您的 Docker Hub 用戶名
IMAGE_NAME="hummingbot-adaptive"
TAG="latest"

echo "=== GCP VM Hummingbot 快速部署 ==="
echo ""

# 檢查 Docker 是否安裝
if ! command -v docker &> /dev/null; then
    echo "🔧 安裝 Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "⚠️  請登出並重新登入以使用 Docker，然後重新運行此腳本"
    exit 1
fi

# 檢查 Docker Compose 是否安裝
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "🔧 安裝 Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# 創建工作目錄
WORK_DIR="$HOME/hummingbot"
if [ ! -d "$WORK_DIR" ]; then
    echo "📁 創建工作目錄..."
    mkdir -p $WORK_DIR
fi

cd $WORK_DIR

# 創建必要的目錄
echo "📁 創建必要的目錄..."
mkdir -p conf conf/connectors conf/strategies conf/controllers conf/scripts logs data certs scripts controllers

# 下載 docker-compose.prod.yml
echo "📥 下載配置文件..."
cat > docker-compose.prod.yml << EOF
services:
  hummingbot:
    container_name: hummingbot
    image: ${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}
    volumes:
      - ./conf:/home/hummingbot/conf
      - ./conf/connectors:/home/hummingbot/conf/connectors
      - ./conf/strategies:/home/hummingbot/conf/strategies
      - ./conf/controllers:/home/hummingbot/conf/controllers
      - ./conf/scripts:/home/hummingbot/conf/scripts
      - ./logs:/home/hummingbot/logs
      - ./data:/home/hummingbot/data
      - ./certs:/home/hummingbot/certs
      - ./scripts:/home/hummingbot/scripts
      - ./controllers:/home/hummingbot/controllers
      - ./hummingbot:/home/hummingbot/hummingbot
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
    tty: true
    stdin_open: true
    network_mode: host
    restart: unless-stopped
EOF

# 拉取最新鏡像
echo "📥 拉取最新鏡像..."
docker pull ${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}

# 停止舊容器（如果存在）
if [ "$(docker ps -aq -f name=hummingbot)" ]; then
    echo "🛑 停止舊容器..."
    docker compose -f docker-compose.prod.yml down
fi

# 啟動 Hummingbot
echo "🚀 啟動 Hummingbot..."
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "✅ 部署完成！"
echo ""
echo "📋 管理命令:"
echo "  查看狀態: docker ps"
echo "  查看日誌: docker logs -f hummingbot"
echo "  進入容器: docker attach hummingbot"
echo "  停止服務: docker compose -f docker-compose.prod.yml down"
echo "  重啟服務: docker compose -f docker-compose.prod.yml restart"
echo ""
echo "📁 工作目錄: $WORK_DIR"
echo "⚙️  配置目錄: $WORK_DIR/conf"
echo "📜 日誌目錄: $WORK_DIR/logs"