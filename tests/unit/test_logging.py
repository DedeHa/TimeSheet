"""Unit tests for configure_logging.

Each test uses the ``clean_root_logger`` fixture so that
``logging.basicConfig`` actually installs a handler (it is a no-op when the
root logger already has handlers).
"""

import pytest

from src.TimeSheetAlgo import configure_logging

pytestmark = pytest.mark.unit


def test_configure_logging_custom_level(clean_root_logger):
    """An explicit level/format installs a handler on the root logger."""
    configure_logging({"level": "DEBUG", "format": "%(levelname)s - %(message)s"})
    assert len(clean_root_logger.handlers) > 0


def test_configure_logging_default_level(clean_root_logger):
    """A missing 'level' key falls back to INFO without raising."""
    configure_logging({"format": "%(message)s"})
    assert len(clean_root_logger.handlers) > 0


def test_configure_logging_invalid_level(clean_root_logger):
    """An unknown level name falls back to INFO without raising."""
    configure_logging({"level": "INVALID_LEVEL", "format": "%(message)s"})
    assert len(clean_root_logger.handlers) > 0


def test_configure_logging_default_format(clean_root_logger):
    """A missing 'format' key uses the default format without raising."""
    configure_logging({"level": "WARNING"})
    assert len(clean_root_logger.handlers) > 0
