#run selected rfc documents through every model and method combination

import argparse
import os
import sys
import time

from ascii_diagram_input import extract_rfc_from_ascii_diagrams
from llm_ascii_diagram_input import extract_rfc_from_llm_ascii_diagrams
from extraction_selector import ordered_models
from load_llm import PROJECT_PATH, ensure_ollama_server, load_models
from output_export import SAVEFILE_PATH, export_extraction_results, safe_filename_part
from text_input import extract_rfc_packet_diagrams


RFC_DOCUMENT_PATH = os.path.join(PROJECT_PATH, "rfc_document_set")
METHODS = ("full", "ascii", "llm_ascii")
EXPECTED_MODEL_COUNT = 10
RFC_LIMIT = 10


def discover_rfc_numbers(document_path=RFC_DOCUMENT_PATH, limit=RFC_LIMIT):
    #store the rfc numbers found in the document folder
    documents = []

    #check every file in the document folder
    for filename in os.listdir(document_path):
        lower_filename = filename.lower()

        #ignore files that do not use the rfc<number>.txt name format
        if not lower_filename.startswith("rfc"):
            continue
        if not lower_filename.endswith(".txt"):
            continue

        #get the number between rfc and .txt
        number_text = filename[3:-4]
        if not number_text.isdigit():
            continue

        documents.append(int(number_text))

    documents.sort()

    #convert the first numbers back to text for the extraction functions
    selected_numbers = []
    for number in documents[:limit]:
        selected_numbers.append(str(number))
    return selected_numbers


def result_path(output_path, rfc_number, model_name, method):
    #use safe names because model names may contain special characters
    filename = "rfc{}_{}_{}.json".format(
        safe_filename_part(rfc_number),
        safe_filename_part(model_name),
        safe_filename_part(method),
    )
    return os.path.join(output_path, filename)


def result_exists(output_path, rfc_number, model_name, method):
    #check whether this model and method already produced a result
    path = result_path(output_path, rfc_number, model_name, method)
    return os.path.isfile(path)


def count_existing_results(models, rfc_numbers, output_path):
    #count finished results before the batch starts
    count = 0
    for rfc_number in rfc_numbers:
        for method in METHODS:
            for model_name in models:
                if result_exists(output_path, rfc_number, model_name, method):
                    count += 1
    return count


def parse_arguments():
    #read optional settings from the command line
    parser = argparse.ArgumentParser(
        description=(
            "Test the numerically first 50 RFC files with 10 Ollama models "
            "using the full, rule-based ASCII, and LLM-based ASCII methods."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=SAVEFILE_PATH,
        help="directory for result JSON files (default: %(default)s)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="rerun combinations whose result JSON already exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show the selected RFCs/models and total work without running models",
    )
    return parser.parse_args()


def run_batch(models, rfc_numbers, output_path, overwrite=False):
    #calculate how many model calls will be made
    total = len(models) * len(rfc_numbers) * len(METHODS)

    #store progress information
    completed = 0
    skipped = 0
    failed = 0
    started = time.monotonic()

    #run every rfc with both methods and every model
    for rfc_number in rfc_numbers:
        for method in METHODS:
            #choose the extraction function for the current method
            if method == "full":
                extractor = extract_rfc_packet_diagrams
            elif method == "ascii":
                extractor = extract_rfc_from_ascii_diagrams
            else:
                extractor = extract_rfc_from_llm_ascii_diagrams

            for model_name in models:
                completed += 1
                prefix = "[{}/{}] RFC {} | {} | {}".format(
                    completed, total, rfc_number, method, model_name
                )

                #skip finished work unless overwrite was requested
                if not overwrite and result_exists(
                    output_path, rfc_number, model_name, method
                ):
                    skipped += 1
                    print(prefix + " - skipped (result exists)", flush=True)
                    continue

                print(prefix + " - running", flush=True)
                try:
                    #run one model so an error does not affect other models
                    results = extractor(rfc_number, [model_name])

                    #save the returned result as a json file
                    exported = export_extraction_results(
                        results, rfc_number, method, output_path=output_path
                    )

                    #read an error returned by the extraction function
                    if exported:
                        error = exported[0][3]
                    else:
                        error = "No result returned"

                    if error:
                        failed += 1
                        print(prefix + " - failed: " + str(error), flush=True)
                    else:
                        print(prefix + " - complete", flush=True)
                except Exception as error:  #keep a long benchmark running
                    failed += 1
                    print(prefix + " - failed: " + str(error), flush=True)

    #show the final result of the complete batch
    elapsed = time.monotonic() - started
    succeeded = total - skipped - failed
    print(
        "Finished: {} succeeded, {} skipped, {} failed, {:.1f}s elapsed.".format(
            succeeded, skipped, failed, elapsed
        )
    )
    if failed > 0:
        return 1
    return 0


def main():
    #load the command line settings and the first 50 rfc numbers
    args = parse_arguments()
    try:
        rfc_numbers = discover_rfc_numbers()
    except OSError as error:
        print("Failed to read RFC documents: " + str(error), file=sys.stderr)
        return 1

    if len(rfc_numbers) < RFC_LIMIT:
        print(
            "Expected at least {} RFC documents, found {}.".format(
                RFC_LIMIT, len(rfc_numbers)
            ),
            file=sys.stderr,
        )
        return 1

    #start ollama and load the available models
    try:
        ensure_ollama_server()
        models = ordered_models(load_models())
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1

    if len(models) != EXPECTED_MODEL_COUNT:
        model_text = ", ".join(models)
        if not model_text:
            model_text = "none"
        print(
            "Expected exactly {} Ollama models, found {}: {}".format(
                EXPECTED_MODEL_COUNT, len(models), model_text
            ),
            file=sys.stderr,
        )
        return 1

    #show exactly what will be tested before starting
    total = len(rfc_numbers) * len(models) * len(METHODS)
    print("RFCs ({}): {}".format(len(rfc_numbers), ", ".join(rfc_numbers)))
    print("Models ({}): {}".format(len(models), ", ".join(models)))
    print("Methods: " + ", ".join(METHODS))
    print("Total runs: {}".format(total))

    #show how many model calls can be skipped
    if not args.overwrite:
        existing = count_existing_results(models, rfc_numbers, args.output_dir)
        print("Existing results to skip: {}".format(existing))

    if args.dry_run:
        return 0

    #create the output folder and start the full batch
    os.makedirs(args.output_dir, exist_ok=True)
    return run_batch(models, rfc_numbers, args.output_dir, args.overwrite)


if __name__ == "__main__":
    raise SystemExit(main())
