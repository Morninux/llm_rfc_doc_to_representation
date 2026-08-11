#provide evidence extractors for every supported extraction method

from extractors.full_extractor import extract_full_evidence
from extractors.llm_ascii_extractor import extract_llm_ascii_evidence
from extractors.rule_ascii_extractor import extract_rule_ascii_evidence


EVIDENCE_EXTRACTORS = {
    "full": extract_full_evidence,
    "ascii": extract_rule_ascii_evidence,
    "llm_ascii": extract_llm_ascii_evidence,
}
