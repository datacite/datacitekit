# coding: utf-8
import requests
import re

# String matches the regular expression for a doi

def extract_doi(doi_string):
    doi_regex = re.compile(r'^(?:https?://doi\.org/)?(10\.\d{4,9}/[-._;()/:A-Z0-9]+)$', re.I)
    matches = doi_regex.match(doi_string.lower())
    return matches.group(1) if matches else None

def is_a_doi(rid):
    return bool(extract_doi(rid.get("relatedIdentifier", "")))
    # If either the relatedIdentifierType is DOI or the relatedIdentifier matches the regular expression for a doi
# return rid.get("relatedIdentifierType") == "DOI" or re.match(DOI_REGEX, rid.get("relatedIdentifier"))

def get_related_dois(data):
    related = data.get("relatedIdentifiers", [])
    related_dois = [r for r in related if is_a_doi(r)]
    return related_dois


def get_relation_types_grouped_by_doi(related_dois):
    res = {}
    for r in related_dois:
        r_doi = extract_doi(r.get("relatedIdentifier", ""))
        r_type = r["relationType"]
        res[r_doi] = [r_type] if r_doi not in res.keys() else res[r_doi] + [r_type]
    return res


def get_doi_data(doi):
    response = requests.get(f"https://api.datacite.org/dois/{doi}")
    if response.ok:
        return response.json()["data"]["attributes"]
    else:
        return {}


# def outgoing_dois_and_relations(doi):
#     data = get_doi_data(doi)
#     related_dois = get_related_dois(data)
#     relation_types_grouped_by_doi = get_relation_types_grouped_by_doi(related_dois)
#     return relation_types_grouped_by_doi

def doi_permutations(doi):
    return " OR ".join([
        f'"{doi}"',
        f'"https://doi.org/{doi}"',
        f'"http://doi.org/{doi}"'
    ])

def search_params(doi, page=1):
    return {
            "query": doi_permutations(doi),
        "disable_facets": "true",
        "page[size]": 100,
        "page[number]": page,
    }


def data_for_page(doi, page):
    response = requests.get(
        "https://api.datacite.org/dois/",
        params=search_params(doi, page)
    )
    return response.json()
    if response.ok:
        return response.json()
    else:
        return {}


def search_for_doi(doi):
    data = []
    page = 1
    response = data_for_page(doi, page)
    if response:
        data += response["data"]
        total_pages = response["meta"]["totalPages"]
        if total_pages > 1:
            for page in range(2, total_pages + 1):
                response = data_for_page(doi, page)
                data += response["data"]
    return data



def all_relations(doi):
    d_list = search_for_doi(doi)
    id_dois = {d["id"]: get_related_dois(d["attributes"]) for d in d_list}
    id_dois2 = {
        k: [vv for vv in v if extract_doi(vv.get("relatedIdentifier", "")) == doi or k == doi]
        for k, v in id_dois.items()
    }
    return {
        k.lower(): get_relation_types_grouped_by_doi(v) for k, v in id_dois2.items()
    }


def get_relations(doi):
    a_relations = all_relations(doi)
    o_relations = a_relations.pop(doi, {})
    i_relations = {k: v.get(doi, []) for k, v in a_relations.items()}
    all_dois = set(o_relations.keys()) | set(i_relations.keys())
    return {
        "doi": doi,
        "incoming": i_relations,
        "outgoing": o_relations,
        "related_dois": all_dois,
    }



def second_order_relations(doi):
    primary_relations = get_relations(doi)
    related_dois = primary_relations.get("related_dois", [])
    return [get_relations(d) for d in related_dois]


if __name__ == "__main__":
    from pprint import pprint
    import sys

    if len(sys.argv) < 2:
        print("Usage: python related_works.py <doi>")
        sys.exit(1)

    arguments = sys.argv[1:]

    query = arguments[0]

    # relations = all_relations(query)
    # pprint(all_relations(query))
    relations = get_relations(query)

    pprint(relations)
    # pprint(relations.get("incoming"))
    r_dois = relations.get("related_dois")
    pprint(len(list(r_dois)))
    #
    # dois_OR = " OR ".join( r_dois)
    # pprint(
    #         # f"{r_dois}"
    #     list(r_dois)
    # )

    # INTERESTED_ATTRIBUTES=[
    #     'doi',
    #     'types',
    #     'creators',
    #     'contributors',
    # ]
    # from glom import glom
    # for d in r_dois:
    #     doi_data = get_doi_data(d)
    #     pprint(
    #             glom(doi_data,
    #                  ('doi', 'types.resourceTypeGeneral')
    #                  )
    #     # { k: doi_data.get(k) for k in INTERESTED_ATTRIBUTES}
    #     )
    # pprint(get_relations(query))
    # pprint(second_order_relations(query))
