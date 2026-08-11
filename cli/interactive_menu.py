#collect interactive choices and call the shared extraction runner

from extraction_runner import METHODS, run_extraction
from ollama_client import is_cloud_model
from result_exporter import export_extraction_results


def ordered_models(model_list):
    #remove duplicate model names and return stable ordering
    models = []
    for model_name in model_list:
        if model_name not in models:
            models.append(model_name)
    models.sort(key=str.lower)
    return models


def select_models(model_list, selection):
    #accept all, a one-based number, or one exact model name
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


def choose_method():
    #repeat until the user selects one registered extraction method
    print("Extraction methods:")
    print("  1) Full RFC")
    print("  2) ASCII packet diagrams")
    print("  3) LLM-located ASCII packet diagrams")
    choices = {"1": "full", "2": "ascii", "3": "llm_ascii"}
    while True:
        value = input("Choose method [1/2/3]: ").strip().lower()
        if value in choices:
            return choices[value]
        if value in METHODS:
            return value
        print("Unknown extraction method: " + value)
        print("Please enter 1, 2, 3, full, ascii, or llm_ascii.")


def choose_models(models):
    #show model locations and repeat until the selection is valid
    print("Available Ollama models (ordered by name):")
    print("  0) All models")
    for index, model_name in enumerate(models, start=1):
        location = "local"
        if is_cloud_model(model_name):
            location = "cloud"
        print("  " + str(index) + ") " + model_name + " [" + location + "]")
    while True:
        try:
            value = input("Choose model number [0-" + str(len(models)) + "]: ")
            return select_models(models, value)
        except ValueError as error:
            print(error)


def print_extraction_results(results):
    #show saved paths or individual model errors
    for model_name, answer, result_path, error in results:
        print("\n====================>> " + model_name + " <<====================")
        if error:
            print("Error: " + error)
            if result_path:
                print("Saved invalid output: " + result_path)
        elif result_path:
            print("Saved: " + result_path)
        else:
            print(answer)


def start_interactive_menu(model_list):
    #collect one method and model selection before accepting rfc numbers
    models = ordered_models(model_list)
    method = choose_method()
    selected_models = choose_models(models)
    print("Using method: " + method + "; model(s): " + ", ".join(selected_models))

    #accept rfc numbers until the user exits
    while True:
        rfc_number = input("\nRFC number (or exit): ").strip()
        if rfc_number.lower() == "exit":
            print("Stopped.")
            return
        if not rfc_number:
            continue
        try:
            results = run_extraction(rfc_number, method, selected_models)
            exported = export_extraction_results(results, rfc_number, method)
            print_extraction_results(exported)
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            print(error)
