import sys

from load_llm import load_models
from text_input import (
    extract_rfc_packet_diagrams,
    print_extraction_results,
    start_input,
)


def main():
    model_list = load_models()  #load local model names

    if len(model_list) == 0:
        print("No local models were found.")
        return

    if len(sys.argv) > 1:
        rfc_number = sys.argv[1]
        try:
            results = extract_rfc_packet_diagrams(rfc_number, model_list)
            print_extraction_results(results)
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            print(error)
    else:
        start_input(model_list)  #start keyboard input


if __name__ == "__main__":
    main()  #run the main function
