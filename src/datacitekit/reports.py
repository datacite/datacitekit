from collections import defaultdict
from extractors import extract_doi


class Aggregator:
    def __init__(self, base_connections):
        self.base_connections = base_connections
        aggregations = self.aggregations()
        self.type_connections = aggregations["type_connections"]
        self.type_counts = aggregations["type_counts"]
        self.people_counts = aggregations["people_counts"]
        self.org_counts = aggregations["org_counts"]
        self.full_people = aggregations["full_people"]
        self.full_orgs = aggregations["full_orgs"]

    def aggregations(self):
        resource_types = {
            entry["doi"]: entry["resource_type"] for entry in self.base_connections
        }
        type_connections = defaultdict(lambda: defaultdict(int))
        type_counts = defaultdict(int)
        people_counts = defaultdict(set)
        org_counts = defaultdict(set)
        full_people = set()
        full_orgs = set()
        for entry in self.base_connections:
            source_type = entry["resource_type"]
            type_counts[source_type] += 1
            people_counts[source_type].update(entry["orcid_ids"])
            org_counts[source_type].update(entry["ror_ids"])
            full_people.update(entry["orcid_ids"])
            full_orgs.update(entry["ror_ids"])
            for conn in entry["connections"]:
                target_type = resource_types[conn["related_doi"]]
                type_connections[source_type][target_type] += 1
        return {
            "type_connections": type_connections,
            "type_counts": type_counts,
            "people_counts": people_counts,
            "org_counts": org_counts,
            "full_people": full_people,
            "full_orgs": full_orgs,
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
            for related in entry.get("related_identifiers", []):
                related_doi = extract_doi(related["relatedIdentifier"])
                if related_doi in doi_index_map:
                    related_index = doi_index_map[related_doi]
                    connections.append(
                        {
                            "related_doi": related_doi,
                            "relation_type": related.get("relationType", "Unknown"),
                            "related_index": related_index,
                        }
                    )
            report.append(
                {
                    "doi": doi,
                    "index": index,
                    "connections": connections,
                    "resource_type": self._get_resource_type(entry).title(),
                    "orcid_ids": entry.get("orcid_ids", []),
                    "ror_ids": entry.get("ror_ids", []),
                }
            )
        return report

    def _get_resource_type(self, doi_attributes):
        return doi_attributes.get("resourceType") or doi_attributes.get(
            "resourceTypeGeneral", "Unknown"
        )

    @property
    def aggregate_counts(self):
        NODE_FIELD = "title"
        NODE_COUNT = "count"
        aggregate_report = []
        # Aggregate the counts for People
        aggregate_report.append(
            {NODE_FIELD: "People", NODE_COUNT: len(self.aggregator.full_people)}
        )
        # Aggregate the counts for Organizations
        aggregate_report.append(
            {NODE_FIELD: "Organizations", NODE_COUNT: len(self.aggregator.full_orgs)}
        )

        for resource_type, count in self.aggregator.type_counts.items():
            aggregate_report.append({NODE_FIELD: resource_type, NODE_COUNT: count})
        return aggregate_report

    @property
    def type_connection_report(self):
        EDGE_SOURCE_FIELD = "source"
        EDGE_TARGET_FIELD = "target"
        EDGE_COUNT_FIELD = "count"
        type_connections_report = []
        for source_type, targets in self.aggregator.type_connections.items():
            for target_type, weight in targets.items():
                type_connections_report.append(
                    {
                        EDGE_SOURCE_FIELD: source_type,
                        EDGE_TARGET_FIELD: target_type,
                        EDGE_COUNT_FIELD: weight,
                    }
                )

        for resource_type, count in self.aggregator.type_counts.items():
            people_count = len(self.aggregator.people_counts[resource_type])
            org_count = len(self.aggregator.org_counts[resource_type])
            # Add aggregates for connections between resource types and people
            if people_count > 0:
                type_connections_report.append(
                    {
                        EDGE_SOURCE_FIELD: resource_type,
                        EDGE_TARGET_FIELD: "People",
                        EDGE_COUNT_FIELD: people_count,
                    }
                )
            # Add aggregates for connections between resource types and organizations
            if org_count > 0:
                type_connections_report.append(
                    {
                        EDGE_SOURCE_FIELD: resource_type,
                        EDGE_TARGET_FIELD: "Organizations",
                        EDGE_COUNT_FIELD: org_count,
                    }
                )
            return type_connections_report
