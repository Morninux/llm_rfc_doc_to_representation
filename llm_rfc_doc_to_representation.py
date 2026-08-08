import sys

from load_llm import load_models
from text_input import send_to_all_models, start_input


def main():
    model_list = load_models()  #load local model names

    if len(model_list) == 0:
        print("No local models were found.")
        return

    if len(sys.argv) > 1:
        user_text = " ".join(sys.argv[1:])  #read text from command line
        send_to_all_models(user_text, model_list)
    else:
        start_input(model_list)  #start keyboard input


if __name__ == "__main__":
    main()  #run the main function
