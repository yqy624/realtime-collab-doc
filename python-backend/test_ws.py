# -*- coding: utf-8 -*-
"""测试 WebSocket 在线人数广播"""
import json
import time
import threading
import websocket
import urllib.request

BASE = "http://localhost:3000/new/api"
WS = "ws://localhost:3000/new/api/ws"


def login(username, password):
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": username, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["data"]["token"]


def connect_user(name, token, doc_id, results):
    ws = websocket.WebSocket()
    ws.connect(f"{WS}?token={token}")
    # 发 JOIN
    ws.send(json.dumps({"type": "JOIN", "documentId": doc_id}))
    # 收消息 3 秒
    end = time.time() + 4
    while time.time() < end:
        ws.settimeout(1)
        try:
            msg = ws.recv()
            results.append(f"[{name}] {msg[:120]}")
        except Exception:
            pass
    ws.close()


# 登录两个用户
t1 = login("admin", "password123")
t2 = login("user1", "password123")
print("两个用户登录成功")

results = []
doc_id = 2  # 测试文档

# 用户1先连接
th1 = threading.Thread(target=connect_user, args=("admin", t1, doc_id, results))
th1.start()
time.sleep(1)

# 用户2再连接
th2 = threading.Thread(target=connect_user, args=("user1", t2, doc_id, results))
th2.start()
th2.join(timeout=6)
th1.join(timeout=8)

for r in results:
    print(r)
print("=== 测试完成 ===")
