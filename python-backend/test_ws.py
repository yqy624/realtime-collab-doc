import json
import threading
import time
import urllib.error
import urllib.request

import pytest
import websocket


BASE = "http://localhost:3000/new/api"
WS = "ws://localhost:3000/new/api/ws"


def require_running_server():
    req = urllib.request.Request(BASE + "/health", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=3):
            return
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        pytest.skip(f"integration API server is not running at {BASE}: {exc}")


def login(username, password):
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": username, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=3) as resp:
        return json.loads(resp.read())["data"]["token"]


def create_document(token):
    req = urllib.request.Request(
        BASE + "/documents",
        data=json.dumps(
            {
                "title": f"WebSocket integration test {time.time_ns()}",
                "content": "initial",
                "isPublic": False,
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    with urllib.request.urlopen(req, timeout=3) as resp:
        return json.loads(resp.read())["data"]["id"]


def connect_user(name, token, doc_id, results):
    ws = websocket.WebSocket()
    try:
        ws.connect(f"{WS}?token={token}", timeout=3)
        ws.send(json.dumps({"type": "JOIN", "documentId": doc_id}))
        end = time.time() + 4
        while time.time() < end:
            ws.settimeout(1)
            try:
                msg = ws.recv()
                results.append(f"[{name}] {msg[:120]}")
            except Exception:
                pass
    finally:
        ws.close()


@pytest.mark.integration
def test_websocket_presence_broadcasts_join_events():
    require_running_server()

    admin_token = login("admin", "password123")
    user_token = login("user1", "password123")
    doc_id = create_document(admin_token)

    results = []
    first = threading.Thread(
        target=connect_user,
        args=("admin", admin_token, doc_id, results),
    )
    second = threading.Thread(
        target=connect_user,
        args=("user1", user_token, doc_id, results),
    )

    first.start()
    time.sleep(1)
    second.start()
    second.join(timeout=6)
    first.join(timeout=8)

    assert any('"type":"PRESENCE"' in result or '"type": "PRESENCE"' in result for result in results)
