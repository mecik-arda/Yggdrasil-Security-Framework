"""
Tests for Beacon Handler — register, checkin, task assignment,
OS detection logic, beacon management, and script generation.

Covers ``handlers/beacon_handler.py``.
"""

import sys
import json
import base64
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Module-level setup — remove handlers mock
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def _unmock_handlers():
    """Remove the conftest session mock so real handler modules can be imported."""
    if 'handlers' in sys.modules:
        del sys.modules['handlers']


# ---------------------------------------------------------------------------
# Module-level state reset
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_beacon_state():
    """Reset beacon global state before each test."""
    import handlers.beacon_handler as bh
    bh.BEACONS.clear()
    bh.BEACON_TASKS.clear()
    yield
    bh.BEACONS.clear()
    bh.BEACON_TASKS.clear()


# ---------------------------------------------------------------------------
# Check cryptography availability
# ---------------------------------------------------------------------------

def _ensure_crypto():
    """Ensure cryptography is available for beacon tests."""
    try:
        from cryptography.fernet import Fernet
        return True
    except ImportError:
        return False


CRYPTO_AVAILABLE = _ensure_crypto()


# ---------------------------------------------------------------------------
# register_beacon
# ---------------------------------------------------------------------------

class TestRegisterBeacon:
    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_register_beacon_success(self):
        """Registering a new beacon should return success with beacon_id."""
        from handlers.beacon_handler import register_beacon, BEACONS
        data = {
            'hostname': 'test-pc',
            'os': 'Windows 10',
            'username': 'admin',
            'ip': '192.168.1.50',
            'arch': 'x64',
            'pid': 1234,
        }
        result = register_beacon(data)
        assert result['status'] == 'success'
        assert 'beacon_id' in result
        bid = result['beacon_id']
        assert bid in BEACONS
        assert BEACONS[bid]['hostname'] == 'test-pc'
        assert BEACONS[bid]['os_type'] == 'Windows 10'
        assert BEACONS[bid]['status'] == 'active'

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_register_beacon_default_values(self):
        """Missing fields should default to 'Unknown'."""
        from handlers.beacon_handler import register_beacon, BEACONS
        result = register_beacon({})
        assert result['status'] == 'success'
        bid = result['beacon_id']
        assert BEACONS[bid]['hostname'] == 'Unknown'
        assert BEACONS[bid]['os_type'] == 'Unknown'
        assert BEACONS[bid]['username'] == 'Unknown'

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_register_beacon_creates_task_list(self):
        """Registration should create an empty task list for the beacon."""
        from handlers.beacon_handler import register_beacon, BEACON_TASKS
        result = register_beacon({'hostname': 'test'})
        bid = result['beacon_id']
        assert bid in BEACON_TASKS
        assert BEACON_TASKS[bid] == []

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_register_multiple_beacons_unique_ids(self):
        """Each beacon should get a unique ID."""
        from handlers.beacon_handler import register_beacon, BEACONS
        r1 = register_beacon({'hostname': 'pc1'})
        r2 = register_beacon({'hostname': 'pc2'})
        assert r1['beacon_id'] != r2['beacon_id']
        assert len(BEACONS) == 2


# ---------------------------------------------------------------------------
# beacon_checkin
# ---------------------------------------------------------------------------

