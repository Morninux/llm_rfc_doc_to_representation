#save extraction results as json files with stable names

import json
import os
import re

from ollama_client import PROJECT_PATH


SAVEFILE_PATH = os.path.join(PROJECT_PATH, "savefile")


def safe_filename_part(value):
    #replace characters that are unsafe in result filenames
    safe_value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._")
    return safe_value or "unknown"


def serializable_output(answer):
    #store valid json as data and keep other responses as text
    if answer is None:
        raw_output = ""
    else:
        raw_output = str(answer)
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        return raw_output


def get_result_path(
    rfc_number, model_name, method, output_path=SAVEFILE_PATH, error=False
):
    #use one filename rule for exporting and batch resume checks
    filename = "rfc{}_{}_{}".format(
        safe_filename_part(str(rfc_number).strip()),
        safe_filename_part(model_name),
        safe_filename_part(str(method).strip().lower()),
    )
    if error:
        filename += "_error"
    filename += ".json"
    return os.path.join(output_path, filename)


def result_exists(rfc_number, model_name, method, output_path=SAVEFILE_PATH):
    #accept either a successful result or a saved validation error
    result_path = get_result_path(rfc_number, model_name, method, output_path)
    error_path = get_result_path(
        rfc_number, model_name, method, output_path, error=True
    )
    return os.path.isfile(result_path) or os.path.isfile(error_path)


def export_extraction_results(results, rfc_number, method, output_path=SAVEFILE_PATH):
    #write every successful model response to its own result file
    os.makedirs(output_path, exist_ok=True)
    exported_results = []
    for model_name, answer, _, error in results:
        #do not create a file when no model response is available
        if error and answer is None:
            exported_results.append((model_name, answer, None, error))
            continue
        try:
            result_path = get_result_path(
                rfc_number,
                model_name,
                method,
                output_path,
                error=bool(error),
            )
            exported_data = serializable_output(answer)
            with open(result_path, "w", encoding="utf-8", newline="\n") as file:
                json.dump(exported_data, file, ensure_ascii=False, indent=2)
                file.write("\n")
            exported_results.append((model_name, answer, result_path, error))
        except OSError as export_error:
            exported_results.append(
                (model_name, answer, None, "Export failed: " + str(export_error))
            )
    return exported_results
