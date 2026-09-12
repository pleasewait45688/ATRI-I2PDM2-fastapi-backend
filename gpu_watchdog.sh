#!/bin/bash

# === 設定參數 ===
COMPOSE_FILE="docker-compose.yaml"
CONTAINER_NAME="backend"  # ✅ 請修改為你在 compose 裡定義的容器名稱
LOG_FILE="./gpu_watchdog.log"
CHECK_INTERVAL=600  # 單位：秒（這裡是每 10 分鐘檢查一次）

# === 切換到這個 script 所在的目錄（與 docker-compose.yaml 同層）===
cd "$(dirname "$0")" || exit 1

# === GPU 檢查函式 ===
check_container_gpu() {
    docker exec "$CONTAINER_NAME" nvidia-smi > /dev/null 2>&1
    return $?
}

# === 監控迴圈 ===
while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    if ! check_container_gpu; then
        echo "[$TIMESTAMP] ❌ Container '$CONTAINER_NAME' GPU 驗證失敗，準備重啟 docker compose..." | tee -a "$LOG_FILE"

        docker compose -f "$COMPOSE_FILE" down
        sleep 3
        docker compose -f "$COMPOSE_FILE" up -d

        echo "[$TIMESTAMP] ✅ docker compose 已重啟。" | tee -a "$LOG_FILE"
    else
        echo "[$TIMESTAMP] ✅ Container '$CONTAINER_NAME' GPU 正常。" >> "$LOG_FILE"
    fi

    sleep "$CHECK_INTERVAL"
done