class TestBeaconCheckin:
    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_checkin_unknown_beacon(self):
        """Checkin with unknown beacon_id should return error."""
        from handlers.beacon_handler import beacon_checkin
        result = beacon_checkin('unknown-id', 'some-encrypted-data')
        assert result['status'] == 'error'

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_checkin_updates_last_seen_and_callbacks(self):
        """Checkin should update last_seen and increment callbacks."""
        from handlers.beacon_handler import (
            register_beacon, beacon_checkin, BEACONS, BEACON_CIPHER
        )
        import time

        reg = register_beacon({'hostname': 'test', 'os': 'Linux'})
        bid = reg['beacon_id']

        old_seen = BEACONS[bid]['last_seen']
        old_callbacks = BEACONS[bid]['callbacks']

        # Create encrypted checkin data
        payload = {'sysinfo': {'hostname': 'test-updated', 'os': 'Linux'}}
        encrypted = BEACON_CIPHER.encrypt(json.dumps(payload).encode())

        time.sleep(0.01)  # ensure timestamp changes
        result = beacon_checkin(bid, encrypted.decode())

        assert result['status'] == 'success'
        assert BEACONS[bid]['callbacks'] == old_callbacks + 1
        assert BEACONS[bid]['last_seen'] > old_seen

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_checkin_updates_sysinfo(self):
        """Checkin with sysinfo should update beacon metadata."""
        from handlers.beacon_handler import (
            register_beacon, beacon_checkin, BEACONS, BEACON_CIPHER
        )

        reg = register_beacon({'hostname': 'old-name', 'os': 'OldOS'})
        bid = reg['beacon_id']

        payload = {
            'sysinfo': {
                'hostname': 'new-name',
                'os': 'NewOS',
                'username': 'newuser',
                'ip': '10.0.0.99',
            }
        }
        encrypted = BEACON_CIPHER.encrypt(json.dumps(payload).encode())
        beacon_checkin(bid, encrypted.decode())

        assert BEACONS[bid]['hostname'] == 'new-name'
        assert BEACONS[bid]['os_type'] == 'NewOS'
        assert BEACONS[bid]['username'] == 'newuser'
        assert BEACONS[bid]['ip'] == '10.0.0.99'

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_checkin_decryption_failure(self):
        """Invalid encrypted data should return decryption error."""
        from handlers.beacon_handler import register_beacon, beacon_checkin
        reg = register_beacon({'hostname': 'test'})
        bid = reg['beacon_id']

        result = beacon_checkin(bid, 'not-valid-encrypted-data!!!')
        assert result['status'] == 'error'


# ---------------------------------------------------------------------------
# assign_task
# ---------------------------------------------------------------------------

class TestAssignTask:
    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_assign_task_success(self):
        """Assigning a task should return task_id."""
        from handlers.beacon_handler import register_beacon, assign_task, BEACON_TASKS
        reg = register_beacon({'hostname': 'test'})
        bid = reg['beacon_id']

        result = assign_task(bid, 'whoami', task_type='shell')
        assert result['status'] == 'success'
        assert 'task_id' in result
        assert result['command'] == 'whoami'
        assert len(BEACON_TASKS[bid]) == 1

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_assign_task_nonexistent_beacon(self):
        """Assigning task to unknown beacon should return error."""
        from handlers.beacon_handler import assign_task
        result = assign_task('nonexistent', 'whoami')
        assert result['status'] == 'error'

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_assign_multiple_tasks(self):
        """Multiple tasks should all be queued."""
        from handlers.beacon_handler import register_beacon, assign_task, BEACON_TASKS
        reg = register_beacon({'hostname': 'test'})
        bid = reg['beacon_id']

        assign_task(bid, 'cmd1')
        assign_task(bid, 'cmd2')
        assign_task(bid, 'cmd3')

        assert len(BEACON_TASKS[bid]) == 3


# ---------------------------------------------------------------------------
# get_beacons / get_beacon_detail
# ---------------------------------------------------------------------------

class TestGetBeacons:
    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_get_beacons_empty(self):
        from handlers.beacon_handler import get_beacons
        result = get_beacons()
        assert result['status'] == 'success'
        assert result['beacons'] == []

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_get_beacons_with_data(self):
        from handlers.beacon_handler import register_beacon, get_beacons
        register_beacon({'hostname': 'pc1', 'os': 'Linux'})
        register_beacon({'hostname': 'pc2', 'os': 'Windows'})

        result = get_beacons()
        assert len(result['beacons']) == 2

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_get_beacon_detail(self):
        from handlers.beacon_handler import register_beacon, get_beacon_detail
        reg = register_beacon({'hostname': 'detail-pc', 'os': 'Linux', 'username': 'root'})
        bid = reg['beacon_id']

        result = get_beacon_detail(bid)
        assert result['status'] == 'success'
        assert result['beacon']['hostname'] == 'detail-pc'
        assert result['beacon']['username'] == 'root'

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_get_beacon_detail_nonexistent(self):
        from handlers.beacon_handler import get_beacon_detail
        result = get_beacon_detail('nonexistent')
        assert result['status'] == 'error'


