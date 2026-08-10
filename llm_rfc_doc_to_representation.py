from extraction_selector import start_selection_input
from load_llm import ensure_ollama_server, load_models


def main():
    #start ollama and discover all available models
    try:
        ensure_ollama_server()
        model_list = load_models()
    except RuntimeError as error:
        print(error)
        return

    #stop before opening the menu when no models are available
    if not model_list:
        print("No Ollama models were found.")
        return

    #always open the interactive method and model menu
    try:
        start_selection_input(model_list)
    except ValueError as error:
        print(error)


if __name__ == "__main__":
    main()  #run the main function
