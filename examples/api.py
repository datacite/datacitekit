import os

from datacitekit.extractors import extract_doi
from datacitekit.related_works import get_full_corpus_doi_attributes
from datacitekit.reports import RelatedWorkReports
from flask import Flask, jsonify

DOI_API = os.getenv("DOI_API", "https://api.stage.datacite.org/dois/")
app = Flask(__name__)


@app.route("/doi/related-graph/<path:doi>", methods=["GET"])
def related_works(doi):
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


if __name__ == "__main__":
    app.run(debug=True)
