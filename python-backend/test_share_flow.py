import json
import urllib.error
import urllib.request

import pytest


BASE = "http://localhost:3000/new/api"


def api(method, path, body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if body:
        req.data = json.dumps(body).encode()
    with urllib.request.urlopen(req, timeout=3) as resp:
        return json.loads(resp.read())


def require_running_server():
    try:
        api("GET", "/health")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        pytest.skip(f"integration API server is not running at {BASE}: {exc}")


def login(username, password):
    return api("POST", "/auth/login", {"username": username, "password": password})[
        "data"
    ]["token"]


@pytest.mark.integration
def test_shared_document_is_visible_to_target_user():
    require_running_server()

    owner_token = login("user1", "password123")
    target_token = login("user2", "password123")

    doc = api(
        "POST",
        "/documents",
        {"title": "Collaboration visibility test", "content": "hi", "isPublic": False},
        owner_token,
    )
    doc_id = doc["data"]["id"]

    api(
        "POST",
        f"/documents/{doc_id}/share/users",
        {"username": "user2", "permission": "edit"},
        owner_token,
    )

    docs = api("GET", "/documents", token=target_token)
    titles = [item["title"] for item in docs["data"]]

    assert "Collaboration visibility test" in titles
