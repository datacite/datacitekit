import re
from collections import defaultdict

from glom import Coalesce, Iter, glom

from .extractors import extract_doi


def camel_terms(value):
    return re.findall(
        "[A-Z][a-z]+|[0-9A-Z]+(?=[A-Z][a-z])|[0-9A-Z]{2,}|[a-z0-9]{2,}|[a-zA-Z0-9]",
        value,
    )


class Aggregator:
    def __init__(self, base_connections):
        self.base_connections = base_connections
        aggregations = self.aggregations()
        self.type_connections = aggregations["type_connections"]
        self.type_counts = aggregations["type_counts"]

    def aggregations(self):
        resource_types = {
            entry["doi"]: entry["resource_type"] for entry in self.base_connections
        }
        type_connections = defaultdict(lambda: defaultdict(int))
        type_counts = defaultdict(int)
        for entry in self.base_connections:
            source_type = entry["resource_type"]
            type_counts[source_type] += 1
            for conn in entry["connections"]:
                target_type = resource_types[conn["related_doi"]]
                type_connections[source_type][target_type] += 1
        return {
            "type_connections": type_connections,
            "type_counts": type_counts,
        }


class RelatedWorkReports:
    def __init__(self, data):
        self.data = data
        self.base_connections = self._base_connections()
        self.aggregator = Aggregator(self.base_connections)

    @staticmethod
    def is_a_doi(related):
        return bool(extract_doi(related.get("relatedIdentifier", "")))

    @staticmethod
    def parser(doi_result):
        doi_result = doi_result.get("attributes", {}) or doi_result
        if not doi_result:
            return {}
        spec = {
            "doi": ("doi"),
            "resourceTypeGeneral": Coalesce("types.resourceTypeGeneral", default=""),
            "resourceType": Coalesce("types.resourceType", default=""),
            "related_identifiers": Coalesce(
                (
                    "relatedIdentifiers",
                    Iter().filter(lambda r: RelatedWorkReports.is_a_doi(r)).all(),
                ),
                default=[],
            ),
        }
        return glom(doi_result, spec)

    def _base_connections(self):
        dois = self.data.keys()
        report = []
        for doi, entry in self.data.items():
            connections = []
            for related in entry.get("related_identifiers", []):
                related_doi = extract_doi(related["relatedIdentifier"])
                if related_doi in dois:
                    connections.append(
                        {
                            "related_doi": related_doi,
                            "relation_type": related.get("relationType", "Unknown"),
                        }
                    )
            report.append(
                {
                    "doi": doi,
                    "connections": connections,
                    "resource_type": self._get_resource_type(entry),
                }
            )
        return report

    def _is_a_project(self, doi_attributes):
        return doi_attributes.get("resourceType", "Unknown") == "Project" and (
            doi_attributes.get("resourceTypeGeneral", "Unknown")
            in [
                "Other",
                "Text",
            ]
        )

    def _get_resource_type(self, doi_attributes):
        if self._is_a_project(doi_attributes):
            return "Project"
        return " ".join(
            camel_terms(doi_attributes.get("resourceTypeGeneral", "Unknown"))
        )

    @property
    def aggregate_counts(self):
        NODE_FIELD = "title"
        NODE_COUNT = "count"
        aggregate_report = []
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

        return type_connections_report
