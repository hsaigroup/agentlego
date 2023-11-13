# Copyright (c) OpenMMLab. All rights reserved.
import os
from typing import Callable, List, Tuple, Union

import requests

from agentlego.parsers import DefaultParser
from agentlego.schema import ToolMeta
from ..base import BaseTool


class GoogleSearch(BaseTool):
    """A tool to search on Google.

    Code is modified from lang-chain GoogleSerperAPIWrapper
    (https://github.com/langchain-ai/langchain/blob/ba5f
    baba704a2d729a4b8f568ed70d7c53e799bb/libs/langchain/
    langchain/utilities/google_serper.py)

    To get an Serper.dev API key. you can create it at https://serper.dev

    Args:
        toolmeta (dict | ToolMeta): The meta info of the tool. Defaults to
            the :attr:`DEFAULT_TOOLMETA`.
        parser (Callable): The parser constructor, Defaults to
            :class:`DefaultParser`.
        api_key (str): API key to use for serper google search API.
            Defaults to 'env', which means to use the `SERPER_API_KEY` in
            the environ variable.
        timeout (int): Upper bound of waiting time for a serper request.
            Defaults to 5.
        search_type (str): Serper API support ['search', 'images', 'news',
            'places'] types of search, currently we only support 'search'.
            Defaults to `search`.
        max_out_len (int): The maximum length of the total search result.
            Defaults to 1500.
        with_url (bool): Whether to include the url of search results.
            Defaults to False.
        k (int): select first k results in the search results as response.
            Defaults to 10.
    """

    result_key_for_type = {
        'news': 'news',
        'places': 'places',
        'images': 'images',
        'search': 'organic',
    }

    DEFAULT_TOOLMETA = ToolMeta(
        name='Google Search',
        description=('The tool can search the input query text from Google '
                     'and return the related results'),
        inputs=['text'],
        outputs=['text'],
    )

    def __init__(self,
                 toolmeta: Union[dict, ToolMeta] = DEFAULT_TOOLMETA,
                 parser: Callable = DefaultParser,
                 api_key: str = 'env',
                 timeout: int = 5,
                 search_type: str = 'search',
                 max_out_len: int = 1500,
                 with_url: bool = False,
                 k: int = 10) -> None:
        super().__init__(toolmeta=toolmeta, parser=parser)

        if api_key == 'env':
            api_key = os.environ.get('SERPER_API_KEY', None)
        if not api_key:
            raise ValueError(
                'Please set Serper API key either in the environment '
                ' as SERPER_API_KEY or pass it as `api_key` parameter.')

        self.api_key = api_key
        self.timeout = timeout
        self.search_type = search_type
        self.k = k
        self.max_out_len = max_out_len
        self.with_url = with_url

    def apply(self, query: str) -> str:
        status_code, results = self._search(
            query, search_type=self.search_type, k=self.k)
        # convert search results to ToolReturn format
        if status_code == 200:
            results = self._parse_results(results)
            return str(results)
        else:
            raise ConnectionError(f'Error {status_code}: {results}')

    def _parse_results(self, results: dict) -> Union[str, List[str]]:
        """Parse the search results from Serper API.

        Args:
            results (dict): The search content from Serper API
                in json format.

        Returns:
            List[str]: The parsed search results.
        """

        snippets = []

        answer_box = results.get('answerBox', {})
        if answer_box:
            content = 'Answer box: '
            if answer_box.get('answer'):
                content += answer_box['answer']
            elif answer_box.get('snippet'):
                content += answer_box['snippet']
            elif answer_box.get('snippetHighlighted'):
                content += answer_box['snippetHighlighted']
            snippets.append(content)

        kg = results.get('knowledgeGraph', {})
        if kg:
            content = 'Knowledge graph: '
            if kg.get('title'):
                content = kg['title'] + ' knowledge graph: '
            if kg.get('type'):
                content += kg['type'] + '. '
            if kg.get('description'):
                content += kg['description']
            if kg.get('attributes'):
                attributes = ', '.join(f'{k}: {v}'
                                       for k, v in kg['attributes'].items())
                content += f'({attributes})'
            snippets.append(content)

        for item in results[self.result_key_for_type[
                self.search_type]][:self.k]:
            content = ''
            if item.get('title'):
                content += item['title'] + ': '
            if item.get('link') and self.with_url:
                content += f"({item['link']})"
            if item.get('snippet'):
                content += item['snippet']
            if item.get('attributes'):
                attributes = ', '.join(f'{k}: {v}'
                                       for k, v in item['attributes'].items())
                content += f'({attributes})'
            snippets.append(content)

        if len(snippets) == 0:
            return 'No good Google Search Result was found'

        result = ''
        for idx, item in enumerate(snippets):
            item = item.strip().replace('\n', ' ')
            result += f'{idx+1} - {item}\n\n'

        if len(result) > self.max_out_len:
            result = result[:self.max_out_len] + '...'
        return result

    def _search(self,
                query: str,
                search_type: str = 'search',
                **kwargs) -> Tuple[int, Union[dict, str]]:
        """HTTP requests to Serper API.

        Args:
            query (str): The search query.
            search_type (str): search type supported by Serper API,
                default to 'search'.

        Returns:
            tuple: the return value is a tuple contains:

            - status_code (int): HTTP status code from Serper API.
            - response (dict): response context with json format.
        """
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json',
        }
        params = {k: v for k, v in kwargs.items() if v is not None}
        params['q'] = query

        try:
            response = requests.post(
                f'https://google.serper.dev/{search_type}',
                headers=headers,
                params=params,
                timeout=self.timeout)
        except Exception as e:
            return -1, str(e)
        return response.status_code, response.json()
