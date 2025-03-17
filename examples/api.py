import itertools
import os
from collections import defaultdict

from datacitekit.doi_relations import DoiRelationRelatonsReport
from datacitekit.extractors import extract_doi
from datacitekit.related_works import get_full_corpus_doi_attributes
from datacitekit.resource_type_graph import RelatedWorkReports
from flask import Flask, jsonify

DOI_API = os.getenv("DOI_API", "https://api.stage.datacite.org/dois/")
app = Flask(__name__)


@app.route("/doi/related-graph/<path:doi>", methods=["GET"])
def related_graph(doi):
    doi = extract_doi(doi)
    if not doi:
        return jsonify({"error": "Does not match DOI format"}), 400

    full_doi_attributes = get_full_corpus_doi_attributes(
        doi, RelatedWorkReports.parser, DOI_API
    )
    if not full_doi_attributes:
        return jsonify({"error": "DOI not found"}), 404

    report = RelatedWorkReports(full_doi_attributes)
    return jsonify(
        {
            "nodes": report.aggregate_counts,
            "edges": report.type_connection_report,
        }
    )


def transpose_defaultdict(my_dict):
    transposed = defaultdict(list)
    for key, values in my_dict.items():
        for value in values:
            transposed[value].append(key)
    return dict(transposed)


@app.route("/doi/connections/<path:doi>", methods=["GET"])
def connections(doi):
    doi = extract_doi(doi)
    if not doi:
        return jsonify({"error": "Does not match DOI format"}), 400

    full_doi_attributes = get_full_corpus_doi_attributes(
        doi, RelatedWorkReports.parser, DOI_API
    )
    if not full_doi_attributes:
        return jsonify({"error": "DOI not found"}), 404

    report = DoiRelationRelatonsReport(full_doi_attributes)
    relations = report.relations_to_doi(doi)
    relation_counts = dict(
        [(relation, len(values)) for relation, values in relations.items() if values]
    )
    all_relations = transpose_defaultdict(relations)

    return jsonify(
        {
            "relations": relations,
            "counts": relation_counts,
            "all_relations:": all_relations,
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
