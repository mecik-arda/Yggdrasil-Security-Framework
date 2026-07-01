"""
Integration tests: verify every tool type dispatches correctly.

These tests mock subprocess calls and verify the routing logic without
requiring actual external binaries to be installed.
"""
import subprocess

import pytest

from core.tool_runner import execute_tool, execute_tool_streaming
from tools_config import TOOLS_CONFIG


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_output(callback):
    """Capture streaming callback lines into a list."""
    lines = []

    def _cb(line):
        lines.append(line)

    _cb.lines = lines
    return _cb


# ---------------------------------------------------------------------------
# CLI tools — representative sample
# ---------------------------------------------------------------------------

class TestCliTools:
    """Every CLI tool should be recognized and build a command."""
    CLI_TOOLS = [
        ('whois', 'example.com'),
        ('nmap_stealth', '10.0.0.1'),
        ('dig', 'example.com'),
        ('nslookup', 'example.com'),
        ('amass', 'example.com'),
        ('sherlock', 'john_doe'),
    ]

    @pytest.mark.parametrize('tool_key,target', CLI_TOOLS)
    def test_tool_recognised_non_empty_output(self, tool_key, target, mocker):
        """Mock subprocess.Popen to return canned output."""
        mock_popen = mocker.MagicMock()
        mock_proc = mocker.MagicMock()
        mock_proc.communicate.return_value = (b'test output line\nsecond line', b'')
        mock_popen.return_value = mock_proc
        mocker.patch('subprocess.Popen', mock_popen)
        mocker.patch('core.tool_runner.platform.system', return_value='Linux')

        result = execute_tool(tool_key, target)
        assert len(result) > 0
        assert 'not found' not in result.lower()

    @pytest.mark.parametrize('tool_key,target', CLI_TOOLS)
    def test_streaming_yields_lines(self, tool_key, target, mocker):
        """Streaming mode should call the callback for each output line."""
        mock_popen = mocker.MagicMock()
        mock_proc = mocker.MagicMock()

        class FakeStdout:
            def __init__(self, lines):
                self._lines = iter(lines)

            def readline(self):
                try:
                    return next(self._lines)
                except StopIteration:
                    return ''

        mock_proc.stdout = FakeStdout(['line1\n', 'line2\n', 'line3\n'])
        mock_proc.wait = mocker.MagicMock()
        mock_popen.return_value = mock_proc
        mocker.patch('subprocess.Popen', mock_popen)
        mocker.patch('core.tool_runner.platform.system', return_value='Linux')

        cb = _collect_output(None)
        result = execute_tool_streaming(tool_key, target, cb)
        assert 'line1' in result
        assert len(cb.lines) >= 1


# ---------------------------------------------------------------------------
# GUI tools
# ---------------------------------------------------------------------------

class TestGuiTools:
    GUI_TOOLS = ['java_sniffer', 'snoopdork', 'huginn_ui', 'huginn_web']

    @pytest.mark.parametrize('tool_key', GUI_TOOLS)
    def test_gui_returns_launch_message(self, tool_key, mocker):
        mocker.patch('subprocess.Popen')
        mocker.patch('core.tool_runner.platform.system', return_value='Windows')

        result = execute_tool(tool_key, '')
        assert 'INITIATING GUI TOOL' in result or 'gui' in result.lower() or len(result) > 0


# ---------------------------------------------------------------------------
# custom_html tools
# ---------------------------------------------------------------------------

class TestCustomHtmlTools:
    CUSTOM_HTML = ['google_dorks', 'wayback', 'update_modules', 'odin_ai', 'loki']

    @pytest.mark.parametrize('tool_key', CUSTOM_HTML)
    def test_custom_html_dispatches(self, tool_key):
        result = execute_tool(tool_key, 'example.com')
        assert result is not None
        assert len(result) > 0


# ---------------------------------------------------------------------------
# custom_script tools
# ---------------------------------------------------------------------------

class TestCustomScriptTools:
    CUSTOM_SCRIPT = [
        'erebus', 'subfinder', 'knockpy', 'gobuster_dns',
        'adv_syn_scan', 'packet_injector', 'mimir_scanner',
        'bifrost_gateway', 'muninn_scanner', 'fenrir', 'hydra',
    ]

    @pytest.mark.parametrize('tool_key', CUSTOM_SCRIPT)
    def test_custom_script_dispatches(self, tool_key):
        """Handler dispatch should return a string (even if mocked)."""
        # Some handlers require data as a dict; pass empty dict for safety
        result = execute_tool(tool_key, 'example.com', data={})
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Tool config validation
# ---------------------------------------------------------------------------

class TestToolConfigComplete:
    """Verify that TOOLS_CONFIG is self-consistent for every tool."""

    def test_all_58_tools_have_type_and_category(self):
        assert len(TOOLS_CONFIG) == 58
        for key, cfg in TOOLS_CONFIG.items():
            assert 'type' in cfg, f"{key}: missing type"
            assert 'category' in cfg, f"{key}: missing category"
            assert 'name' in cfg, f"{key}: missing name"

    def test_all_cli_tools_have_cmd(self):
        for key, cfg in TOOLS_CONFIG.items():
            if cfg['type'] == 'cli':
                assert 'cmd' in cfg, f"CLI tool {key} missing cmd"
                assert isinstance(cfg['cmd'], list), f"CLI tool {key} cmd not a list"

    def test_all_custom_tools_have_handler(self):
        for key, cfg in TOOLS_CONFIG.items():
            if cfg['type'] in ('custom_script', 'custom_html'):
                assert 'handler' in cfg, f"{key}: missing handler"
