from load_llm import run_model


def send_to_all_models(user_text, model_list): #Send the same text to every model one by one
    for model_name in model_list:  #run models in order
        print("\n====================>> " + model_name + " <<====================")
        answer = run_model(model_name, user_text)  # get model answer
        print(answer)


def start_input(model_list):
    """Start a simple input loop."""
    print("Loaded local models: " + ", ".join(model_list))
    print("Type exit to stop.")

    while True:
        user_text = input("\nYou: ").strip()  #get user input

        if user_text.lower() == "exit":
            print("Stopped.")
            break

        if user_text != "":
            send_to_all_models(user_text, model_list)  #run every local model
