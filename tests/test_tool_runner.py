"""
Tests for core.tool_runner — tool execution, WSL helpers, and dispatch.
"""
import subprocess



class TestGetWslDistros:
    def test_returns_empty_on_error(self, mocker):
        mocker.patch('subprocess.check_output', side_effect=subprocess.CalledProcessError(1, 'wsl'))
        mocker.patch('core.tool_runner.platform.system', return_value='Windows')
        from core.tool_runner import get_wsl_distros
        assert get_wsl_distros() == []

    def test_returns_empty_on_non_windows(self, mocker):
        mocker.patch('core.tool_runner.platform.system', return_value='Linux')
        from core.tool_runner import get_wsl_distros
        assert get_wsl_distros() == []

    def test_parses_distro_list(self, mocker):
        mocker.patch('core.tool_runner.platform.system', return_value='Windows')
        mocker.patch(
            'subprocess.check_output',
            return_value='Ubuntu-22.04\r\nDebian\r\n'.encode('utf-16-le'),
        )
        from core.tool_runner import get_wsl_distros
        result = get_wsl_distros()
        assert 'Ubuntu-22.04' in result
        assert 'Debian' in result
        assert len(result) == 2


class TestGetPreferredWsl:
    def test_no_config_uses_first_distro(self, mocker, tmp_path):
        mocker.patch('core.tool_runner.platform.system', return_value='Windows')
        mocker.patch(
            'subprocess.check_output',
            return_value='Ubuntu\nDebian\n'.encode('utf-16-le'),
        )
        mocker.patch('core.tool_runner.os.path.exists', return_value=False)
        from core.tool_runner import get_preferred_wsl
        distro = get_preferred_wsl()
        assert distro == 'Ubuntu'

    def test_with_config_uses_configured_distro(self, mocker, tmp_path):
        mocker.patch('core.tool_runner.platform.system', return_value='Windows')
        mocker.patch(
            'subprocess.check_output',
            return_value='Ubuntu\nDebian\n'.encode('utf-16-le'),
        )
        # Make os.path.exists return True and mock open to return config JSON
        mocker.patch('core.tool_runner.os.path.exists', return_value=True)
        mocker.patch(
            'builtins.open',
            mocker.mock_open(read_data='{"wsl_distro": "Debian"}'),
        )
        from core.tool_runner import get_preferred_wsl
        distro = get_preferred_wsl()
        assert distro == 'Debian'

    def test_no_distros_returns_none(self, mocker):
        mocker.patch('core.tool_runner.platform.system', return_value='Windows')
        mocker.patch('subprocess.check_output', side_effect=Exception('no WSL'))
        mocker.patch('core.tool_runner.os.path.exists', return_value=False)
        from core.tool_runner import get_preferred_wsl
        assert get_preferred_wsl() is None


class TestExecuteTool:
    def test_unknown_tool(self):
        from core.tool_runner import execute_tool
        result = execute_tool('nonexistent_tool_key', 'target')
        assert 'not found' in result.lower()

    def test_gui_tool_windows(self, mocker):
        mock_popen = mocker.patch('subprocess.Popen')
        mocker.patch('core.tool_runner.platform.system', return_value='Windows')
        from core.tool_runner import execute_tool
        result = execute_tool('java_sniffer', '')
        assert 'INITIATING GUI TOOL' in result
        assert mock_popen.called

    def test_cli_tool_success(self, mocker):
        mock_popen = mocker.MagicMock()
        mock_process = mocker.MagicMock()
        mock_process.communicate.return_value = (b'scan result', b'')
        mock_popen.return_value = mock_process
        mocker.patch('subprocess.Popen', mock_popen)
        mocker.patch('core.tool_runner.platform.system', return_value='Linux')

        from core.tool_runner import execute_tool
        result = execute_tool('whois', 'example.com')
        assert 'scan result' in result

    def test_cli_tool_timeout(self, mocker):
        mock_popen = mocker.MagicMock()
        mock_process = mocker.MagicMock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired('cmd', 120)
        mock_popen.return_value = mock_process
        mocker.patch('subprocess.Popen', mock_popen)
        mocker.patch('core.tool_runner.platform.system', return_value='Linux')

        from core.tool_runner import execute_tool
        result = execute_tool('whois', 'example.com')
        assert 'TIMEOUT' in result

    def test_cli_tool_wsl_fallback(self, mocker):
        """Windows + Linux-only tool should use WSL."""
        mock_popen = mocker.MagicMock()
        mock_process = mocker.MagicMock()
        mock_process.communicate.return_value = (b'wsl output', b'')
        mock_popen.return_value = mock_process
        mocker.patch('subprocess.Popen', mock_popen)
        mocker.patch('core.tool_runner.platform.system', return_value='Windows')
        # Mock get_preferred_wsl to return a distro
        mocker.patch('core.tool_runner.get_preferred_wsl', return_value='Ubuntu')

        from core.tool_runner import execute_tool
        result = execute_tool('dnsenum', 'example.com')
        # The command should be prefixed with wsl.exe
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == 'wsl.exe'
        assert 'wsl output' in result

    def test_custom_script_dispatch(self, mocker):
        mocker.patch('core.tool_runner.dispatch_handler', return_value='custom result')
        from core.tool_runner import execute_tool
        result = execute_tool('erebus', 'target')
        assert result == 'custom result'
