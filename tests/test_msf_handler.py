"""
Tests for Metasploit Framework Handler — payload list, generation,
msfvenom detection, standalone fallback, RPC status, and generated
payload listing.

Covers ``handlers/msf_handler.py``.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, mock_open

pytestmark = pytest.mark.skipif(
    os.environ.get("CI", "").lower() == "true",
    reason="CI ortamında session-scoped fixture mock'u ile çakışıyor",
)


# ---------------------------------------------------------------------------
# Module-level setup — remove handlers mock
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def _unmock_handlers():
    """Remove the conftest session mock so real handler modules can be imported."""
    if 'handlers' in sys.modules:
        del sys.modules['handlers']


# ---------------------------------------------------------------------------
# get_payload_list
# ---------------------------------------------------------------------------

class TestGetPayloadList:
    def test_get_all_payloads(self):
        """Should return full payload catalog across all platforms."""
        from handlers.msf_handler import get_payload_list
        result = get_payload_list()
        assert result['status'] == 'success'
        assert 'payloads' in result
        assert 'encoders' in result
        # Check key platforms exist
        payloads = result['payloads']
        assert 'windows' in payloads
        assert 'linux' in payloads

    def test_get_payload_list_filtered_by_platform(self):
        """Filtering by platform should only return that platform."""
        from handlers.msf_handler import get_payload_list
        result = get_payload_list(platform='linux')
        assert 'linux' in result['payloads']
        assert 'windows' not in result['payloads']

    def test_encoders_list_not_empty(self):
        """Encoder list should include known encoders."""
        from handlers.msf_handler import get_payload_list
        result = get_payload_list()
        assert len(result['encoders']) > 0
        assert 'none' in result['encoders']
        assert 'x86/shikata_ga_nai' in result['encoders']

    def test_msfvenom_available_field(self):
        """Response should indicate if msfvenom is available."""
        from handlers.msf_handler import get_payload_list
        result = get_payload_list()
        assert 'msfvenom_available' in result
        assert isinstance(result['msfvenom_available'], bool)


# ---------------------------------------------------------------------------
# _detect_msfvenom
# ---------------------------------------------------------------------------

class TestDetectMsfvenom:
    def test_detect_when_installed(self):
        """When msfvenom --help succeeds, should return True."""
        from handlers.msf_handler import _detect_msfvenom
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = b'Usage: msfvenom [options]'
            mock_run.return_value = mock_result
            assert _detect_msfvenom() is True

    def test_detect_when_not_installed(self):
        """When msfvenom is not found, should return False."""
        from handlers.msf_handler import _detect_msfvenom
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            # Also mock os.path.exists to return False for all paths
            with patch('os.path.exists', return_value=False):
                assert _detect_msfvenom() is False


# ---------------------------------------------------------------------------
# generate_payload
# ---------------------------------------------------------------------------

class TestGeneratePayload:
    def test_generate_without_msfvenom_returns_standalone(self):
        """When msfvenom is not available, standalone payload should be returned."""
        from handlers.msf_handler import generate_payload
        with patch('handlers.msf_handler._detect_msfvenom', return_value=False):
            result = generate_payload('linux', '10.0.0.1', 4444)
            assert result['status'] == 'success'
            assert result['standalone'] is True

    def test_generate_unknown_platform_returns_standalone(self):
        """Unknown platform should fall back to linux standalone."""
        from handlers.msf_handler import generate_payload
        with patch('handlers.msf_handler._detect_msfvenom', return_value=False):
            result = generate_payload('unknown_platform', '10.0.0.1', 4444)
            assert result['status'] == 'success'

    @patch('handlers.msf_handler._detect_msfvenom', return_value=True)
    @patch('subprocess.run')
    def test_generate_with_msfvenom_success(self, mock_run, _mock_detect):
        """When msfvenom is available and succeeds, return payload info."""
        from handlers.msf_handler import generate_payload
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with patch('os.path.exists', return_value=True):
            with patch('os.path.getsize', return_value=12345):
                with patch('core.db.log_payload'):  # log_payload comes from core.db
                    result = generate_payload('linux', '10.0.0.1', 4444,
                                              payload_type='linux/x64/shell/reverse_tcp')
                    assert result['status'] == 'success'
                    assert result['platform'] == 'linux'
                    assert 'size_bytes' in result

    @patch('handlers.msf_handler._detect_msfvenom', return_value=True)
    @patch('subprocess.run')
    def test_generate_msfvenom_timeout(self, mock_run, _mock_detect):
        """When msfvenom times out, should return error."""
        from handlers.msf_handler import generate_payload
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(['msfvenom'], 60)
        result = generate_payload('windows', '10.0.0.1', 4444)
        assert result['status'] == 'error'
        assert 'timed out' in result['message'].lower()


# ---------------------------------------------------------------------------
# _build_standalone_generator
# ---------------------------------------------------------------------------

class TestStandaloneGenerator:
    def test_windows_standalone(self):
        """Should generate PS1 payload for Windows."""
        from handlers.msf_handler import _build_standalone_generator
        with patch('builtins.open', mock_open()) as mock_f:
            with patch('os.makedirs'):
                with patch('os.path.exists', return_value=True):
                    result = _build_standalone_generator('windows', '10.0.0.1', 4444)
                    assert result['status'] == 'success'
                    assert result['standalone'] is True

    def test_linux_standalone(self):
        """Should generate bash reverse shell for Linux."""
        from handlers.msf_handler import _build_standalone_generator
        with patch('builtins.open', mock_open()) as mock_f:
            with patch('os.makedirs'):
                with patch('os.path.exists', return_value=True):
                    result = _build_standalone_generator('linux', '10.0.0.1', 4444)
                    assert result['status'] == 'success'

    def test_android_standalone(self):
        """Should generate instructions for Android."""
        from handlers.msf_handler import _build_standalone_generator
        with patch('builtins.open', mock_open()) as mock_f:
            with patch('os.makedirs'):
                with patch('os.path.exists', return_value=True):
                    result = _build_standalone_generator('android', '10.0.0.1', 4444)
                    assert result['status'] == 'success'


# ---------------------------------------------------------------------------
# get_msf_rpc_status
# ---------------------------------------------------------------------------

class TestMsfRpcStatus:
    def test_rpc_status_returns_dict(self):
        from handlers.msf_handler import get_msf_rpc_status
        result = get_msf_rpc_status()
        assert result['status'] == 'success'
        assert 'msfrpcd_available' in result
        assert 'msfvenom_available' in result
        assert isinstance(result['msfrpcd_available'], bool)


# ---------------------------------------------------------------------------
# list_generated_payloads
# ---------------------------------------------------------------------------

class TestListGeneratedPayloads:
    def test_list_payloads_returns_list(self):
        """Should return list of generated payload files."""
        from handlers.msf_handler import list_generated_payloads
        with patch('os.listdir', return_value=['payload_test.exe', 'payload_test.elf']):
            with patch('os.path.isfile', return_value=True):
                with patch('os.path.getsize', return_value=100):
                    with patch('os.path.getmtime', return_value=1234567890.0):
                        with patch('os.path.exists', return_value=True):
                            with patch('os.makedirs'):
                                result = list_generated_payloads()
        assert result['status'] == 'success'
        assert isinstance(result['payloads'], list)

    def test_list_empty_directory(self):
        """Empty directory should return empty list."""
        from handlers.msf_handler import list_generated_payloads
        with patch('os.listdir', return_value=[]):
            with patch('os.path.exists', return_value=True):
                with patch('os.makedirs'):
                    result = list_generated_payloads()
        assert result['status'] == 'success'
        assert result['payloads'] == []


# ---------------------------------------------------------------------------
# MSF_PAYLOADS data structure
# ---------------------------------------------------------------------------

class TestMsfPayloadsStructure:
    def test_windows_payloads_have_x64_x86(self):
        from handlers.msf_handler import MSF_PAYLOADS
        assert 'x64' in MSF_PAYLOADS['windows']
        assert 'x86' in MSF_PAYLOADS['windows']
        assert len(MSF_PAYLOADS['windows']['x64']) > 0

    def test_linux_payloads_have_x64_x86(self):
        from handlers.msf_handler import MSF_PAYLOADS
        assert 'x64' in MSF_PAYLOADS['linux']
        assert 'x86' in MSF_PAYLOADS['linux']

    def test_all_platform_payloads_are_strings(self):
        from handlers.msf_handler import MSF_PAYLOADS
        for platform, archs in MSF_PAYLOADS.items():
            for arch, payloads in archs.items():
                for p in payloads:
                    assert isinstance(p, str)
                    assert len(p) > 0

    def test_encoders_are_valid(self):
        from handlers.msf_handler import ENCODERS
        assert 'none' in ENCODERS
        assert len(ENCODERS) >= 3
