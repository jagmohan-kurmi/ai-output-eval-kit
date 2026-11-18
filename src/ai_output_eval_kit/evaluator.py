from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class InputError(ValueError):
    """Raised when an evaluation case is malformed."""


def _json_path(value: Any, path: str) -> Any:
    if path == "$":
        return value
    if not path.startswith("$"):
        raise InputError(f"JSON path must begin with '$': {path}")
    parts = re.findall(r"\.([A-Za-z_][A-Za-z0-9_-]*)|\[(\d+)\]|\[['\"]([^'\"]+)['\"]\]", path[1:])
    consumed = "".join("." + a if a else f"[{b}]" if b else f"['{c}']" for a, b, c in parts)
    if consumed != path[1:]:
        raise InputError(f"Unsupported JSON path syntax: {path}")
    current = value
    for key, index, quoted in parts:
        try:
            if index:
                current = current[int(index)]
            elif quoted:
                current = current[quoted]
            else:
                current = current[key]
        except (KeyError, IndexError, TypeError) as exc:
            raise KeyError(f"Path not found: {path}") from exc
    return current


def _schema_errors(value: Any, schema: Any, path: str = "$") -> list[str]:
    if not isinstance(schema, dict):
        raise InputError("Schema assertion must contain a JSON object schema.")
    if "required" in schema and (
        not isinstance(schema["required"], list)
        or any(not isinstance(key, str) for key in schema["required"])
    ):
        raise InputError("Schema 'required' must be an array of property names.")
    if "properties" in schema and not isinstance(schema["properties"], dict):
        raise InputError("Schema 'properties' must be an object.")
    if "enum" in schema and not isinstance(schema["enum"], list):
        raise InputError("Schema 'enum' must be an array.")
    if "items" in schema and not isinstance(schema["items"], dict):
        raise InputError("Schema 'items' must be an object.")
    for key in ("minLength", "maxLength"):
        if key in schema and (
            not isinstance(schema[key], int) or isinstance(schema[key], bool) or schema[key] < 0
        ):
            raise InputError(f"Schema '{key}' must be a non-negative integer.")
    for key in ("minimum", "maximum"):
        if key in schema and (
            not isinstance(schema[key], (int, float)) or isinstance(schema[key], bool)
        ):
            raise InputError(f"Schema '{key}' must be a number.")
    errors: list[str] = []
    expected_type = schema.get("type")
    type_checks = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "null": lambda v: v is None,
    }
    if expected_type is not None:
        if not isinstance(expected_type, str) or expected_type not in type_checks:
            raise InputError(f"Unsupported schema type: {expected_type}")
        if not type_checks[expected_type](value):
            return [f"{path} expected {expected_type}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path} is not in enum")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key} is required")
        for key, child_schema in schema.get("properties", {}).items():
            if key in value:
                errors.extend(_schema_errors(value[key], child_schema, f"{path}.{key}"))
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            errors.extend(_schema_errors(item, schema["items"], f"{path}[{index}]"))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path} is shorter than minLength")
        if len(value) > schema.get("maxLength", float("inf")):
            errors.append(f"{path} is longer than maxLength")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path} is below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path} is above maximum")
    return errors


def _evaluate_assertion(actual: Any, assertion: Any, fallback_expected: Any) -> tuple[bool, str]:
    if not isinstance(assertion, dict):
        raise InputError("Each assertion must be a JSON object.")
    kind = assertion.get("type")
    if kind == "exact":
        expected = assertion.get("expected", fallback_expected)
        if "expected" not in assertion and fallback_expected is _MISSING:
            raise InputError("Exact assertions require expected.")
        return actual == expected, "value does not exactly match expected" if actual != expected else "exact match"
    if kind == "contains":
        target = actual
        if "path" in assertion:
            if not isinstance(assertion["path"], str):
                raise InputError("Contains assertion path must be a string.")
            try:
                target = _json_path(actual, assertion["path"])
            except KeyError as exc:
                return False, str(exc)
        needle = assertion.get("value", assertion.get("expected", fallback_expected))
        if needle is _MISSING:
            raise InputError("Contains assertions require value or expected.")
        try:
            matched = needle in target
        except TypeError:
            matched = False
        return matched, f"value does not contain {needle!r}" if not matched else "contains value"
    if kind in {"json_path", "json-path"}:
        path = assertion.get("path")
        if not isinstance(path, str):
            raise InputError("JSON-path assertions require a path string.")
        try:
            selected = _json_path(actual, path)
        except KeyError as exc:
            return False, str(exc)
        expected = assertion.get("expected", fallback_expected)
        if expected is _MISSING:
            raise InputError("JSON-path assertions require expected.")
        return selected == expected, f"{path} was {selected!r}, expected {expected!r}" if selected != expected else "path matched"
    if kind == "schema":
        errors = _schema_errors(actual, assertion.get("schema"))
        return not errors, "; ".join(errors) if errors else "schema matched"
    raise InputError(f"Unknown assertion type: {kind!r}")


_MISSING = object()


def evaluate_case(case: Any, line_number: int) -> dict:
    if not isinstance(case, dict) or "actual" not in case:
        raise InputError(f"Line {line_number}: case must be an object with 'actual'.")
    assertions = case.get("assertions")
    if not isinstance(assertions, list) or not assertions:
        raise InputError(f"Line {line_number}: case must contain a non-empty assertions array.")
    case_id = case.get("id", f"line-{line_number}")
    if not isinstance(case_id, (str, int)):
        raise InputError(f"Line {line_number}: id must be a string or integer.")
    results = []
    for index, assertion in enumerate(assertions, start=1):
        passed, detail = _evaluate_assertion(case["actual"], assertion, case.get("expected", _MISSING))
        results.append({"index": index, "type": assertion.get("type"), "passed": passed, "detail": detail})
    return {"id": case_id, "passed": all(item["passed"] for item in results), "assertions": results}


def evaluate_jsonl(path: Path) -> dict:
    results = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise InputError(str(exc)) from exc
    for line_number, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            case = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InputError(f"Line {line_number}: invalid JSON: {exc.msg}") from exc
        results.append(evaluate_case(case, line_number))
    if not results:
        raise InputError("Evaluation file contains no cases.")
    passed = sum(item["passed"] for item in results)
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": passed / len(results),
        "cases": results,
    }
