# coding: utf-8
from glom import glom, Iter, Coalesce
from extractors import (
    extract_doi,
    extract_orcid,
    extract_ror_id,
)
from searchers import DoiListSearcher, DoiSearcher
from reports import RelatedWorkReports


def is_a_doi(rid):
    return bool(extract_doi(rid.get("relatedIdentifier", "")))


def parse_attributes(doi_result):
    doi_result = doi_result.get("attributes", {}) or doi_result
    if not doi_result:
        return {}
    spec = {
        "doi": ("doi"),
        "resourceTypeGeneral": Coalesce("types.resourceTypeGeneral", default=''),
        "resourceType": Coalesce("types.resourceType", default=''),
        "orcid_ids": (
            "creators",
            [("nameIdentifiers", (["nameIdentifier"]))],
            Iter()
            .flatten()
            .map(lambda x: extract_orcid(x))
            .filter(lambda x: x is not None)
            .all(),
        ),
        "ror_ids": (
            "contributors",
            [("nameIdentifiers", (["nameIdentifier"]))],
            Iter()
            .flatten()
            .map(lambda x: extract_ror_id(x))
            .filter(lambda x: x is not None)
            .all(),
        ),
        "related_identifiers": (
            "relatedIdentifiers",
            Iter().filter(lambda r: is_a_doi(r)).all(),
        ),
    }
    return glom(doi_result, spec)

def parse_list(doi_list):
    return {d["id"]: parse_attributes(d) for d in doi_list}

def get_relation_types_grouped_by_doi(related_dois):
    res = {}
    for r in related_dois:
        r_doi = extract_doi(r.get("relatedIdentifier", ""))
        r_type = r["relationType"]
        res[r_doi] = [r_type] if r_doi not in res.keys() else res[r_doi] + [r_type]
    return res

def get_outgoing_link_attributes(primary_doi):
    relations_grouped_by_doi = get_relation_types_grouped_by_doi(
        primary_doi.get("related_identifiers", [])
    )
    # Get outgoing links
    outgoing_dois = relations_grouped_by_doi.keys()
    outgoing_doi_list = DoiListSearcher(outgoing_dois).search()
    outgoing_doi_attributes = parse_list(outgoing_doi_list)
    return outgoing_doi_attributes

def _get_query():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python related_works.py <doi>")
        sys.exit(1)
    arguments = sys.argv[1:]
    query = arguments[0]
    return query


def get_full_corpus_doi_attributes(doi_query):
    # Get incoming links and primary doi
    doi_list = DoiSearcher(doi_query).search()
    doi_attributes = parse_list(doi_list)
    if doi_query in doi_attributes.keys():
        primary_doi = doi_attributes.get(doi_query, {})
        outgoing_doi_attributes = get_outgoing_link_attributes(primary_doi)
    else:
        outgoing_doi_attributes = {}

    # Add lists to get full corpus of attributes
    full_doi_attributes = {**doi_attributes, **outgoing_doi_attributes}
    return full_doi_attributes


if __name__ == "__main__":
    import json

    doi_query = _get_query()
    full_doi_attributes = get_full_corpus_doi_attributes(doi_query)
    report = RelatedWorkReports(full_doi_attributes)

    graph = {"nodes": report.aggregate_counts, "edges": report.type_connection_report}
    print(json.dumps(graph, indent=4))
