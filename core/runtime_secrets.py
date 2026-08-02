import os
import secrets

from cryptography.fernet import Fernet
from dotenv import load_dotenv, set_key


ENV_FILE = ".env"


def _persist_secret(name, value):
    set_key(ENV_FILE, name, value)
    os.environ[name] = value
    return value


def get_or_create_secret(name, byte_length=32):
    load_dotenv()
    existing_value = os.environ.get(name)
    if existing_value:
        return existing_value
    if os.environ.get("YGG_DISABLE_SECRET_GENERATION") == "1":
        raise RuntimeError(f"Required secret is missing: {name}")
    return _persist_secret(name, secrets.token_urlsafe(byte_length))


def get_or_create_fernet_key(name="BEACON_ENCRYPTION_KEY"):
    load_dotenv()
    existing_value = os.environ.get(name)
    if existing_value:
        Fernet(existing_value.encode("ascii"))
        return existing_value
    if os.environ.get("YGG_DISABLE_SECRET_GENERATION") == "1":
        raise RuntimeError(f"Required secret is missing: {name}")
    return _persist_secret(name, Fernet.generate_key().decode("ascii"))


def initialize_runtime_secrets():
    return {
        "SECRET_KEY": get_or_create_secret("SECRET_KEY", 48),
        "ADMIN_PASSWORD": get_or_create_secret("ADMIN_PASSWORD", 24),
        "BEACON_API_KEY": get_or_create_secret("BEACON_API_KEY", 48),
        "BEACON_ENCRYPTION_KEY": get_or_create_fernet_key(),
    }
