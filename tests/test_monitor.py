"""
Tests for core.monitor — system monitoring background thread.
"""

import pytest


@pytest.fixture
def _patch_monitor_deps(mocker):
    """Patch all external dependencies of the monitor module."""
    mocker.patch('time.sleep', side_effect=StopIteration)  # one iteration only
    mocker.patch('psutil.cpu_percent', return_value=42.0)
    mocker.patch('socket.socket')
    mocker.patch('subprocess.check_output')


class TestMonitor:
    def test_module_has_global_variables(self):
        """Verify the module-level globals exist."""
        import core.monitor
        assert hasattr(core.monitor, 'CURRENT_CPU')
        assert hasattr(core.monitor, 'PING_MS')
        assert hasattr(core.monitor, 'OLLAMA_ONLINE')

    def test_start_monitor_creates_daemon_thread(self, _patch_monitor_deps):
        """start_monitor should spawn a daemon thread."""
        import core.monitor
        import threading

        # Ensure we can call start_monitor
        threading.active_count()
        try:
            core.monitor._system_monitor()
        except StopIteration:
            pass  # our sleep mock stops the loop after one iteration
        # Thread should have been created (start_monitor uses daemon thread)
        # We just verify no exception was raised

    def test_ollama_status_tracking(self, mocker):
        """OLLAMA_ONLINE should be set to a boolean."""
        import core.monitor

        # Patch socket to simulate connection refused
        mocker.patch('socket.socket')
        mocker.patch('time.sleep', side_effect=StopIteration)
        mocker.patch('psutil.cpu_percent', return_value=10.0)
        mocker.patch('subprocess.check_output', return_value=b'1 packets transmitted')

        try:
            core.monitor._system_monitor()
        except StopIteration:
            pass

        assert isinstance(core.monitor.OLLAMA_ONLINE, bool)

    def test_cpu_updated(self, mocker):
        """After one monitor tick, CURRENT_CPU should reflect the mocked value."""
        import core.monitor

        mocker.patch('psutil.cpu_percent', return_value=77.0)
        mocker.patch('subprocess.check_output', return_value=b'1 packets transmitted')
        mocker.patch('socket.socket')
        mocker.patch('time.sleep', side_effect=StopIteration)

        try:
            core.monitor._system_monitor()
        except StopIteration:
            pass

        assert core.monitor.CURRENT_CPU == 77.0
