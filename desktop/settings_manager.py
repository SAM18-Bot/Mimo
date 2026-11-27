"""Compatibility import for existing desktop clients."""
import sys

from server.modules import settings_manager

sys.modules[__name__] = settings_manager
