import json
import os

def format_standardized():
    input_folder = "savefile"
    output_folder = "savefile/standardized_file"
    os.makedirs(output_folder, exist_ok=True)

    for name in os.listdir(input_folder):
        if name.endswith(".json"):
            with open(input_folder + "/" + name, "r") as file:
                data = file.read()

            data = data.lower().replace("_", " ")

            with open(output_folder + "/" + name, "w") as file:
                file.write(data)
