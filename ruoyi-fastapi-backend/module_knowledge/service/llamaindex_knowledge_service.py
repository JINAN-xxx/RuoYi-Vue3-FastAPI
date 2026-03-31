from collections.abc import Sequence

from config.env import KnowledgeConfig
from exceptions.exception import ServiceException
from module_knowledge.entity.do.knowledge_document_do import KnowledgeDocument
from module_knowledge.service.knowledge_processing_service import KnowledgeProcessingService
from module_knowledge.service.providers.base import KnowledgeChunkResult

try:
    from llama_index.core import VectorStoreIndex
    from llama_index.core.embeddings import BaseEmbedding
    from llama_index.core.schema import MetadataMode, NodeRelationship, RelatedNodeInfo, TextNode
    from llama_index.core.vector_stores.types import VectorStoreQuery
    from llama_index.vector_stores.milvus import MilvusVectorStore

    LLAMAINDEX_IMPORT_ERROR = None
except ImportError as exc:
    VectorStoreIndex = None
    BaseEmbedding = object
    MetadataMode = None
    NodeRelationship = None
    RelatedNodeInfo = None
    TextNode = None
    VectorStoreQuery = None
    MilvusVectorStore = None
    LLAMAINDEX_IMPORT_ERROR = exc


class OpenAICompatibleLlamaIndexEmbedding(BaseEmbedding):
    """
    复用现有 OpenAI 兼容 Embedding 配置的 LlamaIndex Embedding 适配器
    """

    def _get_query_embedding(self, query: str) -> list[float]:
        embeddings = KnowledgeProcessingService.embed_texts([query])
        return embeddings[0] if embeddings else []

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._get_query_embedding(query)

    def _get_text_embedding(self, text: str) -> list[float]:
        embeddings = KnowledgeProcessingService.embed_texts([text])
        return embeddings[0] if embeddings else []

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        return KnowledgeProcessingService.embed_texts(texts)


class LlamaIndexKnowledgeService:
    """
    基于 LlamaIndex + Milvus 的知识库服务
    """

    @classmethod
    def _ensure_dependencies(cls) -> None:
        if LLAMAINDEX_IMPORT_ERROR is not None:
            raise ServiceException(message=f'LlamaIndex 依赖缺失：{LLAMAINDEX_IMPORT_ERROR}')
        KnowledgeProcessingService.ensure_openai_dependency()
        KnowledgeProcessingService.ensure_embedding_config()

    @classmethod
    def _get_embedding_model(cls) -> OpenAICompatibleLlamaIndexEmbedding:
        return OpenAICompatibleLlamaIndexEmbedding(
            model_name=KnowledgeConfig.knowledge_embedding_model,
            embed_batch_size=max(1, int(KnowledgeConfig.knowledge_embedding_batch_size)),
        )

    @classmethod
    def _get_vector_store(cls) -> MilvusVectorStore:
        cls._ensure_dependencies()

        return MilvusVectorStore(
            uri=KnowledgeConfig.knowledge_milvus_uri,
            token=KnowledgeConfig.knowledge_milvus_token,
            collection_name=KnowledgeConfig.knowledge_llamaindex_milvus_collection,
            dim=KnowledgeConfig.knowledge_embedding_dimension,
            similarity_metric='COSINE',
            consistency_level='Strong',
            use_async_client=False,
        )

    @classmethod
    def _build_nodes(cls, document: KnowledgeDocument, chunks: Sequence[str]) -> list[TextNode]:
        ref_doc_id = str(document.document_id)
        related_node = RelatedNodeInfo(node_id=ref_doc_id)
        dept_id = int(document.dept_id or 0)

        return [
            TextNode(
                id_=f'{document.document_id}_{index}',
                text=chunk,
                metadata={
                    'document_id': int(document.document_id),
                    'scope': document.scope,
                    'user_id': int(document.user_id),
                    'dept_id': dept_id,
                },
                relationships={NodeRelationship.SOURCE: related_node},
            )
            for index, chunk in enumerate(chunks)
        ]

    @classmethod
    def index_document(
        cls, document: KnowledgeDocument, chunk_size: int | None = None, chunk_overlap: int | None = None
    ) -> tuple[str, int]:
        cls._ensure_dependencies()
        content = KnowledgeProcessingService.load_document_text(document.document_path, document.file_ext)
        normalized = KnowledgeProcessingService.normalize_text(content)
        if not normalized:
            raise ServiceException(message='文档内容为空，无法建立索引')

        chunks = KnowledgeProcessingService.split_text(normalized, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        if not chunks:
            raise ServiceException(message='文档切片结果为空，无法建立索引')

        vector_store = cls._get_vector_store()
        ref_doc_id = str(document.document_id)
        vector_store.delete(ref_doc_id)
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            embed_model=cls._get_embedding_model(),
        )
        index.insert_nodes(cls._build_nodes(document, chunks))

        return KnowledgeProcessingService.build_preview(normalized), len(chunks)

    @classmethod
    def delete_document(cls, document_id: int) -> None:
        cls._get_vector_store().delete(str(document_id))

    @classmethod
    def search(cls, query: str, document_ids: Sequence[int], limit: int | None = None) -> list[KnowledgeChunkResult]:
        if not query.strip() or not document_ids:
            return []

        vector_store = cls._get_vector_store()
        query_embedding = cls._get_embedding_model().get_query_embedding(query.strip())
        if not query_embedding:
            return []

        result = vector_store.query(
            VectorStoreQuery(
                query_embedding=query_embedding,
                similarity_top_k=limit or KnowledgeConfig.knowledge_search_top_k,
                doc_ids=[str(int(item)) for item in set(document_ids)],
            )
        )
        nodes = list(result.nodes or [])
        similarities = list(result.similarities or [])
        if len(similarities) < len(nodes):
            similarities.extend([None] * (len(nodes) - len(similarities)))

        results: list[KnowledgeChunkResult] = []
        for node, score in zip(nodes, similarities):
            metadata = getattr(node, 'metadata', {}) or {}
            document_id = node.ref_doc_id or metadata.get('document_id') or 0
            results.append(
                KnowledgeChunkResult(
                    document_id=int(document_id),
                    scope=str(metadata.get('scope') or ''),
                    user_id=int(metadata.get('user_id') or 0),
                    dept_id=int(metadata.get('dept_id') or 0),
                    content=node.get_content(metadata_mode=MetadataMode.NONE),
                    score=float(score) if score is not None else None,
                )
            )

        return results
