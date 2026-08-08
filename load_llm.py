import json
import os
import urllib.error
import urllib.request


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"  #local ollama address
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))  #get project path
MODELS_PATH = os.path.join(PROJECT_PATH, "models")  #get local models path


def load_models(): #find all complete local models in the models folder
    manifest_path = os.path.join(MODELS_PATH, "manifests")
    blob_path = os.path.join(MODELS_PATH, "blobs")
    model_list = []  #save local model names

    if not os.path.isdir(manifest_path):
        return model_list

    for root, folders, files in os.walk(manifest_path):  #read every manifest file
        for file_name in files:
            file_path = os.path.join(root, file_name)

            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    model_data = json.load(file)  #read model information
            except (OSError, json.JSONDecodeError):
                continue

            local_model = False
            for layer in model_data.get("layers", []):
                if layer.get("mediaType") == "application/vnd.ollama.image.model":
                    digest = layer.get("digest", "").replace(":", "-")
                    if os.path.isfile(os.path.join(blob_path, digest)):
                        local_model = True  #model weights exist locally

            if local_model:
                model_name = os.path.basename(root)
                model_tag = file_name
                if model_tag != "latest":
                    model_name = model_name + ":" + model_tag
                model_list.append(model_name)

    model_list.sort()  #keep the output order simple
    return model_list


def run_model(model_name, user_text): #send text to one local Ollama model
    request_data = {
        "model": model_name,
        "prompt": user_text,
        "stream": False,
    }
    json_data = json.dumps(request_data).encode("utf-8")  #make request data

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json_data,
        headers={"Content-Type": "application/json"},
    )

    try:
        response = urllib.request.urlopen(request)  #call local ollama
        result = json.loads(response.read().decode("utf-8"))
        response.close()
        return result.get("response", "")
    except urllib.error.URLError as error:
        return "[error] " + str(error)  #return a simple error message
