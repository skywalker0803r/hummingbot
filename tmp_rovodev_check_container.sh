#!/bin/bash

echo "=== Hummingbot 容器診斷 ==="
echo ""

# 檢查容器狀態
echo "🔍 檢查容器狀態:"
docker ps -a --filter name=hummingbot --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"
echo ""

# 檢查容器是否存在
if [ "$(docker ps -aq -f name=hummingbot)" ]; then
    echo "✅ 容器存在"
    
    # 檢查容器是否運行中
    if [ "$(docker ps -q -f name=hummingbot)" ]; then
        echo "✅ 容器正在運行"
        
        # 檢查容器進程
        echo ""
        echo "🔍 容器內進程:"
        docker exec hummingbot ps aux || echo "❌ 無法執行 ps 命令"
        
        # 檢查容器日誌
        echo ""
        echo "📜 最近的容器日誌:"
        docker logs --tail 20 hummingbot
        
        # 嘗試不同的連接方式
        echo ""
        echo "🔧 測試不同的連接方式:"
        
        echo "1. 嘗試 docker exec (推薦):"
        echo "   docker exec -it hummingbot /bin/bash"
        
        echo ""
        echo "2. 嘗試 docker attach (如果容器有 TTY):"
        echo "   docker attach hummingbot"
        
        echo ""
        echo "3. 檢查容器配置:"
        docker inspect hummingbot | grep -A 5 -B 5 "Tty\|OpenStdin\|AttachStdin\|AttachStdout\|AttachStderr"
        
    else
        echo "❌ 容器已停止"
        echo ""
        echo "📜 停止前的日誌:"
        docker logs --tail 50 hummingbot
        
        echo ""
        echo "🔧 嘗試重新啟動:"
        echo "   docker start hummingbot"
        echo "   docker logs -f hummingbot"
    fi
else
    echo "❌ 容器不存在"
    echo "請先運行部署腳本創建容器"
fi

echo ""
echo "=== 常見解決方案 ==="
echo ""
echo "1. 如果 attach 失敗，使用 exec 替代:"
echo "   docker exec -it hummingbot /bin/bash"
echo ""
echo "2. 如果容器停止了，重新啟動:"
echo "   docker start hummingbot"
echo ""
echo "3. 如果容器一直重啟，檢查日誌:"
echo "   docker logs -f hummingbot"
echo ""
echo "4. 重新創建容器:"
echo "   docker compose down"
echo "   docker compose up -d"