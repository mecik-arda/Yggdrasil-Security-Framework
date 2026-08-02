"""Pytest configuration — ensures BEACON_API_KEY is always set for tests."""
import os
import sys

# Ensure the project root is on the path so 'yggapp' can be imported
_src = os.path.dirname(os.path.abspath(__file__))
if _src not in sys.path:
    sys.path.insert(0, _src)

# Beacon key must be set before routes/beacon_routes.py is imported
if not os.environ.get('BEACON_API_KEY'):
    os.environ['BEACON_API_KEY'] = 'pytest-beacon-key-32-chars-long!!'

if not os.environ.get('SECRET_KEY'):
    os.environ['SECRET_KEY'] = 'pytest-secret-key-32-chars-long!!'

if not os.environ.get('ADMIN_PASSWORD'):
    os.environ['ADMIN_PASSWORD'] = 'pytest-admin-pass'