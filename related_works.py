# coding: utf-8
import requests
import re


ROR_PREFIX = "https://ror.org/"

def extract_orcid(orcid_string):
    orcid_regex = re.compile(r'(?:https?://orcid\.org/)?(\b\d{4}-\d{4}-\d{4}-\d{3}[0-9X]\b)', re.I)
    matches = orcid_regex.match(orcid_string)
    return matches.group(1) if matches else None

def extract_doi(doi_string):
    doi_regex = re.compile(
        r"^(?:https?://doi\.org/)?(10\.\d{4,9}/[-._;()/:A-Z0-9]+)$", re.I
    )
    matches = doi_regex.match(doi_string.lower())
    return matches.group(1) if matches else None

def extract_ror_id(ror_string):
    """Extracts ROR id from a string and transforms it into canonical form"""
    ror_regex = re.compile( r"^(?:(?:(?:http|https):\/\/)?ror\.org\/)?(0\w{6}\d{2})$")
    matches = ror_regex.match(ror_string)
    return ROR_PREFIX + matches.group(1) if matches else None

def is_a_doi(rid):
    return bool(extract_doi(rid.get("relatedIdentifier", "")))


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


class DataCiteSearcher:
    def __init__(self, search_url="https://api.datacite.org/dois/", query=""):
        self.search_query = query
        self.search_url = search_url

    def search_params(self, page=1, query=""):
        return {
            "query": query or self.search_query,
            "disable_facets": "true",
            "page[size]": 100,
            "page[number]": page,
        }

    def data_for_page(self, page):
        response = requests.get(self.search_url, params=self.search_params(page))
        if response.ok:
            return response.json()
        else:
            return {}

    def search(self):
        data = []
        page = 1
        response = self.data_for_page(page)
        if response:
            data += response["data"]
            total_pages = response["meta"]["totalPages"]
            if total_pages > 1:
                for page in range(2, total_pages + 1):
                    response = self.data_for_page(page)
                    data += response["data"]
        return data

class DoiSearcher(DataCiteSearcher):
    def __init__(self, doi, search_url="https://api.datacite.org/dois/"):
        self.doi = extract_doi(doi)
        super().__init__(search_url, self.doi_search_query)

    @property
    def doi_permutations(self):
        doi = self.doi
        return [f'"{doi}"', f'"https://doi.org/{doi}"', f'"http://doi.org/{doi}"']

    @property
    def doi_search_query(self):
        return " OR ".join(self.doi_permutations)


class DoiListSearcher(DataCiteSearcher):
    def __init__(self, doi_list, search_url="https://api.datacite.org/dois/"):
        self.doi_list = self._verified_doi_list(doi_list)
        super().__init__(search_url, self.doi_list_query)

    @property
    def doi_list_query(self):
        return "uid:(" + " OR ".join(self.doi_list) + ")"

    def _verified_doi_list(self, raw_doi_list):
        temp_list = ( extract_doi(doi) for doi in raw_doi_list)
        return [doi for doi in temp_list if doi is not None]

def get_doi_data(doi):
    response = requests.get(f"https://api.datacite.org/dois/{doi}")
    if response.ok:
        return response.json()["data"]["attributes"]
    else:
        return {}


def get_other_attributes(doi_attributes):
    from glom import glom, Iter
    doi_attributes =  doi_attributes.get("attributes", {}) or doi_attributes
    if not doi_attributes:
        return {}
    spec = {
            "doi":('doi'),
            'resourceTypeGeneral':('types.resourceTypeGeneral'),
            'resourceType':('types.resourceType'),
            'creator_ids':('creators', [('nameIdentifiers',(['nameIdentifier']))],Iter().flatten().all()),
            'orcid_ids':('creators', [('nameIdentifiers',(['nameIdentifier']))],Iter().flatten().
                         map(lambda x: extract_orcid(x)).
                         filter(lambda x : x is not None).all()),
            'contributor_ids':('contributors', [('nameIdentifiers',(['nameIdentifier']))],Iter().flatten().all()),
            'ror_ids':('contributors',
                       [('nameIdentifiers',(['nameIdentifier']))],Iter().flatten().
                       map(lambda x: extract_ror_id(x)).
                       filter(lambda x : x is not None).
                       all()
                       ),
            'related_identifiers':('relatedIdentifiers', Iter().
                                   filter(lambda r : is_a_doi(r)).
                                   all()),
            }
    return glom(doi_attributes, spec)

def all_relations(d_list, doi):
    d_attributes = {d["id"]: get_other_attributes(d["attributes"]) for d in d_list}
    # pprint(d_attributes)
    id_dois = {d["id"]: get_related_dois(d["attributes"]) for d in d_list}
    id_dois2 = {
        k: [
            vv
            for vv in v
            if extract_doi(vv.get("relatedIdentifier", "")) == doi or k == doi
        ]
        for k, v in id_dois.items()
    }
    return {
        k.lower(): get_relation_types_grouped_by_doi(v) for k, v in id_dois2.items()
    }


def get_relations(doi):
    doi_list = DoiSearcher(doi).search()
    a_relations = all_relations(doi_list, doi)
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


def _get_query():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python related_works.py <doi>")
        sys.exit(1)
    arguments = sys.argv[1:]
    query = arguments[0]
    return query

if __name__ == "__main__":
    from pprint import pprint

    query = _get_query()

    relations = get_relations(query)
    pprint(relations)
    outgoing = relations.get("outgoing")
    searcher = DoiListSearcher(outgoing.keys())
    outgoing_data = searcher.search()
    for doi_data in outgoing_data:
        pprint( get_other_attributes(doi_data) )
