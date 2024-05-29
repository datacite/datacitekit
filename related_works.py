# coding: utf-8
import requests
import re
from collections import defaultdict


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
    related = data.get("related_identifiers", [])
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


def parse_attributes(doi_result):
    from glom import glom, Iter
    doi_result =  doi_result.get("attributes", {}) or doi_result
    if not doi_result:
        return {}
    spec = {
            "doi":('doi'),
            'resourceTypeGeneral':('types.resourceTypeGeneral'),
            'resourceType':('types.resourceType'),
            'orcid_ids':('creators', [('nameIdentifiers',(['nameIdentifier']))],Iter().flatten().
                         map(lambda x: extract_orcid(x)).
                         filter(lambda x : x is not None).
                         all()
                         ),
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
    return glom(doi_result, spec)

def all_relations(d_attributes, doi):
    id_dois = {d: get_related_dois(attributes) for d, attributes in d_attributes.items()}
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


def get_relations(d_attributes, doi):
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

class Aggregator:
    def __init__(self, base_connections):
        self.base_connections = base_connections
        aggregations = self.aggregations()
        self.type_connections = aggregations['type_connections']
        self.type_counts = aggregations['type_counts']
        self.people_counts = aggregations['people_counts']
        self.org_counts = aggregations['org_counts']
        self.full_people = aggregations['full_people']
        self.full_orgs = aggregations['full_orgs']

    def aggregations(self):
        resource_types = {entry['doi']: entry['resource_type'] for entry in self.base_connections}
        type_connections = defaultdict(lambda: defaultdict(int))
        type_counts = defaultdict(int)
        people_counts = defaultdict(set)
        org_counts = defaultdict(set)
        full_people = set()
        full_orgs = set()
        for entry in self.base_connections:
            source_type = entry['resource_type']
            # source_type = resource_types[entry['doi']]
            type_counts[source_type] += 1
            people_counts[source_type].update(entry['orcid_ids'])
            org_counts[source_type].update(entry['ror_ids'])
            full_people.update(entry['orcid_ids'])
            full_orgs.update(entry['ror_ids'])
            for conn in entry['connections']:
                target_type = resource_types[conn['related_doi']]
                type_connections[source_type][target_type] += 1
        return{
            'type_connections': type_connections,
            'type_counts': type_counts,
            'people_counts': people_counts,
            'org_counts': org_counts,
            'full_people': full_people,
            'full_orgs': full_orgs
        }


class RelatedWorkReports:
    def __init__(self, data):
        self.data = data
        self.base_connections = self._base_connections()
        self.aggregator = Aggregator(self.base_connections)

    def _base_connections(self):
        dois = list(self.data.keys())
        doi_index_map = {doi: index for index, doi in enumerate(dois)}
        report = []
        for doi, entry in self.data.items():
            index = doi_index_map[doi]
            connections = []
            for related in entry.get('related_identifiers', []):
                related_doi = extract_doi(related['relatedIdentifier'])
                if related_doi in doi_index_map:
                    related_index = doi_index_map[related_doi]
                    connections.append({
                        'related_doi': related_doi,
                        'relation_type': related.get('relationType', 'Unknown'),
                        'related_index': related_index
                    })
            report.append({
                'doi': doi,
                'index': index,
                'connections': connections,
                'resource_type': self._get_resource_type(entry).title(),
                'orcid_ids': entry.get('orcid_ids', []),
                'ror_ids': entry.get('ror_ids', [])
            })
        return report

    def _get_resource_type(self, doi_attributes):
        return doi_attributes.get('resourceType') or  doi_attributes.get('resourceTypeGeneral', 'Unknown')


    @property
    def aggregate_counts(self):
        NODE_FIELD = "title"
        NODE_COUNT = "count"
        aggregate_report = []
        # Aggregate the counts for People
        aggregate_report.append({
            NODE_FIELD: 'People',
            NODE_COUNT: len(self.aggregator.full_people)
        })
        # Aggregate the counts for Organizations
        aggregate_report.append({
            NODE_FIELD: 'Organizations',
            NODE_COUNT: len(self.aggregator.full_orgs)
        })

        for resource_type, count in self.aggregator.type_counts.items():
            aggregate_report.append({
                NODE_FIELD: resource_type,
                NODE_COUNT: count
            })
        return aggregate_report

    @property
    def type_connection_report(self):
        EDGE_SOURCE_FIELD = "source"
        EDGE_TARGET_FIELD = "target"
        EDGE_COUNT_FIELD = "count"
        type_connections_report = []
        for source_type, targets in self.aggregator.type_connections.items():
            for target_type, weight in targets.items():
                type_connections_report.append({
                    EDGE_SOURCE_FIELD: source_type,
                    EDGE_TARGET_FIELD: target_type,
                    EDGE_COUNT_FIELD: weight
                })

        for resource_type, count in self.aggregator.type_counts.items():
            people_count = len(self.aggregator.people_counts[resource_type])
            org_count = len(self.aggregator.org_counts[resource_type])
            # Add aggregates for connections between resource types and people
            if people_count > 0:
                type_connections_report.append({
                    EDGE_SOURCE_FIELD: resource_type,
                    EDGE_TARGET_FIELD: 'People',
                    EDGE_COUNT_FIELD: people_count
                })
            # Add aggregates for connections between resource types and organizations
            if org_count > 0:
                type_connections_report.append({
                    EDGE_SOURCE_FIELD: resource_type,
                    EDGE_TARGET_FIELD: 'Organizations',
                    EDGE_COUNT_FIELD: org_count
                })
            return type_connections_report

if __name__ == "__main__":
    from pprint import pprint

    doi_query = _get_query()

    # Get full list
    doi_list = DoiSearcher(doi_query).search()
    # Parse Attributes
    doi_attributes = {d["id"]: parse_attributes(d) for d in doi_list}
    # Get the primary doi
    primary_doi = doi_attributes.get(doi_query)
    relations_grouped_by_doi = get_relation_types_grouped_by_doi(get_related_dois(primary_doi))
    # Get Outgoing
    outgoing_dois = relations_grouped_by_doi.keys()
    # Search outgoing links
    outgoing_doi_list = DoiListSearcher(outgoing_dois).search()
    # Parse Attributes of Outgoing DOIs
    outgoing_doi_attributes = {d["id"]: parse_attributes(d) for d in outgoing_doi_list}

    # Add lists to get full corpus of attributes
    full_doi_attributes = {**doi_attributes, **outgoing_doi_attributes}
    # Get corupus of outgoing and incoming keys
    full_doi_keys = full_doi_attributes.keys()

    # Generate a report on the connections
    report = RelatedWorkReports(full_doi_attributes)
    pprint(report.base_connections)
    pprint(report.aggregate_counts)
    pprint(report.type_connection_report)
