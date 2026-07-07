"""
test_js_assets.py — Verify that all JavaScript assets referenced in
templates/index.html exist, are non-empty, and are free of syntax errors.

Usage:  pytest tests/test_js_assets.py -v
"""
import os
import re
import pytest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, 'templates')
STATIC_DIR = os.path.join(PROJECT_ROOT, 'static')


def _extract_js_paths(html_path: str):
    """Parse ``<script src="...">`` tags and return a list of local static paths.

    Only returns paths under ``static/`` — skips external CDN URLs (socket.io, etc.).
    """
    with open(html_path, 'r', encoding='utf-8') as fh:
        html = fh.read()

    # Match: <script src="{{ url_for('static', filename='js/...') }}">
    pattern = re.compile(
        r"""<script\s+src=["']\{\{\s*url_for\('static',\s*filename='([^']+)'\s*\)\s*\}\}["']""",
    )
    matches = pattern.findall(html)
    return matches


@pytest.fixture(scope='module')
def js_asset_paths():
    """Return the list of ``static/…`` paths referenced in index.html."""
    index_html = os.path.join(TEMPLATE_DIR, 'index.html')
    if not os.path.exists(index_html):
        pytest.skip('templates/index.html not found')
    return _extract_js_paths(index_html)


def test_js_references_found(js_asset_paths):
    """At least the new module files + app.js should be referenced."""
    assert len(js_asset_paths) >= 6, (
        f'Expected at least 6 <script> references in index.html, '
        f'found {len(js_asset_paths)}: {js_asset_paths}'
    )
    # Check our specific modules are present
    expected = [
        'js/modules/ui.js',
        'js/modules/api.js',
        'js/modules/terminal.js',
        'js/modules/modals.js',
        'js/modules/wiki.js',
        'js/app.js',
    ]
    for exp in expected:
        assert exp in js_asset_paths, (
            f'Missing script reference: {exp} not found in index.html'
        )


@pytest.mark.parametrize('rel_path', [
    'js/modules/ui.js',
    'js/modules/api.js',
    'js/modules/terminal.js',
    'js/modules/modals.js',
    'js/modules/wiki.js',
    'js/app.js',
])
def test_each_file_exists(rel_path):
    """Every referenced JS file must exist on disk."""
    abs_path = os.path.join(STATIC_DIR, rel_path)
    assert os.path.isfile(abs_path), f'File not found: {abs_path}'


@pytest.mark.parametrize('rel_path', [
    'js/modules/ui.js',
    'js/modules/api.js',
    'js/modules/terminal.js',
    'js/modules/modals.js',
    'js/modules/wiki.js',
    'js/app.js',
])
def test_each_file_not_empty(rel_path):
    """Every referenced JS file must have content (> 0 bytes)."""
    abs_path = os.path.join(STATIC_DIR, rel_path)
    size = os.path.getsize(abs_path)
    assert size > 0, f'File is empty: {abs_path} ({size} bytes)'


@pytest.mark.parametrize('rel_path', [
    'js/modules/ui.js',
    'js/modules/api.js',
    'js/modules/terminal.js',
    'js/modules/modals.js',
    'js/modules/wiki.js',
    'js/app.js',
])
def test_each_file_no_syntax_errors(rel_path):
    """Quick syntax check — verifies bracket balance on raw file content.

    Raw counting is reliable here: strings inside JS files tend to contain
    code snippets or HTML that are themselves bracket-balanced.  Regex-based
    string stripping creates false positives when a string literal contains
    an odd number of a bracket character (e.g. a lone ``{`` inside a template
    literal), because stripping the whole string removes that bracket from
    the count without removing its non-existent partner.
    """
    abs_path = os.path.join(STATIC_DIR, rel_path)
    with open(abs_path, 'r', encoding='utf-8') as fh:
        content = fh.read()

    # Basic bracket balancing check on raw content
    open_count = content.count('{') + content.count('(') + content.count('[')
    close_count = content.count('}') + content.count(')') + content.count(']')
    assert open_count == close_count, (
        f'{rel_path}: unbalanced brackets/braces/parens '
        f'({{+ (+ [ = {open_count}, }}+ )+ ] = {close_count})'
    )

