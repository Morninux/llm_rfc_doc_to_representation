#locate packet ascii diagrams with local text rules

import re


def is_diagram_line(line):
    #check common borders, cells, and packet bit rulers
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
    #collect lines that look like ascii diagram content
    lines = document.splitlines()
    marked = []
    for index, line in enumerate(lines):
        if is_diagram_line(line):
            marked.append(index)
    if not marked:
        return []

    #merge nearby lines into diagram candidates
    groups = []
    start = marked[0]
    previous = marked[0]
    for index in marked[1:]:
        if index - previous <= 3:
            previous = index
            continue
        groups.append((start, previous))
        start = index
        previous = index
    groups.append((start, previous))

    #filter ordinary tables and likely state machines
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
        if not has_ruler and ("->" in diagram_text or "<-" in diagram_text):
            continue

        #preserve nearby text that explains diagram fields
        context_start = max(0, diagram_start - context_lines)
        context_end = min(len(lines), diagram_end + context_lines)
        results.append(
            {
                "start_line": diagram_start + 1,
                "end_line": diagram_end,
                "context": "\n".join(lines[context_start:context_end]),
            }
        )
    return results


def format_rule_ascii_evidence(rfc_number, diagrams):
    #format selected diagrams as one representation evidence source
    sections = [
        "RFC " + str(rfc_number) + " packet-diagram candidates were located locally.",
        "Use only the candidate diagrams and their nearby RFC text below as evidence.",
    ]
    for index, item in enumerate(diagrams, start=1):
        section = "\n<CANDIDATE number=\"{}\" lines=\"{}-{}\">\n{}\n</CANDIDATE>"
        sections.append(
            section.format(
                index, item["start_line"], item["end_line"], item["context"]
            )
        )
    return "\n".join(sections)


def extract_rule_ascii_evidence(rfc_number, document, model_name=None):
    #find diagrams locally and return their combined evidence text
    diagrams = locate_ascii_packet_diagrams(document)
    if not diagrams:
        raise RuntimeError(
            "No packet-like ASCII diagram was found in RFC " + str(rfc_number) + "."
        )
    return format_rule_ascii_evidence(rfc_number, diagrams)
