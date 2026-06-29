"""External User Directory Provider Factory.

Handles resolving dependency injection variants of the directory provider.
"""

from __future__ import annotations

from xtv_support.core.container import Container
from xtv_support.services.external_directory.null_provider import NullDirectoryProvider


def build_default_directory_provider(container: Container) -> NullDirectoryProvider:
    """Builds a NullDirectoryProvider for when no configuration exists."""
    return NullDirectoryProvider()
