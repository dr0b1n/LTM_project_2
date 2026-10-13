"""Controlled file loaders for synthetic telemetry and FinOps policies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from finops_demo.models import PolicySet, TelemetryDataset


class InputLoadError(RuntimeError):
    """Raised when an input file cannot be read, parsed, or validated."""


def _require_file(path: Path) -> None:
    if not path.exists():
        raise InputLoadError(f"Input file does not exist: {path}")
    if not path.is_file():
        raise InputLoadError(f"Input path is not a file: {path}")


def load_telemetry(path: str | Path) -> TelemetryDataset:
    """Read and validate a synthetic telemetry JSON file."""

    input_path = Path(path)
    _require_file(input_path)
    try:
        with input_path.open(encoding="utf-8") as handle:
            payload: Any = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise InputLoadError(f"Unable to parse telemetry JSON {input_path}: {exc}") from exc

    try:
        return TelemetryDataset.model_validate(payload)
    except ValidationError as exc:
        raise InputLoadError(
            f"Telemetry validation failed for {input_path}:\n{exc}"
        ) from exc


def load_policies(path: str | Path) -> PolicySet:
    """Read and validate a FinOps policy YAML file without executing expressions."""

    input_path = Path(path)
    _require_file(input_path)
    try:
        with input_path.open(encoding="utf-8") as handle:
            payload: Any = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        raise InputLoadError(f"Unable to parse policy YAML {input_path}: {exc}") from exc

    if payload is None:
        raise InputLoadError(f"Policy YAML is empty: {input_path}")

    try:
        return PolicySet.model_validate(payload)
    except ValidationError as exc:
        raise InputLoadError(
            f"Policy validation failed for {input_path}:\n{exc}"
        ) from exc
