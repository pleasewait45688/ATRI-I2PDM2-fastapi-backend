#!/bin/bash
while true; do
    if ! nvidia-smi > /dev/null 2>&1; then
        echo "⚠️ `nvidia-smi` 失敗，嘗試重新掛載 NVML..."
        ldconfig  # 直接執行，不使用 sudo
        sleep 5
        if ! nvidia-smi > /dev/null 2>&1; then
            echo "❌ `nvidia-smi` 仍然失敗，準備重啟容器..."
            exit 1  # 讓 Docker 重新啟動容器
        fi
    fi
    sleep 1800  # 每 30 分鐘檢查一次
done
