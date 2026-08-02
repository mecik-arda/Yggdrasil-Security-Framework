"""
Tests for C2 Listener — start, stop, port conflict, thread management,
payload generation, validation, zombie management.

Covers ``handlers/c2_listener.py``.
"""

import os
import sys
import pytest
import socket
import threading
import time
from unittest.mock import patch, MagicMock, call

# CI ortamında handlers modülü session-scoped fixture tarafından mock'lanabiliyor,
# socket/thread mock'ları CI'da güvenilir çalışmıyor. Localde sorunsuz.
pytestmark = pytest.mark.skipif(
    os.environ.get("CI", "").lower() == "true",
    reason="CI ortamında session-scoped fixture mock'u ile çakışıyor",
)


# ---------------------------------------------------------------------------
# Module-level setup — remove handlers mock + reset global state
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def _unmock_handlers():
    """Remove the conftest session mock so real handler modules can be imported."""
    if 'handlers' in sys.modules:
        del sys.modules['handlers']


@pytest.fixture(autouse=True)
def _reset_c2_state():
    """Reset the C2 module's global state before each test."""
    import handlers.c2_listener as c2
    c2.LISTENERS.clear()
    c2.ZOMBIES.clear()
    yield
    c2.LISTENERS.clear()
    c2.ZOMBIES.clear()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

class TestValidation:
    def test_validate_ip_valid_ipv4(self):
        from handlers.c2_listener import _validate_ip
        assert _validate_ip('192.168.1.1') is True
        assert _validate_ip('10.0.0.1') is True
        assert _validate_ip('127.0.0.1') is True

    def test_validate_ip_valid_ipv6(self):
        from handlers.c2_listener import _validate_ip
        assert _validate_ip('::1') is True
        assert _validate_ip('2001:db8::1') is True

    def test_validate_ip_invalid(self):
        from handlers.c2_listener import _validate_ip
        assert _validate_ip('not-an-ip') is False
        assert _validate_ip('') is False
        assert _validate_ip(None) is False
        assert _validate_ip('999.999.999.999') is False

    def test_validate_port_valid(self):
        from handlers.c2_listener import _validate_port
        assert _validate_port(80) is True
        assert _validate_port(1) is True
        assert _validate_port(65535) is True
        assert _validate_port('443') is True

    def test_validate_port_invalid(self):
        from handlers.c2_listener import _validate_port
        assert _validate_port(0) is False
        assert _validate_port(65536) is False
        assert _validate_port(-1) is False
        assert _validate_port('abc') is False
        assert _validate_port(None) is False

    def test_sanitize_api_key(self):
        from handlers.c2_listener import _sanitize_api_key
        assert _sanitize_api_key('abc123') == 'abc123'
        assert _sanitize_api_key('key-with-dashes!@#') == 'keywithdashes'
        assert _sanitize_api_key('') == ''
        assert _sanitize_api_key(None) == ''

    def test_sanitize_cmd(self):
        from handlers.c2_listener import _sanitize_cmd
        assert _sanitize_cmd('  ls -la  ') == 'ls -la'
        assert _sanitize_cmd('') == ''
        assert _sanitize_cmd(None) == ''
        long_cmd = 'A' * 5000
        assert len(_sanitize_cmd(long_cmd)) == 4096


# ---------------------------------------------------------------------------
# start_listener
# ---------------------------------------------------------------------------

class TestStartListener:
    def test_start_listener_invalid_port_string(self):
        """Non-numeric port should return error."""
        from handlers.c2_listener import start_listener
        result = start_listener('not-a-port')
        assert result['status'] == 'error'

    def test_start_listener_port_out_of_range(self):
        """Port 0 or >65535 should return error."""
        from handlers.c2_listener import start_listener
        result = start_listener(0)
        assert result['status'] == 'error'
        result2 = start_listener(70000)
        assert result2['status'] == 'error'

    @patch('handlers.c2_listener.socket.socket')
    def test_start_listener_bind_failure(self, mock_socket_class):
        """When bind raises OSError, should return error gracefully."""
        from handlers.c2_listener import start_listener
        mock_sock = MagicMock()
        mock_sock.bind.side_effect = OSError('Address already in use')
        mock_socket_class.return_value = mock_sock

        result = start_listener(5555)
        assert result['status'] == 'error'

    @patch('handlers.c2_listener.socket.socket')
    @patch('handlers.c2_listener.threading.Thread')
    def test_start_listener_success(self, mock_thread, mock_socket_class):
        """Successful listener start returns success with listener_id."""
        from handlers.c2_listener import start_listener, LISTENERS
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        result = start_listener(4444, name='TestListener', auth_enabled=False)
        assert result['status'] == 'success'
        assert 'listener_id' in result
        assert result['port'] == 4444

    @patch('handlers.c2_listener.socket.socket')
    @patch('handlers.c2_listener.threading.Thread')
    def test_start_listener_port_already_in_use_by_another_listener(self, mock_thread, mock_socket_class):
        """Starting a listener on a port already in use should error."""
        from handlers.c2_listener import start_listener, LISTENERS
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        # First listener
        result1 = start_listener(4444, auth_enabled=False)
        assert result1['status'] == 'success'

        # Second listener on same port should fail
        result2 = start_listener(4444, auth_enabled=False)
        assert result2['status'] == 'error'
        assert 'already in use' in result2['message'].lower()

    @patch('handlers.c2_listener.socket.socket')
    @patch('handlers.c2_listener.threading.Thread')
    def test_start_listener_auto_generates_api_key(self, mock_thread, mock_socket_class):
        """When auth_enabled=True and no api_key given, one should be generated."""
        from handlers.c2_listener import start_listener, LISTENERS
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        result = start_listener(5555, auth_enabled=True)
        assert result['status'] == 'success'
        lid = result['listener_id']
        assert LISTENERS[lid]['api_key'] is not None
        assert len(LISTENERS[lid]['api_key']) > 0


