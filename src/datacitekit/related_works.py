# coding: utf-8

from .extractors import extract_doi
from .resource_type_graph import RelatedWorkReports
from .searchers import DoiListSearcher, DoiSearcher
from .utils import camel_to_hyphen_case, group_by, merge_list_dicts


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


def summarize_connections(doi, data):
    from collections import defaultdict

    # summary = defaultdict(list)
    outgoing, incoming = defaultdict(list), defaultdict(list)

    # Check each item in the data
    for item in data:
        # If the item's DOI matches the target DOI
        if item["doi"] == doi:
            connections = item["connections"]
            # Group connections by relation_type
            for connection in connections:
                relation_type = connection["relation_type"]
                related_doi = connection["related_doi"]
                outgoing[relation_type].append(related_doi)

        # Check if the target DOI appears as a related_doi in connections
        for connection in item["connections"]:
            if connection["related_doi"] == doi:
                relation_type = connection["relation_type"]
                item_doi = item["doi"]
                incoming[relation_type].append(item_doi)

    summary = {"outgoing": outgoing, "incoming": incoming}

    return summary


def set_source_and_target_doi(subj_id, obj_id, relation_type_id):
    """
    Determines source and target DOIs and relation types based on the input IDs and relation type.

    Args:
        subj_id: The subject DOI or identifier.
        obj_id: The object DOI or identifier.
        relation_type_id: The identifier for the relationship type.

    Returns:
        A dictionary containing the source DOI, target DOI, source relation type, and target relation type,
        or None if there are missing IDs or an unhandled relation type.
    """

    if not subj_id or not obj_id:
        print(f"Warning: Missing ID - subject: {subj_id}, object: {obj_id}")
        return None

    RELATION_MAPPING = {
        # Citation relations
        "cites": ("references", "citations"),
        "is-supplemented-by": ("references", "citations"),
        "references": ("references", "citations"),
        "is-cited-by": ("citations", "references"),
        "is-supplement-to": ("citations", "references"),
        "is-referenced-by": ("citations", "references"),
        # Version relations
        "has-version": ("versions", "version_of"),
        "is-version-of": ("version_of", "versions"),
        # Part relations
        "has-part": ("parts", "part_of"),
        "is-part-of": ("part_of", "parts"),
        # Documentation relations
        "documents": ("documents", "is_documented_by"),
        "is-documented-by": ("is_documented_by", "documents"),
        # Derivation relations
        "is-source-of": ("sources", "derived_from"),
        "is-derived-from": ("derived_from", "sources"),
        # Continuation relations
        "continues": ("continues", "continued_by"),
        "is-continued-by": ("continued_by", "continues"),
        # Requirement relations
        "requires": ("requires", "is_required_by"),
        "is-required-by": ("is_required_by", "requires"),
    }

    result = {
        "source_doi": None,
        "target_doi": None,
        "source_relation_type_id": None,
        "target_relation_type_id": None,
    }

    if relation_type_id in RELATION_MAPPING:
        source_rel, target_rel = RELATION_MAPPING[relation_type_id]
        # Relations where the subject is the source
        if relation_type_id in (
            "cites",
            "is-supplemented-by",
            "references",
            "has-version",
            "has-part",
            "documents",
            "is-source-of",
            "continues",
            "requires",
        ):
            result["source_doi"] = subj_id
            result["target_doi"] = obj_id
        else:  # Relations where the object is the source
            result["source_doi"] = obj_id
            result["target_doi"] = subj_id
        result["source_relation_type_id"] = source_rel
        result["target_relation_type_id"] = target_rel
    else:
        print(f"Warning: Unhandled relation type: {relation_type_id}")
        return None

    return result


def convert_to_source_target_format(data):
    converted = []
    for item in data:
        source = item["doi"]
        for connection in item["connections"]:
            target = connection["related_doi"]
            relationship_type = camel_to_hyphen_case(connection["relation_type"])
            result = set_source_and_target_doi(source, target, relationship_type)
            if result is not None:
                converted.append(result)
    return converted


def relations_to_doi(data, doi):
    source_target = convert_to_source_target_format(data)

    # Helper function to get DOIs for a specific relation type
    def get_outgoing_dois(relation_type):
        return [
            d["target_doi"]
            for d in source_target
            if d["source_doi"] == doi and d["source_relation_type_id"] == relation_type
        ]

    def get_incoming_dois(relation_type):
        return [
            d["source_doi"]
            for d in source_target
            if d["target_doi"] == doi and d["target_relation_type_id"] == relation_type
        ]

    return {
        # Original relations
        "references": get_outgoing_dois("references"),
        "parts": get_outgoing_dois("parts"),
        "citations": get_incoming_dois("citations"),
        "part_of": get_incoming_dois("part_of"),
        # New relations
        "versions": get_outgoing_dois("versions"),
        "version_of": get_outgoing_dois("version_of"),
        "documents": get_outgoing_dois("documents"),
        "is_documented_by": get_outgoing_dois("is_documented_by"),
        "sources": get_outgoing_dois("sources"),
        "derived_from": get_outgoing_dois("derived_from"),
        "continues": get_outgoing_dois("continues"),
        "continued_by": get_outgoing_dois("continued_by"),
        "requires": get_outgoing_dois("requires"),
        "is_required_by": get_outgoing_dois("is_required_by"),
    }


def doi_related_works(doi_query, connections):
    source_target = convert_to_source_target_format(connections)
    s_with_doi = (
        stpair for stpair in source_target if stpair["source_doi"] == doi_query
    )
    t_with_doi = (
        stpair for stpair in source_target if stpair["target_doi"] == doi_query
    )
    sources_grouped = group_by(s_with_doi, "source_relation_type_id")
    source_group_dois = dict(
        [(k, [d["target_doi"] for d in v]) for k, v in sources_grouped.items()]
    )
    targets_grouped = group_by(t_with_doi, "target_relation_type_id")
    target_group_dois = dict(
        [(k, [d["source_doi"] for d in v]) for k, v in targets_grouped.items()]
    )
    merged = merge_list_dicts(source_group_dois, target_group_dois)

    return merged


if __name__ == "__main__":
    from pprint import pprint

    DOI_API = "https://api.stage.datacite.org/dois/"
    DOI_API = "https://api.datacite.org/dois/"
    doi_query = _get_query()
    full_doi_attributes = get_full_corpus_doi_attributes(
        doi_query, RelatedWorkReports.parser, DOI_API
    )
    report = RelatedWorkReports(full_doi_attributes)

    pprint(report.base_connections)
    pprint(" --- Summary --- ")
    pprint(summarize_connections(doi_query, report.base_connections))

    # pprint(" --- relations to doi --- ")
    # pprint(relations_to_doi(report.base_connections, doi_query))
    # relations = relations_to_doi(report.base_connections, doi_query)
    #
    # pprint("--- Summary Count --- ")
    # pprint(
    #     dict(
    #         [
    #             (relation, len(values))
    #             for relation, values in relations.items()
    #             if values
    #         ]
    #     )
    # )
    merged = doi_related_works(doi_query, report.base_connections)
    merged_counts = dict(
        [(relation, len(values)) for relation, values in merged.items() if values]
    )
    pprint(" --- Merged --- ")
    pprint(merged)
    total = 0
    pprint(" --- Merged counts --- ")
    for relation, count in merged_counts.items():
        pprint("{}: {}".format(relation, count))
        total += count
    pprint("all: {}".format(total))

    # graph = {"nodes": report.aggregate_counts, "edges": report.type_connection_report}
    # print(json.dumps(graph, indent=4))
