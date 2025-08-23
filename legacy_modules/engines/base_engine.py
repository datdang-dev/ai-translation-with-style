from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List

class BaseEngineProcessor(ABC):
    """
    Base interface cho các Engine Processor.
    Nhiệm vụ: chuẩn hóa bước tiền xử lý để tạo ra file text theo format chuẩn "---------<block_number>".
    """
    def __init__(self, logger=None):
        self.logger = logger

    @property
    @abstractmethod
    def needs_preprocess(self) -> bool:
        """Cho biết engine có cần preprocess để tạo file .txt chuẩn không."""
        raise NotImplementedError

    @abstractmethod
    def preprocess(self, engine_input_folder: str, text_to_translate_folder: str) -> List[str]:
        """
        Tiền xử lý input engine-đặc thù để sinh ra file .txt chuẩn.
        Trả về danh sách đường dẫn file .txt đã tạo trong text_to_translate_folder.
        """
        raise NotImplementedError

    @abstractmethod
    def postprocess(self, text_to_translate_folder: str, translate_output_folder: str) -> List[str]:
        """
        Postprocess / apply translations back to engine-specific format.
        - `text_to_translate_folder`: folder containing the original engine-format source files (that were preprocessed)
        - `translate_output_folder`: folder containing translated canonical-format files (parts / merged file)
        Should perform any merging/applying needed for the engine and return a list of output paths produced.
        """
        raise NotImplementedError
