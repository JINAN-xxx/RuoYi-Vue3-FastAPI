from collections.abc import Sequence

from config.env import KnowledgeConfig
from exceptions.exception import ServiceException
from module_knowledge.entity.do.knowledge_document_do import KnowledgeDocument
from module_knowledge.service.knowledge_processing_service import KnowledgeProcessingService

try:
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
    VECTOR_IMPORT_ERROR = None
except ImportError as exc:
    Collection = None
    CollectionSchema = None
    DataType = None
    FieldSchema = None
    connections = None
    utility = None
    VECTOR_IMPORT_ERROR = exc


class KnowledgeVectorService:
    """
    知识库向量索引服务
    """

    CONNECTION_ALIAS = 'knowledge_milvus'
    MAX_CONTENT_LENGTH = 4096

    @classmethod
    def _ensure_dependencies(cls) -> None:
        if VECTOR_IMPORT_ERROR is not None:
            raise ServiceException(message=f'知识库索引依赖缺失：{VECTOR_IMPORT_ERROR}')

    @classmethod
    def _get_collection(cls) -> Collection:
        cls._ensure_dependencies()
        if not connections.has_connection(cls.CONNECTION_ALIAS):
            connect_kwargs = {'alias': cls.CONNECTION_ALIAS, 'uri': KnowledgeConfig.knowledge_milvus_uri}
            if KnowledgeConfig.knowledge_milvus_token:
                connect_kwargs['token'] = KnowledgeConfig.knowledge_milvus_token
            connections.connect(**connect_kwargs)

        collection_name = KnowledgeConfig.knowledge_milvus_collection
        if not utility.has_collection(collection_name, using=cls.CONNECTION_ALIAS):
            fields = [
                FieldSchema(name='chunk_id', dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=64),
                FieldSchema(name='document_id', dtype=DataType.INT64),
                FieldSchema(name='user_id', dtype=DataType.INT64),
                FieldSchema(name='dept_id', dtype=DataType.INT64),
                FieldSchema(name='scope', dtype=DataType.VARCHAR, max_length=20),
                FieldSchema(name='content', dtype=DataType.VARCHAR, max_length=cls.MAX_CONTENT_LENGTH),
                FieldSchema(
                    name='embedding',
                    dtype=DataType.FLOAT_VECTOR,
                    dim=KnowledgeConfig.knowledge_embedding_dimension,
                ),
            ]
            schema = CollectionSchema(fields=fields, description='RuoYi FastAPI knowledge chunks')
            collection = Collection(
                name=collection_name,
                schema=schema,
                using=cls.CONNECTION_ALIAS,
                consistency_level='Strong',
            )
            collection.create_index(
                field_name='embedding',
                index_params={'metric_type': 'COSINE', 'index_type': 'AUTOINDEX', 'params': {}},
            )
        else:
            collection = Collection(collection_name, using=cls.CONNECTION_ALIAS)

        collection.load()

        return collection

    @classmethod
    def _delete_document_vectors(cls, document_id: int) -> None:
        collection = cls._get_collection()
        collection.delete(expr=f'document_id == {document_id}')
        collection.flush()

    @classmethod
    def index_document(
        cls, document: KnowledgeDocument, chunk_size: int | None = None, chunk_overlap: int | None = None
    ) -> tuple[str, int]:
        cls._ensure_dependencies()
        KnowledgeProcessingService.ensure_openai_dependency()
        content = KnowledgeProcessingService.load_document_text(document.document_path, document.file_ext)
        normalized = KnowledgeProcessingService.normalize_text(content)
        if not normalized:
            raise ServiceException(message='文档内容为空，无法建立索引')

        chunks = KnowledgeProcessingService.split_text(normalized, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        if not chunks:
            raise ServiceException(message='文档切片结果为空，无法建立索引')

        embeddings = KnowledgeProcessingService.embed_texts(chunks)
        if len(embeddings) != len(chunks):
            raise ServiceException(message='向量化结果数量异常，知识库索引失败')

        collection = cls._get_collection()
        cls._delete_document_vectors(document.document_id)
        dept_id = int(document.dept_id or 0)
        data = [
            [f'{document.document_id}_{index}' for index in range(len(chunks))],
            [int(document.document_id)] * len(chunks),
            [int(document.user_id)] * len(chunks),
            [dept_id] * len(chunks),
            [document.scope] * len(chunks),
            chunks,
            embeddings,
        ]
        collection.insert(data)
        collection.flush()

        return KnowledgeProcessingService.build_preview(normalized), len(chunks)

    @classmethod
    def delete_document_vectors(cls, document_id: int) -> None:
        try:
            cls._delete_document_vectors(document_id)
        except ServiceException:
            raise
        except Exception as exc:
            raise ServiceException(message=f'删除知识库向量索引失败：{exc}') from exc

    @classmethod
    def search_document_chunks(cls, query: str, document_ids: Sequence[int], limit: int | None = None) -> list[dict]:
        if not query.strip() or not document_ids:
            return []

        query_embedding = KnowledgeProcessingService.embed_texts([query.strip()])
        if not query_embedding:
            return []

        collection = cls._get_collection()
        doc_id_expr = ','.join(str(int(item)) for item in set(document_ids))
        expr = f'document_id in [{doc_id_expr}]'
        result = collection.search(
            data=query_embedding,
            anns_field='embedding',
            param={'metric_type': 'COSINE', 'params': {}},
            limit=limit or KnowledgeConfig.knowledge_search_top_k,
            output_fields=['document_id', 'scope', 'user_id', 'dept_id', 'content'],
            expr=expr,
        )
        hits = result[0] if result else []

        return [
            {
                'document_id': hit.entity.get('document_id'),
                'scope': hit.entity.get('scope'),
                'user_id': hit.entity.get('user_id'),
                'dept_id': hit.entity.get('dept_id'),
                'content': hit.entity.get('content'),
                'score': hit.score,
            }
            for hit in hits
        ]
