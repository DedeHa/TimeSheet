"""Unit tests for configuration loading.

Covers load_config, _read_yaml and detect_environment in isolation, using
temporary YAML files and a monkeypatched detect_environment so folder structure
on the test host never influences the result.
"""

import pytest
import yaml

from src.TimeSheetAlgo import (
    ConfigError,
    _read_yaml,
    detect_environment,
    load_config,
)

pytestmark = pytest.mark.unit

_DETECT = "src.TimeSheetAlgo.detect_environment"


def _write_config(path, content):
    """Write a config dict to ``path`` as YAML and return the path string."""
    with open(path, "w") as f:
        yaml.dump(content, f)
    return str(path)


def _valid_config(**overrides):
    """Return a minimal valid config dict with optional overrides."""
    config = {
        "year": 2025,
        "environments": {
            "development": {
                "file_paths": {
                    "timelog_path": "timelog.csv",
                    "timesheet_path": "timesheet.xlsx",
                },
                "logging": {"level": "INFO", "format": "%(message)s"},
            }
        },
        "default_environment": "development",
    }
    config.update(overrides)
    return config


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


def test_load_config_valid(tmp_path, monkeypatch):
    """A valid config returns resolved paths, year and detected environment."""
    config_file = _write_config(tmp_path / "config.yaml", _valid_config())
    monkeypatch.setattr(_DETECT, lambda base: "development")

    config = load_config(config_file)

    assert config["timelog_path"].endswith("timelog.csv")
    assert config["timesheet_path"].endswith("timesheet.xlsx")
    assert config["year"] == 2025
    assert config["environment"] == "development"


def test_load_config_file_not_found():
    """A missing config file raises ConfigError."""
    with pytest.raises(ConfigError, match="Config file not found"):
        load_config("/nonexistent/path/config.yaml")


def test_load_config_invalid_yaml(tmp_path, monkeypatch):
    """Malformed YAML raises ConfigError."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("invalid: yaml: content: [")
    monkeypatch.setattr(_DETECT, lambda base: "development")

    with pytest.raises(ConfigError, match="Invalid YAML format"):
        load_config(str(config_file))


def test_load_config_missing_year(tmp_path, monkeypatch):
    """A config without a root-level 'year' raises ConfigError."""
    content = _valid_config()
    del content["year"]
    config_file = _write_config(tmp_path / "config.yaml", content)
    monkeypatch.setattr(_DETECT, lambda base: "development")

    with pytest.raises(ConfigError, match="Missing required 'year' configuration"):
        load_config(config_file)


def test_load_config_missing_environments(tmp_path, monkeypatch):
    """A config without an 'environments' mapping raises KeyError."""
    config_file = _write_config(
        tmp_path / "config.yaml", {"year": 2025, "default_environment": "development"}
    )
    monkeypatch.setattr(_DETECT, lambda base: "development")

    with pytest.raises(KeyError):
        load_config(config_file)


def test_load_config_invalid_environment(tmp_path, monkeypatch):
    """A detected environment absent from the config raises ConfigError."""
    config_file = _write_config(tmp_path / "config.yaml", _valid_config())
    monkeypatch.setattr(_DETECT, lambda base: "invalid")

    with pytest.raises(ConfigError, match="Environment 'invalid' not found"):
        load_config(config_file)


def test_load_config_missing_file_paths(tmp_path, monkeypatch):
    """An environment without 'file_paths' raises KeyError."""
    content = _valid_config()
    content["environments"]["development"] = {"logging": {"level": "INFO"}}
    config_file = _write_config(tmp_path / "config.yaml", content)
    monkeypatch.setattr(_DETECT, lambda base: "development")

    with pytest.raises(KeyError):
        load_config(config_file)


def test_load_config_incomplete_file_paths(tmp_path, monkeypatch):
    """Missing timesheet_path inside file_paths raises KeyError."""
    content = _valid_config()
    content["environments"]["development"]["file_paths"] = {
        "timelog_path": "timelog.csv"
    }
    config_file = _write_config(tmp_path / "config.yaml", content)
    monkeypatch.setattr(_DETECT, lambda base: "development")

    with pytest.raises(KeyError):
        load_config(config_file)


def test_load_config_auto_detects_environment(tmp_path, monkeypatch):
    """Among multiple environments, the auto-detected one is selected."""
    content = _valid_config(
        environments={
            "development": {
                "file_paths": {
                    "timelog_path": "dev_timelog.csv",
                    "timesheet_path": "dev_timesheet.xlsx",
                }
            },
            "production": {
                "file_paths": {
                    "timelog_path": "prod_timelog.csv",
                    "timesheet_path": "prod_timesheet.xlsx",
                }
            },
        }
    )
    config_file = _write_config(tmp_path / "config.yaml", content)
    monkeypatch.setattr(_DETECT, lambda base: "production")

    config = load_config(config_file)

    assert config["timelog_path"].endswith("prod_timelog.csv")
    assert config["environment"] == "production"


def test_load_config_invalid_structure(tmp_path, monkeypatch):
    """A non-mapping YAML root raises ConfigError."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("- item1\n- item2\n")
    monkeypatch.setattr(_DETECT, lambda base: "development")

    with pytest.raises(ConfigError, match="Config root must be a mapping"):
        load_config(str(config_file))


def test_load_config_empty_file(tmp_path, monkeypatch):
    """An empty YAML file parses to {} and then fails the required-year check."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("")
    monkeypatch.setattr(_DETECT, lambda base: "development")

    with pytest.raises(ConfigError, match="Missing required 'year' configuration"):
        load_config(str(config_file))


# ---------------------------------------------------------------------------
# _read_yaml
# ---------------------------------------------------------------------------


def test_read_yaml_oserror(tmp_path, monkeypatch):
    """An OSError while reading raises ConfigError."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("test: data")

    def raise_oserror(path, *args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", raise_oserror)

    with pytest.raises(ConfigError, match="Unable to read config file"):
        _read_yaml(str(config_file))


# ---------------------------------------------------------------------------
# detect_environment
# ---------------------------------------------------------------------------


def test_detect_environment_src_timesheetalgo(tmp_path):
    """A folder named 'src_timesheetalgo' maps to development."""
    src_folder = tmp_path / "src_timesheetalgo"
    src_folder.mkdir()
    assert detect_environment(str(src_folder)) == "development"


def test_detect_environment_timealarm_folder(tmp_path):
    """A 'Timealarm' subfolder maps to production."""
    (tmp_path / "Timealarm").mkdir()
    assert detect_environment(str(tmp_path)) == "production"


def test_detect_environment_fallback(tmp_path):
    """An unrelated folder falls back to development."""
    assert detect_environment(str(tmp_path)) == "development"
