#validate structured representation responses returned by models

import json
import re


REQUIRED_TOP_LEVEL_KEYS = [
    "protocol",
    "rfc",
    "pdus",
    "bit_string_types",
    "enumerated_types",
    "structure_types",
    "array_types",
    "parsing_context",
    "helper_functions",
    "transform_functions",
]


def remove_thinking_blocks(answer):
    #remove complete thinking tags before json parsing
    return re.sub(
        r"<think>.*?</think>", "", str(answer), flags=re.DOTALL | re.IGNORECASE
    ).strip()


def validate_representation_json(answer):
    #require the complete response to contain one json object
    source = remove_thinking_blocks(answer)
    try:
        representation = json.loads(source)
    except json.JSONDecodeError as error:
        raise ValueError("response is not exactly one valid JSON object") from error
    if not isinstance(representation, dict):
        raise ValueError("top-level JSON value must be an object")

    #check required keys and their top-level value types
    missing = []
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in representation:
            missing.append(key)
    if missing:
        raise ValueError("missing required keys: " + ", ".join(missing))
    if not isinstance(representation["protocol"], str):
        raise ValueError("protocol must be a string")
    if not isinstance(representation["rfc"], str):
        raise ValueError("rfc must be a string")
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key == "protocol" or key == "rfc":
            continue
        if not isinstance(representation[key], list):
            raise ValueError(key + " must be an array")
    return source
