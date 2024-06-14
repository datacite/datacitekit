import re

ROR_PREFIX = "https://ror.org/"

def extract_orcid(orcid_string):
    """Extracts ORCID from a string and transforms it into canonical form"""
    if not orcid_string:
        return None
    orcid_regex = re.compile(
        r"(?:https?://orcid\.org/)?(\b\d{4}-\d{4}-\d{4}-\d{3}[0-9X]\b)", re.I
    )
    matches = orcid_regex.match(orcid_string)
    return matches.group(1) if matches else None


def extract_doi(doi_string):
    """Extracts DOI from a string and transforms it into canonical form"""
    if not doi_string:
        return None
    doi_regex = re.compile(
        r"^(?:https?://doi\.org/)?(10\.\d{4,9}/[-._;()/:A-Z0-9]+)$", re.I
    )
    matches = doi_regex.match(doi_string.lower())
    return matches.group(1) if matches else None


def extract_ror_id(ror_string):
    """Extracts ROR id from a string and transforms it into canonical form"""
    if not ror_string:
        return None
    ror_regex = re.compile(r"^(?:(?:(?:http|https):\/\/)?ror\.org\/)?(0\w{6}\d{2})$")
    matches = ror_regex.match(ror_string)
    return ROR_PREFIX + matches.group(1) if matches else None
