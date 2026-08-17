#generate structured representations with one model

from ollama_client import run_model
from prompts import build_representation_prompt


class RepresentationGenerationError(RuntimeError):
    #keep invalid model output available for error export
    def __init__(self, model_name, answer, reason):
        message = ("Model " + model_name + " failed the representation contract after one retry: " + str(reason))
        super().__init__(message)
        self.answer = answer


def generate_representation(model_name, evidence):
    #build the shared prompt and request one json response
    prompt = build_representation_prompt(evidence)
    return run_model(model_name, prompt, json_output=True)
