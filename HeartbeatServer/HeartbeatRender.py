#!/usr/bin/env python3
"""
Heartbeat Render - 定时访问 Render 部署的服务以保持其活跃
每10分钟访问一次指定的URL
"""

import time
import requests
from datetime import datetime

# 配置
URLS = [
    "https://terminaltoolkit.onrender.com",
    "https://efd-analyzer.onrender.com"
]
INTERVAL = 840  # 10分钟 = 840秒


def heartbeat(url):
    """发送心跳请求"""
    try:
        response = requests.get(url, timeout=30)
        status = response.status_code
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Heartbeat OK - {url} - Status: {status}")
        return True
    except requests.exceptions.Timeout:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Heartbeat FAILED - {url} - Timeout")
        return False
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Heartbeat FAILED - {url} - {e}")
        return False


def main():
    print(f"=== Heartbeat Render Started ===")
    print(f"URLs: {URLS}")
    print(f"Interval: {INTERVAL} seconds (10 minutes)")
    print(f"================================")

    while True:
        for url in URLS:
            heartbeat(url)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
