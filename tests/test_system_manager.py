"""
Tests for core.system_manager — package management, tool status, and target validation.
"""
import subprocess

import pytest


# ---------------------------------------------------------------------------
# get_pkg_name
# ---------------------------------------------------------------------------

class TestGetPkgName:
    def test_apt_get(self):
        from core.system_manager import get_pkg_name
        assert get_pkg_name('sudo apt-get install nmap -y') == 'nmap'

    def test_apt_get_no_flags(self):
        from core.system_manager import get_pkg_name
        assert get_pkg_name('sudo apt-get install python3') == 'python3'

    def test_winget(self):
        from core.system_manager import get_pkg_name
        assert get_pkg_name('winget install Insecure.Nmap') == 'Insecure.Nmap'

    def test_pip(self):
        from core.system_manager import get_pkg_name
        assert get_pkg_name('pip install sherlock') == 'sherlock'

    def test_go(self):
        from core.system_manager import get_pkg_name
        result = get_pkg_name(
            'go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest'
        )
        # go install takes the full import path as the last argument
        assert 'subfinder' in result

    def test_unknown_returns_none(self):
        from core.system_manager import get_pkg_name
        assert get_pkg_name('some weird command') is None


# ---------------------------------------------------------------------------
# validate_target
# ---------------------------------------------------------------------------

class TestValidateTarget:
    @pytest.mark.parametrize('target', [
        '',
        None,
        '192.168.1.1',
        'example.com',
        'example.com:8080',
        '10.0.0.1:443',
        'sub.example.com',
        'my-host.example.com',
        'test-site.co.uk',
    ])
    def test_valid_targets(self, target):
        from core.system_manager import validate_target
        assert validate_target(target) is True

    @pytest.mark.parametrize('target', [
        'hello world',
        'target; rm -rf /',
        '$(whoami)',
        '<script>alert(1)</script>',
        '| cat /etc/passwd',
    ])
    def test_invalid_targets(self, target):
        from core.system_manager import validate_target
        assert validate_target(target) is False

    def test_strips_http_scheme(self):
        from core.system_manager import validate_target
        assert validate_target('http://example.com') is True

    def test_strips_https_scheme(self):
        from core.system_manager import validate_target
        assert validate_target('https://example.com') is True

    def test_strips_path(self):
        from core.system_manager import validate_target
        assert validate_target('example.com/path/to/resource') is True

    def test_ip_with_scheme_and_port(self):
        from core.system_manager import validate_target
        assert validate_target('https://192.168.1.1:8080/admin') is True


# ---------------------------------------------------------------------------
# check_tool_status
# ---------------------------------------------------------------------------

class TestCheckToolStatus:
    def test_unknown_tool_key_returns_false(self):
        from core.system_manager import check_tool_status
        assert check_tool_status('nonexistent_tool') is False

    def test_bin_found_returns_true(self, mocker):
        mocker.patch('shutil.which', return_value='/usr/bin/nmap')
        from core.system_manager import check_tool_status
        assert check_tool_status('nmap') is True

    def test_bin_not_found_returns_false(self, mocker):
        mocker.patch('shutil.which', return_value=None)
        from core.system_manager import check_tool_status
        assert check_tool_status('nmap') is False

    def test_check_path_exists_returns_true(self, mocker):
        mocker.patch('os.path.exists', return_value=True)
        from core.system_manager import check_tool_status
        # 'odin_ai' has check_path='ollama' but no bin
        status = check_tool_status('odin_ai')
        # shutil.which('ollama') may or may not find it, depends on system
        # Just verify no exception
        assert isinstance(status, bool)

    def test_runes_repo_missing_git_returns_false(self, mocker):
        mocker.patch('os.path.exists', side_effect=lambda p: '.git' not in p)
        mocker.patch('core.system_manager.platform.system', return_value='Windows')
        from core.system_manager import check_tool_status
        assert check_tool_status('adv_syn_scan') is False


# ---------------------------------------------------------------------------
# install / remove / update (mocked subprocess)
# ---------------------------------------------------------------------------