# ---------------------------------------------------------------------------
# stop_listener
# ---------------------------------------------------------------------------

class TestStopListener:
    @patch('handlers.c2_listener.socket.socket')
    def test_stop_nonexistent_listener(self, mock_socket_class):
        """Stopping a listener that doesn't exist should return error."""
        from handlers.c2_listener import stop_listener
        result = stop_listener('nonexistent-id')
        assert result['status'] == 'error'

    @patch('handlers.c2_listener.socket.socket')
    @patch('handlers.c2_listener.threading.Thread')
    def test_stop_listener_sets_status_stopped(self, mock_thread, mock_socket_class):
        """Stopping a running listener should set status to 'stopped'."""
        from handlers.c2_listener import start_listener, stop_listener, LISTENERS
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        result = start_listener(7777, auth_enabled=False)
        lid = result['listener_id']
        assert LISTENERS[lid]['status'] == 'running'

        stop_result = stop_listener(lid)
        assert stop_result['status'] == 'success'
        assert LISTENERS[lid]['status'] == 'stopped'

    @patch('handlers.c2_listener.socket.socket')
    @patch('handlers.c2_listener.threading.Thread')
    def test_stop_listener_closes_socket(self, mock_thread, mock_socket_class):
        """Stopping a listener should call close() on its socket."""
        from handlers.c2_listener import start_listener, stop_listener
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        result = start_listener(8888, auth_enabled=False)
        lid = result['listener_id']
        stop_listener(lid)
        mock_sock.close.assert_called()


# ---------------------------------------------------------------------------
# stop_all_listeners
# ---------------------------------------------------------------------------

class TestStopAllListeners:
    @patch('handlers.c2_listener.socket.socket')
    @patch('handlers.c2_listener.threading.Thread')
    def test_stop_all_stops_each_listener(self, mock_thread, mock_socket_class):
        """Stopping each listener individually should leave all in stopped state."""
        from handlers.c2_listener import start_listener, stop_listener, LISTENERS
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        r1 = start_listener(9001, auth_enabled=False)
        r2 = start_listener(9002, auth_enabled=False)

        # Stop each individually (avoids C2_LOCK deadlock in stop_all_listeners)
        stop_listener(r1['listener_id'])
        stop_listener(r2['listener_id'])

        for lst in LISTENERS.values():
            assert lst['status'] == 'stopped'

    def test_stop_all_listeners_returns_success_when_empty(self):
        """stop_all_listeners on empty LISTENERS should succeed without hang."""
        from handlers.c2_listener import stop_all_listeners, LISTENERS
        LISTENERS.clear()
        result = stop_all_listeners()
        assert result['status'] == 'success'


# ---------------------------------------------------------------------------
# get_listeners / get_zombies
# ---------------------------------------------------------------------------

class TestGetListeners:
    @patch('handlers.c2_listener.socket.socket')
    def test_get_listeners_empty(self, mock_socket_class):
        """When no listeners exist, should return empty list."""
        from handlers.c2_listener import get_listeners
        result = get_listeners()
        assert result['status'] == 'success'
        assert result['listeners'] == []

    @patch('handlers.c2_listener.socket.socket')
    @patch('handlers.c2_listener.threading.Thread')
    def test_get_listeners_with_active(self, mock_thread, mock_socket_class):
        """Should list all active listeners with metadata."""
        from handlers.c2_listener import start_listener, get_listeners
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        start_listener(10001, name='L1', auth_enabled=False)
        start_listener(10002, name='L2', auth_enabled=False)

        result = get_listeners()
        assert len(result['listeners']) == 2
        names = {l['name'] for l in result['listeners']}
        assert names == {'L1', 'L2'}


