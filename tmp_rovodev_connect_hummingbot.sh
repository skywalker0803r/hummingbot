#!/bin/bash

echo "=== Hummingbot 連接助手 ==="
echo ""

# 檢查容器是否存在和運行
if [ ! "$(docker ps -q -f name=hummingbot)" ]; then
    if [ "$(docker ps -aq -f name=hummingbot)" ]; then
        echo "⚠️  容器存在但未運行，正在啟動..."
        docker start hummingbot
        sleep 3
    else
        echo "❌ 容器不存在，請先運行部署腳本"
        exit 1
    fi
fi

echo "🔍 容器狀態:"
docker ps --filter name=hummingbot --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
echo ""

# 方法1: 使用 docker exec (推薦)
echo "🚀 方法1: 使用 docker exec (推薦)"
echo "嘗試進入容器..."

if docker exec -it hummingbot /bin/bash -c "echo '連接測試成功'" &>/dev/null; then
    echo "✅ exec 方式可用"
    echo "執行: docker exec -it hummingbot /bin/bash"
    echo ""
    read -p "是否現在使用 exec 方式進入容器? (y/n): " choice
    if [[ $choice == "y" || $choice == "Y" ]]; then
        docker exec -it hummingbot /bin/bash
        exit 0
    fi
else
    echo "❌ exec 方式失敗"
fi

echo ""

# 方法2: 檢查 attach 為什麼失敗
echo "🔍 方法2: 診斷 attach 失敗原因"

# 檢查容器 TTY 配置
TTY_CONFIG=$(docker inspect hummingbot | grep '"Tty"' | grep -o 'true\|false')
STDIN_CONFIG=$(docker inspect hummingbot | grep '"OpenStdin"' | grep -o 'true\|false')

echo "TTY 配置: $TTY_CONFIG"
echo "STDIN 配置: $STDIN_CONFIG"

if [[ "$TTY_CONFIG" == "true" && "$STDIN_CONFIG" == "true" ]]; then
    echo "✅ 容器配置支持 attach"
    echo "嘗試 attach..."
    
    # 檢查是否有其他進程已經 attach
    if timeout 5 docker attach --no-stdin hummingbot </dev/null; then
        echo "✅ attach 測試成功"
        read -p "是否嘗試完整的 attach? (y/n): " choice
        if [[ $choice == "y" || $choice == "Y" ]]; then
            echo "執行: docker attach hummingbot"
            echo "提示: 按 Ctrl+P 然後 Ctrl+Q 退出而不停止容器"
            docker attach hummingbot
        fi
    else
        echo "❌ attach 測試失敗"
        echo "可能原因："
        echo "- 容器主進程已退出"
        echo "- 已有其他會話 attach 到容器"
        echo "- 容器內沒有可互動的進程"
    fi
else
    echo "❌ 容器配置不支持 attach (TTY: $TTY_CONFIG, STDIN: $STDIN_CONFIG)"
fi

echo ""

# 方法3: 檢查容器內的進程
echo "🔍 方法3: 檢查容器內進程"
echo "容器內運行的進程:"
if docker exec hummingbot ps aux 2>/dev/null; then
    echo ""
    echo "如果看到 Python/Hummingbot 進程在運行，容器是正常的"
else
    echo "❌ 無法檢查容器內進程，容器可能有問題"
fi

echo ""

# 方法4: 查看容器日誌
echo "📜 容器日誌 (最近20行):"
docker logs --tail 20 hummingbot

echo ""
echo "=== 建議的解決方案 ==="
echo ""
echo "1. 優先使用 exec 方式 (更穩定):"
echo "   docker exec -it hummingbot /bin/bash"
echo ""
echo "2. 如果需要直接連到 Hummingbot 程序:"
echo "   docker exec -it hummingbot python bin/hummingbot_quickstart.py"
echo ""
echo "3. 如果容器有問題，重新創建:"
echo "   docker compose down && docker compose up -d"
echo ""
echo "4. 查看實時日誌:"
echo "   docker logs -f hummingbot"