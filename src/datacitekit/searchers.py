import requests

from .extractors import extract_doi


class DataCiteSearcher:
    def __init__(
        self, search_url="https://api.datacite.org/dois/", query="", page_size=100
    ):
        self.search_query = query
        self.search_url = search_url
        self.page_size = page_size

    def search_params(self, page=1, query=""):
        return {
            "query": query or self.search_query,
            "disable_facets": "true",
            "affiliation": "true",
            "include-other-registration-agencies": "true",
            "page[size]": self.page_size,
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
        super().__init__(search_url)

    def search_params(self, page=1, query=""):
        return {
            "ids": ",".join(self.doi_list),
            "disable_facets": "true",
            "affiliation": "true",
            "include-other-registration-agencies": "true",
            "page[size]": self.page_size,
            "page[number]": page,
        }

    def _verified_doi_list(self, raw_doi_list):
        temp_list = (extract_doi(doi) for doi in raw_doi_list)
        return [doi for doi in temp_list if doi is not None]
