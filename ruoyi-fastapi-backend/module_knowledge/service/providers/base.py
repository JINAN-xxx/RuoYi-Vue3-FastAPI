from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from module_knowledge.entity.do.knowledge_document_do import KnowledgeDocument


@dataclass
class KnowledgeChunkResult:
    """
    知识片段检索结果
    """

    document_id: int
    scope: str
    user_id: int
    dept_id: int
    content: str
    score: float | None = None


class BaseKnowledgeProvider(ABC):
    """
    知识库 Provider 抽象基类
    """

    provider_name = 'base'

    @abstractmethod
    def index_document(self, document: KnowledgeDocument) -> tuple[str, int]:
        """
        建立文档索引，返回预览文本与切片数量
        """

    @abstractmethod
    def delete_document(self, document_id: int) -> None:
        """
        删除文档索引
        """

    @abstractmethod
    def search(self, query: str, document_ids: Sequence[int], limit: int | None = None) -> list[KnowledgeChunkResult]:
        """
        检索知识片段
        """
