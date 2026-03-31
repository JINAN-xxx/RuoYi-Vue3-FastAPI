from collections.abc import Sequence

from config.env import KnowledgeConfig
from exceptions.exception import ServiceException
from module_knowledge.entity.do.knowledge_document_do import KnowledgeDocument
from module_knowledge.service.providers.base import BaseKnowledgeProvider, KnowledgeChunkResult
from module_knowledge.service.providers.llamaindex_provider import LlamaIndexKnowledgeProvider
from module_knowledge.service.providers.milvus_provider import MilvusKnowledgeProvider


class KnowledgeProviderManager:
    """
    知识库 Provider 管理器
    """

    _providers: dict[str, BaseKnowledgeProvider] = {
        LlamaIndexKnowledgeProvider.provider_name: LlamaIndexKnowledgeProvider(),
        MilvusKnowledgeProvider.provider_name: MilvusKnowledgeProvider(),
    }
    _default_provider_name = KnowledgeConfig.knowledge_provider

    @classmethod
    def get_provider(cls, provider_name: str | None = None) -> BaseKnowledgeProvider:
        name = provider_name or cls._default_provider_name
        provider = cls._providers.get(name)
        if provider is None:
            raise ServiceException(message=f'未找到知识库 Provider：{name}')

        return provider

    @classmethod
    def get_default_provider_name(cls) -> str:
        return cls._default_provider_name

    @classmethod
    def index_document(
        cls,
        document: KnowledgeDocument,
        provider_name: str | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> tuple[str, int]:
        return cls.get_provider(provider_name).index_document(
            document, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    @classmethod
    def delete_document(cls, document_id: int, provider_name: str | None = None) -> None:
        cls.get_provider(provider_name).delete_document(document_id)

    @classmethod
    def search(
        cls,
        query: str,
        document_ids: Sequence[int],
        limit: int | None = None,
        provider_name: str | None = None,
    ) -> list[KnowledgeChunkResult]:
        return cls.get_provider(provider_name).search(query, document_ids, limit)
