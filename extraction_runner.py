#run every extraction method through one shared model loop

from extractors import EVIDENCE_EXTRACTORS
from representation_generator import (
    RepresentationGenerationError,
    generate_representation,
)
from rfc_loader import load_rfc_document


METHODS = tuple(EVIDENCE_EXTRACTORS.keys())


def normalize_method(method):
    #validate a method before selecting its evidence extractor
    method_name = str(method).strip().lower()
    if method_name not in EVIDENCE_EXTRACTORS:
        raise ValueError(
            "Extraction method must be 'full', 'ascii', or 'llm_ascii'."
        )
    return method_name


def run_extraction(rfc_number, method, model_names):
    #load the source once and choose the registered evidence extractor
    method_name = normalize_method(method)
    number, document = load_rfc_document(rfc_number)
    evidence_extractor = EVIDENCE_EXTRACTORS[method_name]

    #run models independently so one failure does not stop the batch
    results = []
    for model_name in model_names:
        try:
            evidence = evidence_extractor(number, document, model_name)
            answer = generate_representation(model_name, evidence)
            results.append((model_name, answer, None, None))
        except RepresentationGenerationError as error:
            #preserve invalid output so it can be exported with an error suffix
            results.append((model_name, error.answer, None, str(error)))
        except (RuntimeError, ValueError) as error:
            results.append((model_name, None, None, str(error)))
    return results
