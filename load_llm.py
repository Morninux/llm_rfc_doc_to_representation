import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"  #local ollama address
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))  #get project path
MODELS_PATH = os.path.join(PROJECT_PATH, "models")  #get local models path
OLLAMA_HEALTH_URL = "http://127.0.0.1:11434/api/tags"


def find_ollama_executable(): #find the local Ollama executable without invoking a cloud service
    executable = shutil.which("ollama")
    if executable:
        return executable

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", "")
    candidates = [
        os.path.join(local_app_data, "Programs", "Ollama", "ollama.exe"),
        os.path.join(local_app_data, "Ollama", "ollama.exe"),
        os.path.join(program_files, "Ollama", "ollama.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path

    if local_app_data:
        return candidates[0]
    return None


def _ollama_is_running():
    try:
        with urllib.request.urlopen(OLLAMA_HEALTH_URL, timeout=1):
            return True
    except (urllib.error.URLError, TimeoutError):
        return False


def ensure_ollama_server(startup_timeout=20): #start the local Ollama server when it is not already running
    if _ollama_is_running():
        return

    executable = find_ollama_executable()
    if not executable:
        raise RuntimeError(
            "Ollama is not running and ollama.exe could not be found. "
            "Install Ollama or add it to PATH."
        )

    environment = os.environ.copy()
    environment["OLLAMA_MODELS"] = MODELS_PATH
    #Ollama is a console application. On Windows, CREATE_NO_WINDOW prevents
    #its server from flashing CMD windows
    creation_flags = (
        getattr(subprocess, "CREATE_NO_WINDOW", 0)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    )
    try:
        subprocess.Popen(
            [executable, "serve"],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
    except OSError as error:
        raise RuntimeError("Failed to start local Ollama: " + str(error)) from error

    deadline = time.monotonic() + startup_timeout
    while time.monotonic() < deadline:
        if _ollama_is_running():
            return
        time.sleep(0.25)

    raise RuntimeError(
        "Local Ollama did not start within " + str(startup_timeout) + " seconds."
    )


def load_models(): #return every model Ollama can call, including signed-in cloud models
    ensure_ollama_server()
    try:
        with urllib.request.urlopen(OLLAMA_HEALTH_URL, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError("Failed to list Ollama models: " + str(error)) from error

    model_list = []
    for model_data in result.get("models", []):
        model_name = model_data.get("name")
        if not model_name:
            model_name = model_data.get("model")
        if isinstance(model_name, str):
            model_name = model_name.strip()
            if model_name and model_name not in model_list:
                model_list.append(model_name)

    model_list.sort(key=str.lower)
    return model_list


def is_cloud_model(model_name): #return whether an Ollama model name represents a cloud model
    return str(model_name).lower().endswith(":cloud")


def run_model(model_name, user_text, json_output=False): #send text to any local or cloud model registered with Ollama
    available_models = load_models()
    if model_name not in available_models:
        available_text = "none"
        if available_models:
            available_text = ", ".join(available_models)
        raise RuntimeError(
            "Ollama model is not available: " + model_name
            + ". Available models: " + available_text
        )

    request_data = {
        "model": model_name,
        "prompt": user_text,
        "stream": False,
    }
    if json_output: #Ollama constrains decoding to syntactically valid JSON. Semantic validation is still performed by the extraction layer.
        request_data["format"] = "json"
    json_data = json.dumps(request_data).encode("utf-8")  #make request data

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json_data,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=300) as response:  #call local ollama
            result = json.loads(response.read().decode("utf-8"))
        return result.get("response", "")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(
            "Failed to run model " + model_name + ": " + str(error)
        ) from error