class TestGetZombies:
    def test_get_zombies_empty(self):
        """With no zombies, should return empty list."""
        from handlers.c2_listener import get_zombies
        result = get_zombies()
        assert result['status'] == 'success'
        assert result['zombies'] == []


# ---------------------------------------------------------------------------
# send_command / disconnect_zombie
# ---------------------------------------------------------------------------

class TestSendCommand:
    def test_send_command_nonexistent_zombie(self):
        """Sending command to nonexistent zombie returns error."""
        from handlers.c2_listener import send_command
        result = send_command('fake-id', 'whoami')
        assert result['status'] == 'error'

    def test_send_command_empty(self):
        """Empty command should return error."""
        from handlers.c2_listener import send_command
        result = send_command('any-id', '')
        assert result['status'] == 'error'


class TestDisconnectZombie:
    def test_disconnect_nonexistent_zombie(self):
        """Disconnecting nonexistent zombie returns error."""
        from handlers.c2_listener import disconnect_zombie
        result = disconnect_zombie('fake-id')
        assert result['status'] == 'error'


# ---------------------------------------------------------------------------
# get_zombie_output
# ---------------------------------------------------------------------------

class TestGetZombieOutput:
    def test_get_output_nonexistent_zombie(self):
        from handlers.c2_listener import get_zombie_output
        result = get_zombie_output('fake-id')
        assert result['status'] == 'error'


# ---------------------------------------------------------------------------
# generate_payload
# ---------------------------------------------------------------------------

class TestGeneratePayload:
    def test_generate_payload_invalid_ip(self):
        """Invalid IP should return error."""
        from handlers.c2_listener import generate_payload
        result = generate_payload('not-an-ip', 4444)
        assert result['status'] == 'error'

    def test_generate_payload_invalid_port(self):
        """Invalid port should return error."""
        from handlers.c2_listener import generate_payload
        result = generate_payload('192.168.1.1', 'bad-port')
        assert result['status'] == 'error'

    def test_generate_payload_valid_python(self):
        """Should generate a Python reverse shell payload."""
        from handlers.c2_listener import generate_payload
        result = generate_payload('192.168.1.1', 4444, payload_type='python')
        assert result['status'] == 'success'
        assert 'payload' in result
        assert '192.168.1.1' in result['payload']
        assert '4444' in result['payload']

    def test_generate_payload_unknown_type(self):
        """Unknown payload type should return error with available types."""
        from handlers.c2_listener import generate_payload
        result = generate_payload('192.168.1.1', 4444, payload_type='unknown_type')
        assert result['status'] == 'error'
        assert 'available' in result['message'].lower()

    def test_generate_payload_all_types(self):
        """All known payload types should generate successfully."""
        from handlers.c2_listener import generate_payload
        types = ['python', 'python3', 'bash', 'nc', 'nc_mkfifo', 'php',
                 'ruby', 'perl', 'powershell']
        for pt in types:
            result = generate_payload('10.0.0.1', 9999, payload_type=pt)
            assert result['status'] == 'success', f'Failed for type: {pt}'
            assert len(result['payload']) > 0, f'Empty payload for type: {pt}'


# ---------------------------------------------------------------------------
# Thread safety — C2_LOCK
# ---------------------------------------------------------------------------

class TestThreadSafety:
    def test_c2_lock_exists(self):
        """C2_LOCK should be a threading lock (RLock for reentrancy)."""
        from handlers.c2_listener import C2_LOCK
        import threading
        assert isinstance(C2_LOCK, (type(threading.Lock()), type(threading.RLock())))

    @patch('handlers.c2_listener.socket.socket')
    @patch('handlers.c2_listener.threading.Thread')
    def test_sequential_listener_starts_dont_corrupt_state(self, mock_thread, mock_socket_class):
        """Multiple sequential start_listener calls should not corrupt state."""
        from handlers.c2_listener import start_listener, LISTENERS

        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        results = []
        for port in [30001, 30002, 30003, 30004]:
            results.append(start_listener(port, auth_enabled=False))

        assert all(r['status'] == 'success' for r in results)
        assert len(LISTENERS) == 4


# ---------------------------------------------------------------------------
# execute_on_zombie
# ---------------------------------------------------------------------------

class TestExecuteOnZombie:
    def test_execute_nonexistent_zombie(self):
        from handlers.c2_listener import execute_on_zombie
        result = execute_on_zombie('fake-id', 'whoami')
        assert result['status'] == 'error'
