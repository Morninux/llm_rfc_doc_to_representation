#generate and repair structured representations with one model

from ollama_client import run_model
from prompts import build_representation_prompt, build_representation_repair_prompt
from representation_validator import validate_representation_json


def generate_representation(model_name, evidence):
    #build the shared prompt and request one json response
    prompt = build_representation_prompt(evidence)
    answer = run_model(model_name, prompt, json_output=True)
    try:
        return validate_representation_json(answer)
    except ValueError as first_error:
        #give the model one opportunity to repair its response
        repair_prompt = build_representation_repair_prompt(
            prompt, answer, first_error
        )
        repaired = run_model(model_name, repair_prompt, json_output=True)
        try:
            return validate_representation_json(repaired)
        except ValueError as second_error:
            raise RuntimeError(
                "Model " + model_name
                + " failed the representation contract after one retry: "
                + str(second_error)
            ) from second_error
