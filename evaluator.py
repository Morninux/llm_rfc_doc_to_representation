import json
import os
import Levenshtein
import nltk.translate.bleu_score

def ANLS(reference, standardized_test_file):
    with open(reference, "r", encoding="utf-8") as file:
        rf = json.load(file) #reference file

    nls_list = [] #list of normalized levenshtein similarities
    for name in os.listdir(standardized_test_file):
        if not name.endswith(".json"):
            continue

        with open(standardized_test_file + "/" + name, "r", encoding="utf-8") as file:
            stf = json.load(file) #standardized test file

        #nomalized_levenshtein_similarity = 1 - Levenshtein_Distance(doc_test, doc_real) / max(len(doc_test), len(doc_real))
        nls = 1 - (Levenshtein.distance(rf, stf) / max(len(rf), len(stf)))
        nls_list.append(nls)
        print(name, nls)

    anls = sum(nls_list) / len(nls_list) #average normalized levenshtein similarity
    return anls