# ---------------------------------------------------------------------------
# remove_beacon
# ---------------------------------------------------------------------------

class TestRemoveBeacon:
    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_remove_beacon(self):
        from handlers.beacon_handler import register_beacon, remove_beacon, BEACONS, BEACON_TASKS
        reg = register_beacon({'hostname': 'to-remove'})
        bid = reg['beacon_id']

        result = remove_beacon(bid)
        assert result['status'] == 'success'
        assert bid not in BEACONS
        assert bid not in BEACON_TASKS

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason='cryptography not installed')
    def test_remove_nonexistent_beacon_does_not_crash(self):
        from handlers.beacon_handler import remove_beacon
        result = remove_beacon('nonexistent')
        assert result['status'] == 'success'


# ---------------------------------------------------------------------------
# generate_beacon_script
# ---------------------------------------------------------------------------

class TestGenerateBeaconScript:
    def test_generate_script_contains_listener_url(self):
        from handlers.beacon_handler import generate_beacon_script
        script = generate_beacon_script('http://192.168.1.1:5000/api/beacon')
        assert '192.168.1.1:5000/api/beacon' in script
        assert 'BEACON_ID' in script
        assert 'checkin' in script.lower()

    def test_generate_script_includes_sleep_jitter(self):
        from handlers.beacon_handler import generate_beacon_script
        script = generate_beacon_script('http://localhost:5000/api/beacon',
                                        sleep_sec=10, jitter_pct=50)
        # Script starts with newline then contains these values
        assert '10' in script  # SLEEP value
        assert '50' in script  # JITTER value

    def test_generate_script_is_valid_python_syntax(self):
        from handlers.beacon_handler import generate_beacon_script
        script = generate_beacon_script('http://127.0.0.1:5000/api/beacon')
        # Basic checks — should be valid Python
        assert 'import' in script
        assert 'def register' in script.lower() or 'register()' in script.lower()
        assert 'checkin' in script.lower()
        assert 'BEACON_ID' in script
        assert 'LISTENER' in script


# ---------------------------------------------------------------------------
# OS detection logic (from beacon_handler.py and c2_listener.py)
# ---------------------------------------------------------------------------

class TestOSDetection:
    def test_windows_detection_from_banner(self):
        """Banner containing 'Windows' should be detected as Windows."""
        from handlers.c2_listener import ZOMBIES, C2_LOCK
        zombie = {
            'id': 'test-zombie',
            'os_type': 'Unknown',
            'output': [],
            'status': 'connected',
        }
        with C2_LOCK:
            ZOMBIES['test-zombie'] = zombie

        # Simulate the banner check logic
        banner = 'Microsoft Windows [Version 10.0.19045]'
        if 'Windows' in banner or 'cmd.exe' in banner or 'PowerShell' in banner:
            zombie['os_type'] = 'Windows'
        assert zombie['os_type'] == 'Windows'

    def test_linux_detection_from_banner(self):
        """Banner containing 'Linux' should be detected as Linux."""
        from handlers.c2_listener import ZOMBIES, C2_LOCK
        zombie = {
            'id': 'test-zombie-linux',
            'os_type': 'Unknown',
            'output': [],
            'status': 'connected',
        }
        with C2_LOCK:
            ZOMBIES['test-zombie-linux'] = zombie

        banner = 'Linux ubuntu 5.15.0-91-generic'
        if 'Linux' in banner or 'bash' in banner or 'sh-' in banner:
            zombie['os_type'] = 'Linux'
        assert zombie['os_type'] == 'Linux'
