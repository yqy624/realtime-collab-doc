import asyncio
import time
import unittest

from app.services.collaboration_hub import InMemoryPresenceStore


class CollaborationHubTests(unittest.TestCase):
    def test_presence_keeps_user_online_until_all_connections_leave(self):
        async def run():
            store = InMemoryPresenceStore(ttl_seconds=30)
            await store.join(1, "conn-a", "user1")
            await store.join(1, "conn-b", "user1")
            await store.leave(1, "conn-a")

            self.assertEqual(await store.get_online_users(1), ["user1"])

            await store.leave(1, "conn-b")
            self.assertEqual(await store.get_online_users(1), [])

        asyncio.run(run())

    def test_presence_expires_stale_connections(self):
        async def run():
            store = InMemoryPresenceStore(ttl_seconds=1)
            await store.join(1, "conn-a", "user1")
            store._connections[1]["conn-a"] = ("user1", time.time() - 1)

            self.assertEqual(await store.get_online_users(1), [])

        asyncio.run(run())

    def test_heartbeat_extends_presence(self):
        async def run():
            store = InMemoryPresenceStore(ttl_seconds=1)
            await store.join(1, "conn-a", "user1")
            store._connections[1]["conn-a"] = ("user1", time.time() - 1)
            await store.heartbeat(1, "conn-a")

            self.assertEqual(await store.get_online_users(1), ["user1"])

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
