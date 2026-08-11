#load and discover rfc documents from the project document folder

import os

from ollama_client import PROJECT_PATH


RFC_DOCUMENT_PATH = os.path.join(PROJECT_PATH, "rfc_document_set")


def validate_rfc_number(rfc_number):
    #normalize the number before building a filename
    number = str(rfc_number).strip()
    if not number.isdigit():
        raise ValueError("RFC number must contain digits only: " + number)
    return number


def get_rfc_path(rfc_number, document_path=RFC_DOCUMENT_PATH):
    #validate the folder and return the expected source path
    number = validate_rfc_number(rfc_number)
    if not os.path.isdir(document_path):
        raise FileNotFoundError("RFC document folder not found: " + document_path)
    source_path = os.path.join(document_path, "rfc" + number + ".txt")
    if not os.path.isfile(source_path):
        raise FileNotFoundError("RFC document not found: " + source_path)
    return source_path


def load_rfc_document(rfc_number, document_path=RFC_DOCUMENT_PATH):
    #read one rfc and return its normalized number with the document text
    number = validate_rfc_number(rfc_number)
    source_path = get_rfc_path(number, document_path)
    with open(source_path, "r", encoding="utf-8", errors="replace") as file:
        document = file.read()
    return number, document


def discover_rfc_numbers(limit=None, document_path=RFC_DOCUMENT_PATH):
    #collect filenames that use the rfc<number>.txt format
    if not os.path.isdir(document_path):
        raise FileNotFoundError("RFC document folder not found: " + document_path)
    numbers = []
    for filename in os.listdir(document_path):
        lower_filename = filename.lower()
        if not lower_filename.startswith("rfc"):
            continue
        if not lower_filename.endswith(".txt"):
            continue
        number_text = filename[3:-4]
        if number_text.isdigit():
            numbers.append(int(number_text))

    #sort numerically before applying the optional limit
    numbers.sort()
    if limit is not None:
        numbers = numbers[:limit]
    results = []
    for number in numbers:
        results.append(str(number))
    return results
