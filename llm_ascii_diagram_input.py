#use a model to locate ascii diagrams and then extract a representation

import json
import os
import re

from load_llm import PROJECT_PATH, run_model
from text_input import (
    RFC_EXTRACTION_INSTRUCTION,
    generate_rfc_representation,
    print_extraction_results,
)


RFC_DOCUMENT_PATH = os.path.join(PROJECT_PATH, "rfc_document_set")


def add_line_numbers(document):
    #add stable line numbers so the model can identify exact text ranges
    numbered_lines = []
    lines = document.splitlines()
    for index, line in enumerate(lines, start=1):
        numbered_lines.append("{}: {}".format(index, line))
    return "\n".join(numbered_lines)


def format_location_prompt(rfc_number, document):
    #ask the model to locate packet diagrams in the complete rfc document
    instruction = (
        "Read the complete numbered RFC document below. Find every ASCII diagram "
        "that defines the layout of a network packet, message, header, frame, or "
        "protocol data unit. Reject ordinary tables, state machines, timelines, "
        "examples, and message flow diagrams. Return exactly one JSON object in "
        "this form: {\"diagram_ranges\":[{\"start_line\":10,\"end_line\":20}]}. "
        "Use an empty diagram_ranges array when no packet layout exists. Include "
        "only line ranges that belong to the ASCII diagram itself."
    )
    return (
        instruction
        + "\n\n<RFC number=\""
        + str(rfc_number)
        + "\">\n"
        + add_line_numbers(document)
        + "\n</RFC>"
    )


def parse_diagram_ranges(answer, line_count):
    #remove complete thinking blocks before parsing the location response
    source = re.sub(
        r"<think>.*?</think>", "", str(answer), flags=re.DOTALL | re.IGNORECASE
    ).strip()
    try:
        data = json.loads(source)
    except json.JSONDecodeError as error:
        raise ValueError("diagram location response is not valid json") from error

    #require the exact top-level range list used by this pipeline
    if not isinstance(data, dict):
        raise ValueError("diagram location response must be a json object")
    ranges = data.get("diagram_ranges")
    if not isinstance(ranges, list):
        raise ValueError("diagram_ranges must be an array")

    #validate each line range before reading from the source document
    valid_ranges = []
    for item in ranges:
        if not isinstance(item, dict):
            raise ValueError("every diagram range must be a json object")
        start_line = item.get("start_line")
        end_line = item.get("end_line")
        if not isinstance(start_line, int) or not isinstance(end_line, int):
            raise ValueError("diagram line numbers must be integers")
        if start_line < 1 or end_line < start_line or end_line > line_count:
            raise ValueError("diagram line range is outside the rfc document")
        valid_ranges.append((start_line, end_line))
    return valid_ranges


def locate_diagram_ranges(rfc_number, document, model_name):
    #send the complete document to the model for diagram location
    prompt = format_location_prompt(rfc_number, document)
    answer = run_model(model_name, prompt, json_output=True)
    line_count = len(document.splitlines())
    try:
        return parse_diagram_ranges(answer, line_count)
    except ValueError as first_error:
        #retry once when the model returns the wrong json structure
        repair_prompt = (
            "Correct the response below. Return exactly one JSON object with a "
            "diagram_ranges array. Every item must contain integer start_line and "
            "end_line values between 1 and {}. Error: {}. Response: {}"
        ).format(line_count, first_error, answer)
        repaired = run_model(model_name, repair_prompt, json_output=True)
        return parse_diagram_ranges(repaired, line_count)


def extract_diagram_evidence(document, ranges, context_lines=12):
    #extract each selected diagram with nearby explanatory rfc text
    lines = document.splitlines()
    sections = []
    for index, line_range in enumerate(ranges, start=1):
        start_line = line_range[0]
        end_line = line_range[1]
        context_start = max(0, start_line - 1 - context_lines)
        context_end = min(len(lines), end_line + context_lines)
        context = "\n".join(lines[context_start:context_end])
        section = "<DIAGRAM number=\"{}\" lines=\"{}-{}\">\n{}\n</DIAGRAM>"
        sections.append(section.format(index, start_line, end_line, context))
    return "\n\n".join(sections)


def extract_rfc_from_llm_ascii_diagrams(
    rfc_number,
    model_list,
    document_path=RFC_DOCUMENT_PATH,
    stream_output=False,
):
    #validate the rfc number and source folder
    number = str(rfc_number).strip()
    if not number.isdigit():
        raise ValueError("RFC number must contain digits only: " + number)
    if not os.path.isdir(document_path):
        raise FileNotFoundError("RFC document folder not found: " + document_path)

    #load the complete rfc document once for all models
    source_path = os.path.join(document_path, "rfc" + number + ".txt")
    if not os.path.isfile(source_path):
        raise FileNotFoundError("RFC document not found: " + source_path)
    with open(source_path, "r", encoding="utf-8", errors="replace") as file:
        document = file.read()

    #let each model locate diagrams and extract its own representation
    results = []
    for model_name in model_list:
        try:
            ranges = locate_diagram_ranges(number, document, model_name)
            if not ranges:
                raise RuntimeError(
                    "Model " + model_name + " found no packet ASCII diagram."
                )

            #send only model-selected diagrams into the representation prompt
            evidence = extract_diagram_evidence(document, ranges)
            prompt = RFC_EXTRACTION_INSTRUCTION.replace("{RFC_TEXT}", evidence)
            answer = generate_rfc_representation(model_name, prompt)
            results.append((model_name, answer, None, None))
        except (RuntimeError, ValueError) as error:
            results.append((model_name, None, None, str(error)))

        if stream_output:
            print_extraction_results([results[-1]])
    return results
