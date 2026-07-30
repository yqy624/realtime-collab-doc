from collections import defaultdict


class SessionManager:
    """Track online users per document."""

    def __init__(self):
        self._document_users: dict[int, set[str]] = defaultdict(set)

    def join(self, document_id: int, username: str):
        self._document_users[document_id].add(username)
        return self.get_online_users(document_id)

    def leave(self, document_id: int, username: str):
        users = self._document_users.get(document_id)
        if users:
            users.discard(username)
            if not users:
                del self._document_users[document_id]
        return self.get_online_users(document_id)

    def get_online_users(self, document_id: int) -> list[str]:
        return list(self._document_users.get(document_id, set()))


session_manager = SessionManager()
