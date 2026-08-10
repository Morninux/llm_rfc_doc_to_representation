import ast
import json
import os
import pprint
import re

from load_llm import PROJECT_PATH, run_model


RFC_DOCUMENT_PATH = os.path.join(PROJECT_PATH, "rfc_document_set")
TEMPFILE_PATH = os.path.join(PROJECT_PATH, "tempfile")

RFC_EXTRACTION_INSTRUCTION = """# MANDATORY OUTPUT CONTRACT

Your entire response MUST be exactly one JSON object conforming to the schema
below. The first non-whitespace character MUST be `{` and the last MUST be `}`.

NEVER return Markdown, headings, prose, summaries, tables, code fences, XML tags,
Python assignments, or analysis outside that JSON object. Do not replace the
required representation with a human-readable RFC summary. Every required
top-level key MUST be present even when its value is an empty array.

# RFC to Network Packet Representation Prompt

You are a network protocol specification analysis system.

Your task is to analyse an RFC document and convert the packet format
described in the RFC into a structured Network Packet Representation.

The representation must describe protocol data units using typed packet
structures, field layouts, constraints, optional fields, variable-length
data, and parsing dependencies when such information is available.

## Core Representation Concepts

Use the following concepts when constructing the representation:

- Protocol: the overall network protocol.
- PDU: a protocol data unit or packet format defined by the protocol.
- Bit String Type: raw protocol data with a specific bit width and semantic meaning.
- Enumerated Type: a value or packet type that can have multiple variants.
- Structure Type: an ordered collection of heterogeneous packet fields.
- Array Type: a sequence of elements whose length may be fixed or depend on another field.
- Presence Condition: an expression determining whether a field is present.
- Constraint: a condition that must hold for a packet or field to be valid.
- Parsing Context: persistent or external information required to parse packet data.
- Helper Function: a function used to calculate values or evaluate constraints.
- Transform Function: a function describing how one representation is parsed from or
  serialized to another representation.

## Extraction Rules

1. Use only information contained in the supplied RFC input.

2. Do not use prior knowledge about the protocol.

3. Do not invent:
   - packet fields
   - field sizes
   - field offsets
   - constraints
   - optionality
   - packet types
   - parsing dependencies
   - functions

4. Packet diagrams and field descriptions are the primary evidence for packet structure.

5. Field order must match the order in which fields occur on the wire.

6. `offset_bits` is measured from the beginning of the current PDU.

7. `size_bits` may be obtained from:
   - an explicit field size in the RFC;
   - packet diagram boundaries;
   - a deterministic calculation based on preceding fixed-width fields.

8. If a size or offset cannot be determined reliably, use `null`.

9. Use lowercase snake_case for machine-readable field names.

Example:

Source Port

becomes:

"name": "source_port",
"display_name": "Source Port"

10. Preserve the semantic meaning of field descriptions, but descriptions may be
    shortened.

11. A field may only have:

"optional": true

when the RFC explicitly defines it as optional or defines a condition under
which it is present.

12. If the presence of a field depends on another field, store that dependency in:

"presence_condition"

Example:

"presence_condition": "x == 1"

13. Only generate constraints that are explicitly stated in the RFC or can be
    deterministically expressed from an RFC requirement.

Examples:

"length >= 8"
"version == 4"
"payload_length == length - 8"

14. If no constraint is available, use:

"constraints": []

15. Variable-length data must not be converted into an arbitrary fixed size.

Represent its size using an expression when possible.

Example:

"size": "length - 8"

16. If multiple different packet formats are defined, represent them as separate
    structure types.

17. If multiple packet formats are alternatives of a common packet type, they may
    be represented as variants of an enumerated type.

18. Different fields with the same bit width may still represent different
    semantic types.

19. Create parsing context information only when parsing depends on:
    - previous packets;
    - external state;
    - out-of-band information.

20. Create helper functions or transform functions only when the RFC explicitly
    describes such processing.

21. Never guess missing information.

When evidence is insufficient, use:
- null
- an empty array
- an empty object where appropriate

Accuracy is more important than completeness.

## Required Output Format

Return ONLY one valid JSON object.

Do NOT output:
- Markdown
- code fences
- comments
- explanations
- Python assignments
- text before the JSON
- text after the JSON

The JSON must follow this structure:

{
  "protocol": "string",
  "rfc": "string",

  "pdus": [
    "string"
  ],

  "bit_string_types": [
    {
      "name": "string",
      "size_bits": "integer or null",
      "description": "string"
    }
  ],

  "enumerated_types": [
    {
      "name": "string",
      "variants": [
        {
          "name": "string",
          "type": "string",
          "condition": "string or null"
        }
      ]
    }
  ],

  "structure_types": [
    {
      "name": "string",

      "header_size_bytes": "integer or null",

      "byte_order": "string or null",

      "fields": [
        {
          "name": "string",
          "display_name": "string",
          "offset_bits": "integer or null",
          "size_bits": "integer or null",
          "type": "string or null",
          "optional": "boolean or null",
          "presence_condition": "string or null",
          "description": "string",
          "constraints": [
            "string"
          ]
        }
      ],

      "payload": {
        "name": "string",
        "offset_bits": "integer or null",
        "size": "integer, expression, or null"
      },

      "constraints": [
        "string"
      ],

      "parse_from": "string or null",
      "serialize_to": "string or null"
    }
  ],

  "array_types": [
    {
      "name": "string",
      "element_type": "string",
      "length": "integer, expression, or null"
    }
  ],

  "parsing_context": [
    {
      "name": "string",
      "type": "string",
      "description": "string"
    }
  ],

  "helper_functions": [
    {
      "name": "string",
      "description": "string"
    }
  ],

  "transform_functions": [
    {
      "name": "string",
      "from": "string",
      "to": "string",
      "description": "string"
    }
  ]
}

## RFC Input

<RFC_DOCUMENT>

{RFC_TEXT}

</RFC_DOCUMENT>
"""


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


