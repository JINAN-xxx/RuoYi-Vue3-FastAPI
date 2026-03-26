from collections.abc import Sequence

from module_knowledge.entity.do.knowledge_document_do import KnowledgeDocument
from module_knowledge.service.knowledge_vector_service import KnowledgeVectorService
from module_knowledge.service.providers.base import BaseKnowledgeProvider, KnowledgeChunkResult


class MilvusKnowledgeProvider(BaseKnowledgeProvider):
    """
    基于 Milvus 的知识库 Provider
    """

    provider_name = 'milvus'

    def index_document(self, document: KnowledgeDocument) -> tuple[str, int]:
        return KnowledgeVectorService.index_document(document)

    def delete_document(self, document_id: int) -> None:
        KnowledgeVectorService.delete_document_vectors(document_id)

    def search(self, query: str, document_ids: Sequence[int], limit: int | None = None) -> list[KnowledgeChunkResult]:
        rows = KnowledgeVectorService.search_document_chunks(query, document_ids, limit)

        return [KnowledgeChunkResult(**row) for row in rows]
