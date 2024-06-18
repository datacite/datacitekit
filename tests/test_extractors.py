# test_extractors.py
from datacitekit.extractors import extract_orcid, extract_doi, extract_ror_id

def test_extract_orcid():
    assert extract_orcid("https://orcid.org/0000-0002-1825-0097") == "0000-0002-1825-0097"
    assert extract_orcid("0000-0002-1825-0097") == "0000-0002-1825-0097"
    assert extract_orcid("invalid-orcid") is None

def test_extract_doi():
    assert extract_doi("https://doi.org/10.1000/xyz123") == "10.1000/xyz123"
    assert extract_doi("10.1000/xyz123") == "10.1000/xyz123"
    assert extract_doi("invalid-doi") is None

def test_extract_ror_id():
    assert extract_ror_id("https://ror.org/012345678") == "https://ror.org/012345678"
    assert extract_ror_id("ror.org/012345678") == "https://ror.org/012345678"
    assert extract_ror_id("invalid-ror") is None

#
# def test_get_relation_types_grouped_by_doi():
#     related_dois = [
#         {"relatedIdentifier": "10.1000/xyz123", "relationType": "IsCitedBy"},
#         {"relatedIdentifier": "10.1000/xyz123", "relationType": "Cites"}
#     ]
#     expected = {
#         "10.1000/xyz123": ["IsCitedBy", "Cites"]
#     }
#     assert get_relation_types_grouped_by_doi(related_dois) == expected
