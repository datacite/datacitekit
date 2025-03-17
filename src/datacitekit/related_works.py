# coding: utf-8

from .doi_relations import DoiRelationRelatonsReport
from .extractors import extract_doi
from .resource_type_graph import RelatedWorkReports
from .searchers import DoiListSearcher, DoiSearcher


def get_relation_types_grouped_by_doi(related_dois):
    res = {}
    for r in related_dois:
        r_doi = extract_doi(r.get("relatedIdentifier", ""))
        r_type = r["relationType"]
        res[r_doi] = [r_type] if r_doi not in res.keys() else res[r_doi] + [r_type]
    return res


def parse_list(doi_list, parser):
    return {d["id"]: parser(d) for d in doi_list}


def get_incoming_and_primary_attributes(doi_query, doi_url, parser):
    # Get incoming links and primary doi
    doi_list = DoiSearcher(doi_query, doi_url).search()
    doi_attributes = parse_list(doi_list, parser)
    return doi_attributes


def get_outgoing_link_attributes(primary_doi, doi_url, parser):
    relations_grouped_by_doi = get_relation_types_grouped_by_doi(
        primary_doi.get("related_identifiers", [])
    )
    # Get outgoing links
    outgoing_dois = relations_grouped_by_doi.keys()
    outgoing_doi_list = DoiListSearcher(outgoing_dois, doi_url).search()
    outgoing_doi_attributes = parse_list(outgoing_doi_list, parser)
    return outgoing_doi_attributes


def get_full_corpus_doi_attributes(
    doi_query, parser, api_url="https://api.stage.datacite.org/dois/"
):
    doi_attributes = get_incoming_and_primary_attributes(doi_query, api_url, parser)
    if doi_query in doi_attributes.keys():
        primary_doi = doi_attributes.get(doi_query, {})
        outgoing_doi_attributes = get_outgoing_link_attributes(
            primary_doi, api_url, parser
        )
    else:
        outgoing_doi_attributes = {}

    # Add lists to get full corpus of attributes
    full_doi_attributes = {**doi_attributes, **outgoing_doi_attributes}
    return full_doi_attributes


def _get_query():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python related_works.py <doi>")
        sys.exit(1)
    arguments = sys.argv[1:]
    query = arguments[0]
    return query


if __name__ == "__main__":
    import os
    from pprint import pprint

    DOI_API = os.getenv("DOI_API", "https://api.stage.datacite.org/dois/")
    doi_query = _get_query()
    full_doi_attributes = get_full_corpus_doi_attributes(
        doi_query, RelatedWorkReports.parser, DOI_API
    )
    report = DoiRelationRelatonsReport(full_doi_attributes)
    relations = report.relations_to_doi(doi_query)

    relation_counts = dict(
        [(relation, len(values)) for relation, values in relations.items() if values]
    )
    pprint(" --- Merged counts --- ")
    for relation, count in relation_counts.items():
        pprint("{}: {}".format(relation, count))
    total = sum(relation_counts.values())
    pprint("all: {}".format(total))

    # graph = {"nodes": report.aggregate_counts, "edges": report.type_connection_report}
    # print(json.dumps(graph, indent=4))
