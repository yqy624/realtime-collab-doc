# -*- coding: utf-8 -*-
"""验证分享后文档对目标用户可见"""
import json
import urllib.request

BASE = "http://localhost:3000/new/api"


def api(method, path, body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if body:
        req.data = json.dumps(body).encode()
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def login(u, p):
    return api("POST", "/auth/login", {"username": u, "password": p})["data"]["token"]


t1 = login("user1", "password123")
t2 = login("user2", "password123")
print("两个用户登录成功")

# user1 创建文档
doc = api("POST", "/documents", {"title": "协作测试文档", "content": "hi", "isPublic": False}, t1)
doc_id = doc["data"]["id"]
print(f"user1 创建文档 id={doc_id}")

# user1 分享给 user2
r = api("POST", f"/documents/{doc_id}/share/users", {"username": "user2", "permission": "edit"}, t1)
print("分享后 users:", len(r["data"]["users"]))

# user2 看列表
docs = api("GET", "/documents", token=t2)
titles = [d["title"] for d in docs["data"]]
print("user2 文档列表:", titles)
print("协作测试文档可见:", "协作测试文档" in titles)
