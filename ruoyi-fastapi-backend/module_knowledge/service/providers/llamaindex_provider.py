from collections.abc import Sequence

from module_knowledge.entity.do.knowledge_document_do import KnowledgeDocument
from module_knowledge.service.llamaindex_knowledge_service import LlamaIndexKnowledgeService
from module_knowledge.service.providers.base import BaseKnowledgeProvider, KnowledgeChunkResult


class LlamaIndexKnowledgeProvider(BaseKnowledgeProvider):
    """
    基于 LlamaIndex 的知识库 Provider
    """

    provider_name = 'llamaindex'

    def index_document(
        self, document: KnowledgeDocument, chunk_size: int | None = None, chunk_overlap: int | None = None
    ) -> tuple[str, int]:
        return LlamaIndexKnowledgeService.index_document(
            document, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def delete_document(self, document_id: int) -> None:
        LlamaIndexKnowledgeService.delete_document(document_id)

    def search(self, query: str, document_ids: Sequence[int], limit: int | None = None) -> list[KnowledgeChunkResult]:
        return LlamaIndexKnowledgeService.search(query, document_ids, limit)
