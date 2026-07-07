"""
Sleipnir Scanner Handler — Yggdrasil Integration
Dispatches XSS injection scans via ``Runes/sleipnir-scanner/sleipnir.py``.
Handles git-clone on first run and git-pull for updates.
"""
import subprocess
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCANNER_DIR = os.path.join(BASE_DIR, 'Runes', 'sleipnir-scanner')
SCANNER_SCRIPT = os.path.join(SCANNER_DIR, 'sleipnir.py')
REPO_URL = 'https://github.com/mecik-arda/Sleipnir-Scanner'


def _ensure_scanner_available():
    """Clone the Sleipnir repo if missing; pull if already cloned."""
    if not os.path.isdir(SCANNER_DIR):
        print('[SLEIPNIR] Cloning scanner repository...', flush=True)
        try:
            subprocess.check_output(
                ['git', 'clone', REPO_URL, SCANNER_DIR],
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            print('[SLEIPNIR] Clone complete.', flush=True)
        except subprocess.CalledProcessError as e:
            # Repo may not exist yet — create minimal stub directory
            os.makedirs(SCANNER_DIR, exist_ok=True)
            print(f'[SLEIPNIR] Clone unavailable ({e}). Using local stub.', flush=True)
        except FileNotFoundError:
            os.makedirs(SCANNER_DIR, exist_ok=True)
            print('[SLEIPNIR] git not found. Using local scanner.', flush=True)
        return

    # Already exists — try to pull updates
    git_dir = os.path.join(SCANNER_DIR, '.git')
    if os.path.isdir(git_dir):
        try:
            subprocess.check_output(
                ['git', 'pull'],
                cwd=SCANNER_DIR,
                stderr=subprocess.STDOUT,
                timeout=30,
            )
        except Exception:
            pass  # Non-fatal; proceed with current version


def handle_sleipnir_scan(target, data, output_callback=None):
    """Yggdrasil handler entry-point.

    Parameters
    ----------
    target : str
        The target URL to scan.
    data : dict | None
        Form fields from the modal: mode, profile, headers, threads.
    output_callback : callable | None
        If provided, called with each output line for real-time streaming.

    Returns
    -------
    str — full scan output.
    """
    if not target or target.lower() == 'none':
        return '>> ERROR: Target URL is required for Sleipnir Scanner.'

    # Ensure scanner directory exists
    _ensure_scanner_available()

    if not os.path.isfile(SCANNER_SCRIPT):
        return (
            f'>> ERROR: Sleipnir scanner script not found at {SCANNER_SCRIPT}.\n'
            f'>> The scanner repository could not be cloned automatically.\n'
            f'>> Please manually clone: git clone {REPO_URL} Runes/sleipnir-scanner'
        )

    if data is None:
        data = {}

    mode = data.get('sleipnir_mode', 'auto-query')
    profile = data.get('sleipnir_profile', 'all')
    threads = data.get('sleipnir_threads', '3')
    headers_raw = data.get('sleipnir_headers', '')

    # Build command
    cmd = [
        sys.executable, SCANNER_SCRIPT,
        '-u', str(target),
        '-m', mode,
        '-p', profile,
        '-t', str(threads),
    ]

    # Parse custom headers
    if headers_raw and headers_raw.strip():
        for h in headers_raw.strip().split('\n'):
            h = h.strip()
            if h:
                cmd.extend(['-H', h])

    # Run with real-time streaming
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            env=env,
        )

        output_lines = []
        for line in iter(process.stdout.readline, ''):
            if line:
                line = line.rstrip('\n\r')
                output_lines.append(line)
                if output_callback:
                    output_callback(line)

        process.wait(timeout=600)
        return '\n'.join(output_lines) if output_lines else '[SLEIPNIR] Scan produced no output.'

    except subprocess.TimeoutExpired:
        process.kill()
        msg = 'TIMEOUT: Sleipnir scan exceeded 10 minutes.'
        if output_callback:
            output_callback(msg)
        return msg
    except Exception as e:
        msg = f'>> ERROR running Sleipnir: {str(e)}'
        if output_callback:
            output_callback(msg)
        return msg
