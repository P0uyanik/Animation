"""Validate offline dialogue and viseme documents using their bundled schemas."""
import argparse
import json
import math
import re
from pathlib import Path


def check(value, schema, path):
    """Evaluate the small subset of JSON Schema used by the two shipped files."""
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            raise ValueError(f"{path}: expected object")
        missing = set(schema.get("required", [])) - value.keys()
        if missing or len(value) < schema.get("minProperties", 0):
            raise ValueError(f"{path}: missing properties {sorted(missing)}")
        for key, item in value.items():
            if "propertyNames" in schema:
                check(key, schema["propertyNames"], path)
            rule = schema.get("properties", {}).get(key, schema.get("additionalProperties"))
            if rule is False:
                raise ValueError(f"{path}: unexpected key {key}")
            check(item, rule, f"{path}.{key}")
    elif kind == "array":
        if not isinstance(value, list) or len(value) < schema.get("minItems", 0):
            raise ValueError(f"{path}: expected array with enough items")
        for i, item in enumerate(value):
            check(item, schema["items"], f"{path}[{i}]")
    elif kind == "number":
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"{path}: expected finite number")
        if (value < schema.get("minimum", -math.inf) or value > schema.get("maximum", math.inf)
                or value <= schema.get("exclusiveMinimum", -math.inf)):
            raise ValueError(f"{path}: number outside allowed range")
    elif kind == "string":
        if not isinstance(value, str) or not re.search(schema["pattern"], value):
            raise ValueError(f"{path}: expected nonblank string")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: unknown value {value!r}")
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{path}: expected {schema['const']}")


def validate(doc):
    fmt = doc.get("format") if isinstance(doc, dict) else None
    if fmt not in ("plush.visemes/1", "plush.dialogue/1"):
        raise ValueError("unknown document format")
    schema = Path(__file__).with_name(fmt.split("/")[0] + ".schema.json")
    check(doc, json.loads(schema.read_text(encoding="utf-8")), "$")
    if fmt == "plush.visemes/1":
        # Allow roundoff when exact sample duration lands on a frame boundary.
        count = doc["duration"] * doc["fps"]
        if len(doc["frames"]) != max(1, math.ceil(math.nextafter(count, -math.inf))):
            raise ValueError("frame count does not cover the audio duration")
        for i, weights in enumerate(doc["frames"]):
            if abs(sum(weights.values()) - 1) > 1e-6:
                raise ValueError(f"frame {i}: weights must sum to one")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("documents", type=Path, nargs="+")
    args = parser.parse_args()
    for filename in args.documents:
        try:
            validate(json.loads(filename.read_text(encoding="utf-8")))
        except (ValueError, OSError, OverflowError) as exc:
            parser.exit(1, f"{filename}: {exc}\n")
        print(f"{filename}: valid")
