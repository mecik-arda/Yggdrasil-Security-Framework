# Backward-compatible re-export of login_required.
# The canonical definition lives in core.__init__ so that
# ``from core import login_required`` works without extra imports.
from core import login_required  # noqa: F401