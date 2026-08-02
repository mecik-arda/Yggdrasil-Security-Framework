"""Thread safety ve concurrency testleri"""
import pytest, threading, time
from yggapp import create_app, init_services


@pytest.fixture(scope="session")
def app():
    a = create_app("test")
    init_services(a)
    return a


class TestTaskManagerConcurrency:
    def test_create_many_tasks(self):
        """Aynı anda çok sayıda task oluşturma."""
        from core.task_manager import create_task
        ids = [create_task(f"tool_{i}", f"target_{i}", "run") for i in range(50)]
        assert len(ids) == 50
        assert len(set(ids)) == 50  # hepsi unique

    def test_concurrent_kill_all(self):
        from core.task_manager import kill_all_tasks
        results = []
        def worker():
            results.append(kill_all_tasks())
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 5


class TestC2LockReentrancy:
    def test_rlock_reentrant(self):
        """C2_LOCK RLock ise aynı thread tekrar lock alabilir."""
        from handlers.c2_listener import C2_LOCK
        assert "RLock" in str(type(C2_LOCK))

    def test_stop_all_no_deadlock(self):
        from handlers.c2_listener import stop_all_listeners
        import time
        done = []
        def worker():
            stop_all_listeners()
            done.append(True)
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(timeout=5)
        assert not t.is_alive(), "stop_all_listeners deadlock!"
        assert len(done) == 1


class TestDBConcurrency:
    def test_concurrent_db_reads(self):
        from core.db import get_db_stats
        results = []
        def worker():
            results.append(get_db_stats())
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 5
        for r in results:
            assert "total_scans" in r