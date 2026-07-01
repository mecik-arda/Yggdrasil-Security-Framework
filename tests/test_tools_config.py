"""
Tests for tools_config.py — structural integrity of the TOOLS_CONFIG dictionary.
"""
import pytest

from tools_config import TOOLS_CONFIG

VALID_TYPES = {'cli', 'gui', 'script', 'custom_html', 'custom_script'}
VALID_CATEGORIES = {
    'nmap_scans', 'passive_recon', 'dns_subdomain', 'active_scanning',
    'vulnerability', 'ai_ops', 'erebus_scanner', 'kali_ghost',
    'adv_syn', 'java_sniffer', 'system_ops', 'snoopdork',
    'packet_injector', 'mimir_scanner', 'bifrost_gateway',
    'my_runes', 'fenrir',
}


class TestToolsConfigStructure:
    def test_is_non_empty_dict(self):
        assert isinstance(TOOLS_CONFIG, dict)
        assert len(TOOLS_CONFIG) > 0

    @pytest.mark.parametrize('tool_key,tool_def', [
        (k, v) for k, v in TOOLS_CONFIG.items()
    ])
    def test_every_tool_has_name(self, tool_key, tool_def):
        assert 'name' in tool_def, f"{tool_key} missing 'name'"

    @pytest.mark.parametrize('tool_key,tool_def', [
        (k, v) for k, v in TOOLS_CONFIG.items()
    ])
    def test_every_tool_has_type(self, tool_key, tool_def):
        assert 'type' in tool_def, f"{tool_key} missing 'type'"
        assert tool_def['type'] in VALID_TYPES, \
            f"{tool_key} has invalid type '{tool_def['type']}'"

    @pytest.mark.parametrize('tool_key,tool_def', [
        (k, v) for k, v in TOOLS_CONFIG.items()
    ])
    def test_every_tool_has_category(self, tool_key, tool_def):
        assert 'category' in tool_def, f"{tool_key} missing 'category'"

    def test_cli_tools_have_cmd(self):
        cli_tools = [(k, v) for k, v in TOOLS_CONFIG.items() if v.get('type') == 'cli']
        for key, tool in cli_tools:
            assert 'cmd' in tool, f"CLI tool '{key}' missing 'cmd'"
            assert isinstance(tool['cmd'], list), f"CLI tool '{key}' cmd is not a list"

    def test_cli_tools_have_bin(self):
        cli_tools = [(k, v) for k, v in TOOLS_CONFIG.items() if v.get('type') == 'cli']
        for key, tool in cli_tools:
            assert 'bin' in tool, f"CLI tool '{key}' missing 'bin'"

    def test_script_tools_have_cmd(self):
        script_tools = [(k, v) for k, v in TOOLS_CONFIG.items() if v.get('type') == 'script']
        for key, tool in script_tools:
            assert 'cmd' in tool, f"Script tool '{key}' missing 'cmd'"

    def test_custom_tools_have_handler(self):
        custom_tools = [
            (k, v) for k, v in TOOLS_CONFIG.items()
            if v.get('type') in ('custom_script', 'custom_html')
        ]
        for key, tool in custom_tools:
            assert 'handler' in tool, f"Custom tool '{key}' missing 'handler'"

    def test_tool_keys_are_unique(self):
        assert len(TOOLS_CONFIG) == len(set(TOOLS_CONFIG.keys()))
