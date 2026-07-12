try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    limiter = Limiter(
        get_remote_address,
        default_limits=["200 per minute", "50 per second"],
        storage_uri="memory://",
    )
except ImportError:
    limiter = None
