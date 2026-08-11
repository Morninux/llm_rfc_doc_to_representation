#generate and repair structured representations with one model

from ollama_client import run_model
from prompts import build_representation_prompt, build_representation_repair_prompt
from representation_validator import validate_representation_json


class RepresentationGenerationError(RuntimeError):
    #keep invalid model output available for error export
    def __init__(self, model_name, answer, reason):
        message = (
            "Model " + model_name
            + " failed the representation contract after one retry: "
            + str(reason)
        )
        super().__init__(message)
        self.answer = answer


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
        try:
            repaired = run_model(model_name, repair_prompt, json_output=True)
        except RuntimeError as repair_error:
            raise RepresentationGenerationError(
                model_name, answer, repair_error
            ) from repair_error
        try:
            return validate_representation_json(repaired)
        except ValueError as second_error:
            raise RepresentationGenerationError(
                model_name, repaired, second_error
            ) from second_error
