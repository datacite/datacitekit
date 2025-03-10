from .extractors import extract_doi
from .utils import camel_to_hyphen_case, group_by, merge_list_dicts


class DoiRelationRelatonsReport:
    """
    Reports relationships between DOIs.
    """

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

    def __init__(self, data):
        """
        Initialize with connection data.

        Args:
            connections: List of DOI connection data
        """
        self.data = data
        self.connections = self._base_connections()
        self._source_target_format = None

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
                }
            )
        return report

    @staticmethod
    def _set_source_and_target_doi(subj_id, obj_id, relation_type_id):
        """
        Determines source and target DOIs and relation types based on the input IDs and relation type.

        Args:
            subj_id: The subject DOI or identifier
            obj_id: The object DOI or identifier
            relation_type_id: The identifier for the relationship type

        Returns:
            A dictionary containing the source DOI, target DOI, source relation type, and target relation type,
            or None if there are missing IDs or an unhandled relation type
        """
        if not subj_id or not obj_id:
            print(f"Warning: Missing ID - subject: {subj_id}, object: {obj_id}")
            return None

        result = {
            "source_doi": None,
            "target_doi": None,
            "source_relation_type_id": None,
            "target_relation_type_id": None,
        }

        if relation_type_id in DoiRelationRelatonsReport.RELATION_MAPPING:
            source_rel, target_rel = DoiRelationRelatonsReport.RELATION_MAPPING[
                relation_type_id
            ]
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

    @property
    def source_target_format(self):
        """
        Convert connection data to source-target format, caching the result.

        Returns:
            List of dictionaries with source and target DOI information
        """
        if self._source_target_format is None:
            self._source_target_format = self._convert_to_source_target_format()
        return self._source_target_format

    def _convert_to_source_target_format(self):
        """
        Convert the raw connection data to source-target format.

        Returns:
            List of dictionaries with source and target DOI information
        """
        converted = []
        for item in self.connections:
            source = item["doi"]
            for connection in item["connections"]:
                target = connection["related_doi"]
                relationship_type = camel_to_hyphen_case(connection["relation_type"])
                result = self._set_source_and_target_doi(
                    source, target, relationship_type
                )
                if result is not None:
                    converted.append(result)
        return converted

    def relations_to_doi(self, doi):
        """
        Get all relations for a specific DOI.

        Args:
            doi: The DOI to get relations for

        Returns:
            A dictionary mapping relation types to lists of related DOIs
        """
        s_with_doi = (
            stpair
            for stpair in self.source_target_format
            if stpair["source_doi"] == doi
        )
        t_with_doi = (
            stpair
            for stpair in self.source_target_format
            if stpair["target_doi"] == doi
        )

        sources_grouped = group_by(s_with_doi, "source_relation_type_id")
        source_group_dois = dict(
            [(k, [d["target_doi"] for d in v]) for k, v in sources_grouped.items()]
        )

        targets_grouped = group_by(t_with_doi, "target_relation_type_id")
        target_group_dois = dict(
            [(k, [d["source_doi"] for d in v]) for k, v in targets_grouped.items()]
        )

        return merge_list_dicts(source_group_dois, target_group_dois)
