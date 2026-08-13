import json
import os



def format_standardized():
    input_folder = "savefile"
    output_folder = "savefile/standardized_file"
    os.makedirs(output_folder, exist_ok=True)

    for name in os.listdir(input_folder):
        if name.endswith(".json"):
            with open(input_folder + "/" + name) as file:
                data = json.load(file)