def validate_representation_json(answer): #validate the minimum contract required of an extracted representation."""
    source = re.sub(
        r"<think>.*?</think>", "", str(answer), flags=re.DOTALL | re.IGNORECASE
    ).strip()
    try:
        representation = json.loads(source)
    except json.JSONDecodeError as error:
        raise ValueError("response is not exactly one valid JSON object") from error
    if not isinstance(representation, dict):
        raise ValueError("top-level JSON value must be an object")

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


def generate_rfc_representation(model_name, prompt):
    answer = run_model(model_name, prompt, json_output=True)
    try:
        return validate_representation_json(answer)
    except ValueError as first_error:
        repair_prompt = """Your previous response violated the mandatory output
contract: {error}.

Return the corrected Network Packet Representation now. Output exactly one JSON
object and nothing else. It must contain every required top-level key shown in
the original instruction. Do not summarize the RFC and do not use Markdown.

<INVALID_RESPONSE>
{answer}
</INVALID_RESPONSE>

<ORIGINAL_INSTRUCTION>
{prompt}
</ORIGINAL_INSTRUCTION>
""".format(error=first_error, answer=answer, prompt=prompt)
        repaired = run_model(model_name, repair_prompt, json_output=True)
        try:
            return validate_representation_json(repaired)
        except ValueError as second_error:
            raise RuntimeError(
                "Model " + model_name
                + " failed the representation contract after one retry: "
                + str(second_error)
            ) from second_error

