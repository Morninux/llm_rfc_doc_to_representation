import argparse

from extraction_selector import run_selected_extraction, start_selection_input
from load_llm import ensure_ollama_server, load_models
from text_input import print_extraction_results


def _parse_arguments():
    parser = argparse.ArgumentParser(
        description="Convert an RFC into a structured packet representation."
    )
    parser.add_argument("rfc_number", nargs="?", help="RFC number, for example 768")
    parser.add_argument(
        "--method", choices=("full", "ascii"), default="full",
        help="full RFC extraction or locally located ASCII diagrams (default: full)",
    )
    parser.add_argument(
        "--model", default="all",
        help="ordered model number (1-based), or 0/all for every model (default: all)",
    )
    return parser.parse_args()


def main():
    args = _parse_arguments()
    try:
        ensure_ollama_server()
        model_list = load_models()
    except RuntimeError as error:
        print(error)
        return

    if len(model_list) == 0:
        print("No Ollama models were found.")
        return

    if args.rfc_number:
        try:
            results = run_selected_extraction(
                args.rfc_number, args.method, args.model, model_list
            )
            print_extraction_results(results)
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            print(error)
    else:
        try:
            start_selection_input(model_list)
        except ValueError as error:
            print(error)


if __name__ == "__main__":
    main()  #run the main function
