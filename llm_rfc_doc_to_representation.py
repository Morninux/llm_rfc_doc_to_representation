from cli.interactive_menu import start_interactive_menu
from ollama_client import ensure_ollama_server, load_models


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
    start_interactive_menu(model_list)


if __name__ == "__main__":
    main()  #run the main function