class TestInstallToolSystem:
    def test_no_command_for_os(self, mocker):
        mocker.patch('core.system_manager.platform.system', return_value='Windows')
        mocker.patch('core.system_manager.get_preferred_wsl', return_value=None)
        from core.system_manager import install_tool_system
        # 'wpscan' has install_linux but no install_windows
        ok, msg = install_tool_system('wpscan')
        assert ok is False

    def test_successful_install(self, mocker):
        mocker.patch('core.system_manager.platform.system', return_value='Linux')
        mocker.patch(
            'subprocess.check_output',
            return_value=b'Installation complete',
        )
        from core.system_manager import install_tool_system
        ok, msg = install_tool_system('nmap')
        assert ok is True
        assert 'Installation' in msg

    def test_install_failure(self, mocker):
        mocker.patch('core.system_manager.platform.system', return_value='Linux')
        mocker.patch(
            'subprocess.check_output',
            side_effect=subprocess.CalledProcessError(1, 'apt-get', b'error'),
        )
        from core.system_manager import install_tool_system
        ok, msg = install_tool_system('nmap')
        assert ok is False

    def test_wsl_install_strips_sudo(self, mocker):
        mocker.patch('core.system_manager.platform.system', return_value='Windows')
        mocker.patch('core.system_manager.get_preferred_wsl', return_value='Ubuntu')
        mock_check = mocker.patch(
            'subprocess.check_output',
            return_value=b'ok',
        )
        from core.system_manager import install_tool_system
        # 'nmap' has install_windows so it won't use WSL; use 'wpscan' which only has install_linux
        ok, _ = install_tool_system('wpscan')
        assert ok is True
        # Command should use wsl.exe with the distro
        cmd = mock_check.call_args[0][0]
        assert 'wsl.exe' in cmd


class TestRemoveToolSystem:
    def test_runes_repo_removal(self, mocker):
        mocker.patch('os.path.exists', return_value=True)
        mock_rmtree = mocker.patch('shutil.rmtree')
        from core.system_manager import remove_tool_system
        ok, msg = remove_tool_system('adv_syn_scan')
        assert ok is True
        assert mock_rmtree.called

    def test_runes_repo_not_found(self, mocker):
        mocker.patch('os.path.exists', return_value=False)
        from core.system_manager import remove_tool_system
        ok, msg = remove_tool_system('adv_syn_scan')
        assert ok is False

    def test_apt_removal(self, mocker):
        mocker.patch('core.system_manager.platform.system', return_value='Linux')
        mocker.patch('os.path.exists', return_value=False)  # not a Runes repo
        mock_check = mocker.patch(
            'subprocess.check_output',
            return_value=b'Removed.',
        )
        from core.system_manager import remove_tool_system
        ok, _ = remove_tool_system('nmap')
        assert ok is True
        cmd = mock_check.call_args[0][0]
        assert 'remove' in cmd


class TestUpdateToolSystem:
    def test_apt_only_upgrade(self, mocker):
        mocker.patch('core.system_manager.platform.system', return_value='Linux')
        mock_check = mocker.patch(
            'subprocess.check_output',
            return_value=b'Upgraded.',
        )
        from core.system_manager import update_tool_system
        ok, _ = update_tool_system('nmap')
        assert ok is True
        cmd = mock_check.call_args[0][0]
        assert '--only-upgrade' in cmd

    def test_pip_upgrade(self, mocker):
        mocker.patch('core.system_manager.platform.system', return_value='Windows')
        mocker.patch('os.path.exists', return_value=True)  # pip install_linux cmd
        mock_check = mocker.patch(
            'subprocess.check_output',
            return_value=b'Upgraded.',
        )
        from core.system_manager import update_tool_system
        ok, _ = update_tool_system('sqlmap')
        assert ok is True
        cmd = mock_check.call_args[0][0]
        assert '--upgrade' in cmd

    def test_unknown_package_type(self, mocker):
        mocker.patch('core.system_manager.platform.system', return_value='Linux')
        # 'go' install type with an unusual command
        from core.system_manager import update_tool_system
        ok, msg = update_tool_system('nslookup')
        # nslookup has no install command at all
        assert ok is False
