import json
import os
import re

from load_llm import PROJECT_PATH


SAVEFILE_PATH = os.path.join(PROJECT_PATH, "savefile")


def safe_filename_part(value):
    safe_value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._")
    return safe_value or "unknown"


def serializable_output(answer):
    if answer is None:
        raw_output = ""
    else:
        raw_output = str(answer)
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        return raw_output


def export_extraction_results(results, rfc_number, method, output_path=SAVEFILE_PATH):
    os.makedirs(output_path, exist_ok=True)
    number = safe_filename_part(str(rfc_number).strip())
    method_name = safe_filename_part(str(method).strip().lower())
    exported_results = []

    for model_name, answer, _, error in results:
        if error:
            exported_results.append((model_name, answer, None, error))
            continue
        try:
            filename = "rfc{}_{}_{}.json".format(
                number,
                safe_filename_part(model_name),
                method_name,
            )
            result_path = os.path.join(output_path, filename)
            exported_data = {
                "rfc": str(rfc_number).strip(),
                "model": model_name,
                "method": str(method).strip().lower(),
                "output": serializable_output(answer),
            }
            with open(result_path, "w", encoding="utf-8", newline="\n") as file:
                json.dump(exported_data, file, ensure_ascii=False, indent=2)
                file.write("\n")
            exported_results.append((model_name, answer, result_path, None))
        except OSError as export_error:
            exported_results.append(
                (model_name, answer, None, "Export failed: " + str(export_error))
            )
    return exported_results
