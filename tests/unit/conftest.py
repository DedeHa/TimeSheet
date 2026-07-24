"""Unit-level fixtures."""

import logging

import pytest


@pytest.fixture
def clean_root_logger():
    """Clear root logging handlers around a test, then restore them.

    ``logging.basicConfig`` is a no-op when the root logger already has
    handlers, so the ``configure_logging`` tests need a clean slate to observe
    that a handler was actually installed.
    """
    root_logger = logging.getLogger()
    saved = root_logger.handlers[:]
    for handler in saved:
        root_logger.removeHandler(handler)
    yield root_logger
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    for handler in saved:
        root_logger.addHandler(handler)
