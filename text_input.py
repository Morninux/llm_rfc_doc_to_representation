import os
import re

from load_llm import PROJECT_PATH, run_model


RFC_DOCUMENT_PATH = os.path.join(PROJECT_PATH, "rfc_document_set")
TEMPFILE_PATH = os.path.join(PROJECT_PATH, "tempfile")

RFC_EXTRACTION_INSTRUCTION = """You extract network packet-format diagrams from RFC documents.

Read the RFC document enclosed between <rfc_document> tags and return every ASCII
diagram that represents a network packet, message, header, option, or other
on-the-wire format. Include the field names shown in each diagram.

Output rules:
- Output only the ASCII diagrams and their field names.
- Preserve the diagrams' spacing, borders, labels, and line breaks exactly.
- Do not add Markdown fences, headings, explanations, summaries, or commentary.
- Do not include state diagrams, flow charts, examples, or unrelated artwork.
- If the document contains no matching diagram, return an empty response.

<rfc_document>
{document}
</rfc_document>
"""


def _safe_path_name(name):
    """Return a portable directory name for a model name."""
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return safe_name or "model"


def extract_rfc_packet_diagrams(
    rfc_number,
    model_list,
    document_path=RFC_DOCUMENT_PATH,
    output_path=TEMPFILE_PATH,
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
    prompt = RFC_EXTRACTION_INSTRUCTION.format(document=document)

    os.makedirs(output_path, exist_ok=True)
    results = []

    for model_name in model_list:
        model_output_path = os.path.join(output_path, _safe_path_name(model_name))
        os.makedirs(model_output_path, exist_ok=True)
        answer = run_model(model_name, prompt)
        result_path = os.path.join(model_output_path, "rfc" + number + ".txt")
        with open(result_path, "w", encoding="utf-8", newline="\n") as file:
            file.write(answer.strip())
            if answer.strip():
                file.write("\n")
        results.append((model_name, answer.strip(), result_path))

    return results


def print_extraction_results(results):
    """Print each model's ASCII diagram and the file containing it."""
    for model_name, answer, result_path in results:
        print("\n====================>> " + model_name + " <<====================")
        print(answer if answer else "(No packet-format diagram found.)")
        print("Saved to: " + result_path)


def send_to_all_models(user_text, model_list): #Send the same text to every model one by one
    for model_name in model_list:  #run models in order
        print("\n====================>> " + model_name + " <<====================")
        answer = run_model(model_name, user_text)  # get model answer
        print(answer)


def start_input(model_list):
    """Start a simple input loop."""
    print("Loaded local models: " + ", ".join(model_list))
    print("Enter an RFC number to extract packet diagrams, or type exit to stop.")

    while True:
        user_text = input("\nYou: ").strip()  #get user input

        if user_text.lower() == "exit":
            print("Stopped.")
            break

        if user_text != "":
            try:
                results = extract_rfc_packet_diagrams(user_text, model_list)
                print_extraction_results(results)
            except (ValueError, FileNotFoundError, RuntimeError) as error:
                print(error)