def clean_python_output(answer):
    source = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()
    if not source:
        return "NO_MODELS = []"

    fenced_blocks = re.findall(
        r"```(?:python|py)?\s*\n(.*?)```", source, flags=re.DOTALL | re.IGNORECASE
    )
    candidates = fenced_blocks + [source]

    for candidate in candidates:
        candidate = candidate.strip()

        try:
            json_model = json.loads(candidate)
        except json.JSONDecodeError:
            json_model = None
        if isinstance(json_model, dict):
            protocol = str(json_model.get("protocol", "PROTOCOL"))
            constant_name = re.sub(r"[^A-Za-z0-9]+", "_", protocol).strip("_")
            constant_name = (constant_name or "PROTOCOL").upper() + "_MODEL"
            return constant_name + " = " + pprint.pformat(
                json_model, sort_dicts=False, width=88
            )

        assignment = re.search(
            r"(?m)^(?:[A-Z][A-Z0-9_]*_MODEL|NO_MODELS)\s*=", candidate
        )
        if assignment:
            candidate = candidate[assignment.start():]

        #models often append an explanation after otherwise valid code. Try progressively shorter line prefixes and retain the longest valid one.
        lines = candidate.splitlines()
        for end in range(len(lines), 0, -1):
            possible_source = "\n".join(lines[:end]).strip()
            try:
                tree = ast.parse(possible_source)
            except SyntaxError:
                continue

            assignments = [node for node in tree.body if isinstance(node, ast.Assign)]
            valid_target = any(
                isinstance(target, ast.Name)
                and (target.id.endswith("_MODEL") or target.id == "NO_MODELS")
                for node in assignments
                for target in node.targets
            )
            if valid_target:
                return possible_source

    raise RuntimeError("The model returned invalid Python source.")


def generate_python_output(model_name, prompt):
    answer = run_model(model_name, prompt)
    try:
        return clean_python_output(answer)
    except RuntimeError:
        repair_prompt = """Repair the content below into valid Python source code.
Return only one or more uppercase *_MODEL dictionary assignments. Preserve all
available protocol information. Do not use Markdown or add explanations.

<content>
{answer}
</content>
""".format(answer=answer)
        repaired_answer = run_model(model_name, repair_prompt)
        try:
            return clean_python_output(repaired_answer)
        except RuntimeError as error:
            raise RuntimeError(
                "Model " + model_name
                + " returned invalid Python source after an automatic retry."
            ) from error


def safe_path_name(name):
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return safe_name or "model"


def extract_rfc_packet_diagrams(
    rfc_number,
    model_list,
    document_path=RFC_DOCUMENT_PATH,
    output_path=TEMPFILE_PATH,
    stream_output=False,
):

    if not os.path.isdir(document_path):
        raise FileNotFoundError("RFC document folder not found: " + document_path)

    number = str(rfc_number).strip()
    if not number.isdigit():
        raise ValueError("RFC number must contain digits only: " + number)

    document_name = "rfc" + number + ".txt"
    source_path = os.path.join(document_path, document_name)
    if not os.path.isfile(source_path):
        raise FileNotFoundError("RFC document not found: " + source_path)

    with open(source_path, "r", encoding="utf-8", errors="replace") as file:
        document = file.read()
    #keep the structured Network Packet Representation requested by the original prompt, but print each model's raw JSON response instead of converting it to Python or saving it to a file.
    prompt = RFC_EXTRACTION_INSTRUCTION.replace("{RFC_TEXT}", document)

    results = []

    for model_name in model_list:
        try:
            answer = generate_rfc_representation(model_name, prompt)
            results.append((model_name, answer, None, None))
        except RuntimeError as error:
            error_text = str(error)
            results.append((model_name, None, None, error_text))

        if stream_output:
            print_extraction_results([results[-1]])

    return results


def print_extraction_results(results):
    for model_name, answer, result_path, error in results:
        print("\n====================>> " + model_name + " <<====================")
        if error:
            print("Skipped: " + error)
        else:
            print(answer)
            if result_path:
                print("Saved to: " + result_path)


def send_to_all_models(user_text, model_list): #send the same text to every model one by one
    for model_name in model_list:  #run models in order
        print("\n====================>> " + model_name + " <<====================")
        answer = run_model(model_name, user_text)  # get model answer
        print(answer)


def start_input(model_list):
    print("Loaded local models: " + ", ".join(model_list))
    print(
        "Enter an RFC number to generate its structured packet representation, "
        "or type exit to stop."
    )

    while True:
        user_text = input("\nYou: ").strip()  #get user input

        if user_text.lower() == "exit":
            print("Stopped.")
            break

        if user_text != "":
            try:
                extract_rfc_packet_diagrams(
                    user_text, model_list, stream_output=True
                )
            except (ValueError, FileNotFoundError, RuntimeError) as error:
                print(error)
