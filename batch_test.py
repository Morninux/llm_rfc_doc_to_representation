#run selected rfc documents through every model and method combination

import argparse
import os
import sys
import time

from cli.interactive_menu import ordered_models
from extraction_runner import METHODS, run_extraction
from ollama_client import ensure_ollama_server, load_models
from result_exporter import (
    SAVEFILE_PATH,
    export_extraction_results,
    result_exists,
)
from rfc_loader import discover_rfc_numbers


EXPECTED_MODEL_COUNT = 10
RFC_LIMIT = 10


def parse_arguments():
    #read optional batch settings from the command line
    parser = argparse.ArgumentParser(
        description=(
            "Test RFC files with 10 Ollama models using every registered "
            "extraction method."
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
        help="show selected work without running models",
    )
    return parser.parse_args()


def count_existing_results(models, rfc_numbers, output_path):
    #count exact result files that can be skipped
    count = 0
    for rfc_number in rfc_numbers:
        for method in METHODS:
            for model_name in models:
                if result_exists(rfc_number, model_name, method, output_path):
                    count += 1
    return count


def run_batch(models, rfc_numbers, output_path, overwrite=False):
    #calculate progress totals for all combinations
    total = len(models) * len(rfc_numbers) * len(METHODS)
    completed = 0
    skipped = 0
    failed = 0
    started = time.monotonic()

    #use the shared runner for every individual combination
    for rfc_number in rfc_numbers:
        for method in METHODS:
            for model_name in models:
                completed += 1
                prefix = "[{}/{}] RFC {} | {} | {}".format(
                    completed, total, rfc_number, method, model_name
                )
                if not overwrite and result_exists(
                    rfc_number, model_name, method, output_path
                ):
                    skipped += 1
                    print(prefix + " - skipped (result exists)", flush=True)
                    continue

                print(prefix + " - running", flush=True)
                try:
                    results = run_extraction(rfc_number, method, [model_name])
                    exported = export_extraction_results(
                        results, rfc_number, method, output_path
                    )
                    if exported:
                        error = exported[0][3]
                    else:
                        error = "No result returned"
                    if error:
                        failed += 1
                        print(prefix + " - failed: " + str(error), flush=True)
                    else:
                        print(prefix + " - complete", flush=True)
                except Exception as error:  #keep a long batch running
                    failed += 1
                    print(prefix + " - failed: " + str(error), flush=True)

    #show final batch counts and elapsed time
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
    #load the selected rfc numbers before starting ollama
    args = parse_arguments()
    try:
        rfc_numbers = discover_rfc_numbers(RFC_LIMIT)
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

    #start ollama and load the exact benchmark model set
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

    #show work and resume information before model calls begin
    total = len(rfc_numbers) * len(models) * len(METHODS)
    print("RFCs ({}): {}".format(len(rfc_numbers), ", ".join(rfc_numbers)))
    print("Models ({}): {}".format(len(models), ", ".join(models)))
    print("Methods: " + ", ".join(METHODS))
    print("Total runs: {}".format(total))
    if not args.overwrite:
        existing = count_existing_results(models, rfc_numbers, args.output_dir)
        print("Existing results to skip: {}".format(existing))
    if args.dry_run:
        return 0

    #create the output folder and start the batch
    os.makedirs(args.output_dir, exist_ok=True)
    return run_batch(models, rfc_numbers, args.output_dir, args.overwrite)


if __name__ == "__main__":
    raise SystemExit(main())
