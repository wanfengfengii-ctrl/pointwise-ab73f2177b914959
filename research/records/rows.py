from dataclasses import dataclass
from fractions import Fraction
import json


def normalize_rational(value):
    if isinstance(value, bool) or not isinstance(value, (int, str, Fraction)):
        raise ValueError("expected int, fraction string or Fraction")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError("invalid rational") from exc


def identity(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError("identity must be integer or string")
    if isinstance(value, str) and not value:
        raise ValueError("empty identity")
    return value


def identity_key(value):
    identity(value)
    return (0, value) if isinstance(value, int) else (1, value)


def encode_value(value):
    if isinstance(value, Fraction):
        return {"$fraction": [value.numerator, value.denominator]}
    if isinstance(value, dict):
        return {k: encode_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [encode_value(v) for v in value]
    return value


def decode_value(value):
    if isinstance(value, dict):
        if set(value) == {"$fraction"}:
            return Fraction(*value["$fraction"])
        return {k: decode_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode_value(v) for v in value]
    return value


def dumps(value):
    return json.dumps(encode_value(value), sort_keys=True, separators=(",", ":"))


def loads(value):
    return decode_value(json.loads(value))


@dataclass(frozen=True)
class RowPayload:
    values: dict
    group: object = None
    withdrawn: bool = False


def normalize_payload(payload):
    if isinstance(payload, RowPayload):
        payload = dict(values=payload.values, group=payload.group,
                       withdrawn=payload.withdrawn)
    if not isinstance(payload, dict) or set(payload) - {"values", "group", "withdrawn"}:
        raise ValueError("invalid payload")
    values = payload.get("values", {})
    if not isinstance(values, dict):
        raise ValueError("values must be a mapping")
    if any(not isinstance(k, str) or not k or k.startswith("$") for k in values):
        raise ValueError("invalid column name")
    withdrawn = payload.get("withdrawn", False)
    if not isinstance(withdrawn, bool):
        raise ValueError("withdrawn must be boolean")
    group = payload.get("group")
    if group is not None:
        identity(group)
    return RowPayload({k: None if v is None else normalize_rational(v)
                       for k, v in sorted(values.items())}, group, withdrawn)


def payload_data(payload):
    return dict(values=payload.values, group=payload.group, withdrawn=payload.withdrawn)


def payload_fingerprint(payload):
    return dumps(payload_data(payload))
