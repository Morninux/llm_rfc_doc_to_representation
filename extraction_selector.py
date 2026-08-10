
from ascii_diagram_input import extract_rfc_from_ascii_diagrams
from llm_ascii_diagram_input import extract_rfc_from_llm_ascii_diagrams
from load_llm import is_cloud_model
from output_export import export_extraction_results
from text_input import extract_rfc_packet_diagrams, print_extraction_results


def ordered_models(model_list):
    #remove duplicate names while keeping one entry per model
    models = []
    for model_name in model_list:
        if model_name not in models:
            models.append(model_name)
    models.sort(key=str.lower)
    return models


def select_models(model_list, selection):
    #support all, a one-based number, or an exact model name
    models = ordered_models(model_list)
    value = str(selection).strip()
    if value == "0" or value.lower() == "all":
        return models
    if value.isdigit():
        index = int(value) - 1
        if 0 <= index < len(models):
            return [models[index]]
    if value in models:
        return [value]
    raise ValueError(
        "Model number must be between 0 and " + str(len(models)) + "."
    )


def run_selected_extraction(rfc_number, method, model_selection, model_list): #run one extraction method with selected models
    #normalize and validate the requested method
    method_name = str(method).strip().lower()
    if method_name not in ("full", "ascii", "llm_ascii"):
        raise ValueError("Extraction method must be 'full', 'ascii', or 'llm_ascii'.")
    selected_models = select_models(model_list, model_selection)
    #call the matching extraction pipeline
    if method_name == "full":
        results = extract_rfc_packet_diagrams(rfc_number, selected_models)
    elif method_name == "ascii":
        results = extract_rfc_from_ascii_diagrams(rfc_number, selected_models)
    elif method_name == "llm_ascii":
        results = extract_rfc_from_llm_ascii_diagrams(rfc_number, selected_models)
    return export_extraction_results(results, rfc_number, method_name)


def start_selection_input(model_list): #interactively select a method, models, and rfc numbers
    #show models in the same order used by numeric selection
    models = ordered_models(model_list)

    print("Extraction methods:")
    print("  1) Full RFC")
    print("  2) ASCII packet diagrams")
    print("  3) LLM-located ASCII packet diagrams")
    print("Available Ollama models (ordered by name):")
    print("  0) All models")
    #label cloud models separately from local models
    for index, model_name in enumerate(models, start=1):
        location = "local"
        if is_cloud_model(model_name):
            location = "cloud"
        print("  " + str(index) + ") " + model_name + " [" + location + "]")

    #repeat the method question until the input is valid
    while True:
        method_input = input("Choose method [1/2/3]: ").strip().lower()
        if method_input == "1" or method_input == "full":
            method = "full"
            break
        elif method_input == "2" or method_input == "ascii":
            method = "ascii"
            break
        elif method_input == "3" or method_input == "llm_ascii":
            method = "llm_ascii"
            break
        else:
            print("Unknown extraction method: " + method_input)
            print("Please enter 1, 2, 3, full, ascii, or llm_ascii.")

    #repeat the model question until the selection is valid
    while True:
        try:
            selected = select_models(
                models, input("Choose model number [0-" + str(len(models)) + "]: ")
            )
            break
        except ValueError as error:
            print(error)
    print("Using method: " + method + "; model(s): " + ", ".join(selected))

    #accept multiple rfc numbers until the user exits
    while True:
        rfc_number = input("\nRFC number (or exit): ").strip()
        if rfc_number.lower() == "exit":
            print("Stopped.")
            return
        if not rfc_number:
            continue
        try:
            if method == "full":
                results = extract_rfc_packet_diagrams(rfc_number, selected)
            elif method == "ascii":
                results = extract_rfc_from_ascii_diagrams(rfc_number, selected)
            elif method == "llm_ascii":
                results = extract_rfc_from_llm_ascii_diagrams(rfc_number, selected)
            else:
                print("Unknown extraction method: " + method)
                continue
            results = export_extraction_results(results, rfc_number, method)
            print_extraction_results(results)
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            print(error)
