import os
import re

from load_llm import PROJECT_PATH
from text_input import (
    RFC_EXTRACTION_INSTRUCTION,
    generate_rfc_representation,
    print_extraction_results,
)


RFC_DOCUMENT_PATH = os.path.join(PROJECT_PATH, "rfc_document_set")


def is_diagram_line(line):
    stripped = line.strip()
    if not stripped:
        return False
    border_chars = 0
    for character in "+|-=":
        border_chars += stripped.count(character)
    has_border = border_chars >= 4 and ("+" in stripped or "|" in stripped)
    has_cells = stripped.count("|") >= 2
    has_bit_ruler = bool(
        re.search(r"(?:^|\s)0\s+.*(?:7|15|23|31)(?:\s|$)", stripped)
    )
    return has_border or has_cells or has_bit_ruler


def locate_ascii_packet_diagrams(document, context_lines=12):
    lines = document.splitlines()
    marked = []
    for index, line in enumerate(lines):
        if is_diagram_line(line):
            marked.append(index)
    if not marked:
        return []

    groups = []
    start = previous = marked[0]
    for index in marked[1:]:
        if index - previous <= 3:
            previous = index
            continue
        groups.append((start, previous))
        start = previous = index
    groups.append((start, previous))

    results = []
    for start, end in groups:
        diagram_start = max(0, start - 1)
        diagram_end = min(len(lines), end + 2)
        diagram_lines = lines[diagram_start:diagram_end]
        diagram_text = "\n".join(diagram_lines)

        border_rows = 0
        cell_rows = 0
        for line in diagram_lines:
            if "+" in line and "-" in line:
                border_rows += 1
            if line.count("|") >= 2:
                cell_rows += 1
        has_ruler = bool(
            re.search(r"(?:^|\s)0\s+.*(?:7|15|23|31)(?:\s|$)", diagram_text)
        )
        if border_rows < 2 or cell_rows < 1:
            continue
        if not has_ruler and cell_rows < 2:
            continue
        #state machines commonly use the same box characters, but connect small boxes with arrows
        #maybe this is a way to judge
        if not has_ruler and ("->" in diagram_text or "<-" in diagram_text):
            continue

        context_start = max(0, diagram_start - context_lines)
        context_end = min(len(lines), diagram_end + context_lines)
        results.append(
            {
                "start_line": diagram_start + 1,
                "end_line": diagram_end,
                "diagram": diagram_text,
                "context": "\n".join(lines[context_start:context_end]),
            }
        )
    return results


def _format_diagram_evidence(rfc_number, diagrams):
    sections = [
        "RFC " + str(rfc_number) + " packet-diagram candidates were located locally.",
        "Use only the candidate diagrams and their nearby RFC text below as evidence.",
    ]
    for index, item in enumerate(diagrams, start=1):
        sections.append(
            "\n<CANDIDATE number=\"{}\" lines=\"{}-{}\">\n{}\n</CANDIDATE>".format(
                index,
                item["start_line"],
                item["end_line"],
                item["context"],
            )
        )
    return "\n".join(sections)


def extract_rfc_from_ascii_diagrams(
    rfc_number,
    model_list,
    document_path=RFC_DOCUMENT_PATH,
    stream_output=False,
):
    number = str(rfc_number).strip()
    if not number.isdigit():
        raise ValueError("RFC number must contain digits only: " + number)
    if not os.path.isdir(document_path):
        raise FileNotFoundError("RFC document folder not found: " + document_path)

    source_path = os.path.join(document_path, "rfc" + number + ".txt")
    if not os.path.isfile(source_path):
        raise FileNotFoundError("RFC document not found: " + source_path)
    with open(source_path, "r", encoding="utf-8", errors="replace") as file:
        document = file.read()

    diagrams = locate_ascii_packet_diagrams(document)
    if not diagrams:
        raise RuntimeError("No packet-like ASCII diagram was found in RFC " + number + ".")

    evidence = _format_diagram_evidence(number, diagrams)
    prompt = RFC_EXTRACTION_INSTRUCTION.replace("{RFC_TEXT}", evidence)
    results = []
    for model_name in model_list:
        try:
            answer = generate_rfc_representation(model_name, prompt)
            results.append((model_name, answer, None, None))
        except RuntimeError as error:
            results.append((model_name, None, None, str(error)))
        if stream_output:
            print_extraction_results([results[-1]])
    return results
