#!/usr/bin/env python3
"""
Heartbeat Render - 定时访问 Render 部署的服务以保持其活跃
每10分钟访问一次指定的URL
"""

import time
import requests
from datetime import datetime

# 配置
URL = "https://terminaltoolkit.onrender.com"
INTERVAL = 600  # 10分钟 = 600秒


def heartbeat():
    """发送心跳请求"""
    try:
        response = requests.get(URL, timeout=30)
        status = response.status_code
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Heartbeat OK - Status: {status}")
        return True
    except requests.exceptions.Timeout:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Heartbeat FAILED - Timeout")
        return False
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Heartbeat FAILED - {e}")
        return False


def main():
    print(f"=== Heartbeat Render Started ===")
    print(f"URL: {URL}")
    print(f"Interval: {INTERVAL} seconds (10 minutes)")
    print(f"================================")

    while True:
        heartbeat()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
