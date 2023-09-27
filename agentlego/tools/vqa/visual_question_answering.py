# Copyright (c) OpenMMLab. All rights reserved.
from typing import Callable, Union

from agentlego.parsers import DefaultParser
from agentlego.schema import ToolMeta
from agentlego.types import ImageIO
from agentlego.utils import load_or_build_object, require
from ..base import BaseTool


class VisualQuestionAnswering(BaseTool):
    """A tool to answer the question about an image.

    Args:
        toolmeta (dict | ToolMeta): The meta info of the tool. Defaults to
            the :attr:`DEFAULT_TOOLMETA`.
        parser (Callable): The parser constructor, Defaults to
            :class:`DefaultParser`.
        remote (bool): Whether to use the remote model. Defaults to False.
        device (str): The device to load the model. Defaults to 'cuda'.
    """

    DEFAULT_TOOLMETA = ToolMeta(
        name='Visual Question Answering',
        description='This is a useful tool '
        'when you want to know some information about the image.'
        'and this tool will return the answer to the question based on '
        'the image.',
        inputs=['image', 'text'],
        outputs=['text'])

    def __init__(self,
                 toolmeta: Union[ToolMeta, dict] = DEFAULT_TOOLMETA,
                 parser: Callable = DefaultParser,
                 model: str = 'ofa-base_3rdparty-zeroshot_vqa',
                 device: str = 'cuda'):
        super().__init__(toolmeta, parser)
        self.device = device
        self.model = model

    @require('mmpretrain')
    def setup(self):
        from mmpretrain.apis import VisualQuestionAnsweringInferencer
        self._inferencer = load_or_build_object(
            VisualQuestionAnsweringInferencer,
            model=self.model,
            device=self.device)

    def apply(self, image: ImageIO, text: str) -> str:
        return self._inferencer(image.to_path(), text)[0]['pred_answer']