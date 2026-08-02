"""yggapp/repositories/c2_repository.py için testler"""
import time
import pytest
from yggapp.repositories.c2_repository import (
    persist_listener, load_all_listeners, delete_listener,
    persist_zombie, update_zombie_status, load_all_zombies,
)


class TestListenerPersistence:
    def test_persist_and_load(self):
        lid = "test-lid-001"
        data = {
            "name": "Test Listener",
            "port": 4444,
            "bind_addr": "127.0.0.1",
            "status": "running",
            "auth_enabled": True,
            "api_key": "abc123",
            "started_at": time.time(),
            "total_connections": 5,
        }
        persist_listener(lid, data)
        loaded = load_all_listeners()
        assert lid in loaded, f"Listener {lid} should be persisted"
        assert loaded[lid]["name"] == "Test Listener"
        assert loaded[lid]["port"] == 4444
        assert loaded[lid]["status"] == "running"

    def test_update_existing_listener(self):
        lid = "test-lid-002"
        persist_listener(lid, {"name": "V1", "port": 5555, "status": "running"})
        persist_listener(lid, {"name": "V2", "port": 5555, "status": "stopped"})
        loaded = load_all_listeners()
        assert loaded[lid]["name"] == "V2"
        assert loaded[lid]["status"] == "stopped"

    def test_delete_listener(self):
        lid = "test-lid-003"
        persist_listener(lid, {"name": "ToDelete", "port": 6666, "status": "running"})
        delete_listener(lid)
        loaded = load_all_listeners()
        assert lid not in loaded

    def test_load_empty(self):
        loaded = load_all_listeners()
        assert isinstance(loaded, dict)

    def test_partial_data(self):
        """Eksik alanlarla persist etmek hata vermemeli."""
        persist_listener("minimal", {"name": "M", "port": 7777})


class TestZombiePersistence:
    def test_persist_and_load_zombie(self):
        zid = "test-zid-001"
        data = {
            "listener_id": "lid-1",
            "addr": "192.168.1.1:12345",
            "hostname": "target-pc",
            "os_type": "Linux",
            "connected_at": time.time(),
            "last_seen": time.time(),
            "status": "connected",
        }
        persist_zombie(zid, data)
        loaded = load_all_zombies()
        assert zid in loaded
        assert loaded[zid]["hostname"] == "target-pc"
        assert loaded[zid]["os_type"] == "Linux"

    def test_update_zombie_status(self):
        zid = "test-zid-002"
        persist_zombie(zid, {"listener_id": "lid-2", "status": "connected"})
        update_zombie_status(zid, "disconnected")
        loaded = load_all_zombies()
        assert loaded[zid]["status"] == "disconnected"

    def test_load_empty_zombies(self):
        loaded = load_all_zombies()
        assert isinstance(loaded, dict)