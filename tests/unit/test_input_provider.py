"""Unit tests for the injected InputProvider.

These tests supply a pure ``Callable[[str], str]`` to the functions that
previously called ``builtins.input`` directly — no ``monkeypatch`` on
``builtins.input`` is required.
"""

from datetime import datetime

import pytest

from src.TimeSheetAlgo import (
    _default_input_provider,
    parse_date,
)

pytestmark = pytest.mark.unit


def _make_provider(inputs):
    """Build an InputProvider that returns strings from a queue."""

    def _provider(prompt: str) -> str:
        if not inputs:
            raise EOFError("no more inputs")
        return inputs.pop(0)

    return _provider


# ---------------------------------------------------------------------------
# InputProvider type alias and default
# ---------------------------------------------------------------------------


def test_input_provider_is_callable():
    """InputProvider is a Callable alias usable as a type hint."""
    assert callable(_default_input_provider)


def test_default_input_provider_delegates_to_builtin(monkeypatch):
    """The default InputProvider delegates to ``builtins.input``."""
    captured = {}

    def fake_input(prompt):
        captured["prompt"] = prompt
        return "15.03.2025"

    monkeypatch.setattr("builtins.input", fake_input)
    assert _default_input_provider("Enter date: ") == "15.03.2025"
    assert captured["prompt"] == "Enter date: "


# ---------------------------------------------------------------------------
# parse_date with injected InputProvider
# ---------------------------------------------------------------------------


def test_parse_date_valid_via_provider():
    """A valid date string is parsed when supplied via the provider."""
    provider = _make_provider(["15.03.2025"])
    assert parse_date("Enter date: ", input_provider=provider) == datetime(2025, 3, 15)


def test_parse_date_retries_exhausted_via_provider():
    """Repeated invalid input raises ValueError after the retry budget."""
    provider = _make_provider(["invalid", "invalid", "invalid"])
    with pytest.raises(ValueError, match="Maximum retries reached"):
        parse_date("Enter date: ", retries=3, input_provider=provider)


def test_parse_date_retries_zero_via_provider():
    """retries=0 raises ValueError immediately."""
    provider = _make_provider(["invalid"])
    with pytest.raises(ValueError, match="Maximum retries reached"):
        parse_date("Enter date: ", retries=0, input_provider=provider)


def test_parse_date_invalid_then_valid_via_provider():
    """An invalid entry followed by a valid one returns the parsed date."""
    provider = _make_provider(["invalid", "15.03.2025"])
    assert parse_date("Enter date: ", retries=3, input_provider=provider) == datetime(
        2025, 3, 15
    )


def test_parse_date_eof_propagates_via_provider():
    """An EOFError from the provider propagates (only ValueError is caught)."""

    def _provider(prompt):
        raise EOFError("no input")

    with pytest.raises(EOFError):
        parse_date("Enter date: ", retries=1, input_provider=_provider)
