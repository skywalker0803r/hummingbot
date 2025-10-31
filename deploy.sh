#!/bin/bash

# Hummingbot 自定義鏡像部署腳本
# 使用方法: ./deploy.sh [版本號]

set -e

# 配置參數 - 請修改為您的設定
DOCKER_USERNAME="skywalker0803r"  # 替換為您的 Docker Hub 用戶名
IMAGE_NAME="hummingbot-adaptive"
DEFAULT_TAG="latest"

# 取得版本參數
VERSION_TAG=${1:-$DEFAULT_TAG}

echo "=== Hummingbot 自定義鏡像部署 ==="
echo "Docker Hub 用戶名: $DOCKER_USERNAME"
echo "鏡像名稱: $IMAGE_NAME"
echo "標籤: $VERSION_TAG"
echo ""

# 檢查是否已登入 Docker Hub
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未運行，請先啟動 Docker"
    exit 1
fi

echo "🔧 檢查 Docker Hub 登入狀態..."
if ! docker system info | grep -q "Username:"; then
    echo "⚠️  請先登入 Docker Hub:"
    echo "   docker login"
    exit 1
fi

# 構建鏡像
echo "🏗️  構建鏡像..."
docker build -t ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION_TAG} .

# 如果不是 latest，也標記為 latest
if [ "$VERSION_TAG" != "latest" ]; then
    echo "🏷️  標記為 latest..."
    docker tag ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION_TAG} ${DOCKER_USERNAME}/${IMAGE_NAME}:latest
fi

# 推送到 Docker Hub
echo "📤 推送鏡像到 Docker Hub..."
docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION_TAG}

if [ "$VERSION_TAG" != "latest" ]; then
    docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:latest
fi

echo ""
echo "✅ 部署完成！"
echo ""
echo "📋 接下來的步驟："
echo "1. 修改 docker-compose.prod.yml 中的鏡像名稱為: ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION_TAG}"
echo "2. 在生產環境執行:"
echo "   docker compose -f docker-compose.prod.yml pull"
echo "   docker compose -f docker-compose.prod.yml up -d"
echo ""
echo "🔍 查看鏡像: https://hub.docker.com/r/${DOCKER_USERNAME}/${IMAGE_NAME}"