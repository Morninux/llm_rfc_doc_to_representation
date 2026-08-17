import json
import os

def format_standardized():
    input_folder = "savefile"
    output_folder = "savefile/standardized_file"
    os.makedirs(output_folder, exist_ok=True)

    for name in os.listdir(input_folder):
        if name.endswith(".json"):
            with open(input_folder + "/" + name, "r", encoding="utf-8") as file:
                data = json.load(file)

            data = json.dumps(data)
            data = data.lower().replace("_", " ")

            with open(output_folder + "/" + name, "w", encoding="utf-8") as file:
                file.write(data)

if __name__ == "__main__":
    format_standardized()