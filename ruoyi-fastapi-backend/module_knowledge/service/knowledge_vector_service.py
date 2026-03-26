import os
import re
from collections.abc import Sequence

from config.env import KnowledgeConfig
from exceptions.exception import ServiceException
from module_knowledge.entity.do.knowledge_document_do import KnowledgeDocument

try:
    from docx import Document as WordDocument
except ImportError as exc:
    WordDocument = None
    DOCX_IMPORT_ERROR = exc

try:
    from openai import OpenAI
except ImportError as exc:
    OpenAI = None
    OPENAI_IMPORT_ERROR = exc

try:
    from pypdf import PdfReader
except ImportError as exc:
    PdfReader = None
    PDF_IMPORT_ERROR = exc

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

if WordDocument is not None:
    DOCX_IMPORT_ERROR = None
if OpenAI is not None:
    OPENAI_IMPORT_ERROR = None
if PdfReader is not None:
    PDF_IMPORT_ERROR = None


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
    def _ensure_openai_dependency(cls) -> None:
        if OPENAI_IMPORT_ERROR is not None:
            raise ServiceException(message=f'Embedding 依赖缺失：{OPENAI_IMPORT_ERROR}')

    @classmethod
    def _ensure_parser_dependency(cls, file_ext: str | None) -> None:
        if file_ext == '.docx' and DOCX_IMPORT_ERROR is not None:
            raise ServiceException(message=f'DOCX 解析依赖缺失：{DOCX_IMPORT_ERROR}')
        if file_ext == '.pdf' and PDF_IMPORT_ERROR is not None:
            raise ServiceException(message=f'PDF 解析依赖缺失：{PDF_IMPORT_ERROR}')

    @classmethod
    def _ensure_embedding_config(cls) -> None:
        if not KnowledgeConfig.knowledge_embedding_api_key:
            raise ServiceException(message='未配置 KNOWLEDGE_EMBEDDING_API_KEY，无法建立知识库向量索引')

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
    def _get_embedding_client(cls) -> OpenAI:
        cls._ensure_openai_dependency()
        cls._ensure_embedding_config()

        return OpenAI(
            api_key=KnowledgeConfig.knowledge_embedding_api_key,
            base_url=KnowledgeConfig.knowledge_embedding_base_url,
        )

    @classmethod
    def _normalize_text(cls, content: str) -> str:
        normalized = content.replace('\x00', ' ')
        normalized = re.sub(r'\r\n?', '\n', normalized)
        normalized = re.sub(r'\n{3,}', '\n\n', normalized)
        normalized = re.sub(r'[ \t]+', ' ', normalized)

        return normalized.strip()

    @classmethod
    def _load_document_text(cls, file_path: str, file_ext: str | None) -> str:
        if not os.path.exists(file_path):
            raise ServiceException(message='知识库源文件不存在')
        cls._ensure_parser_dependency(file_ext)

        if file_ext in {'.txt', '.md'}:
            with open(file_path, encoding='utf-8', errors='ignore') as stream:
                return stream.read()
        if file_ext == '.pdf':
            reader = PdfReader(file_path)
            return '\n'.join((page.extract_text() or '') for page in reader.pages)
        if file_ext == '.docx':
            document = WordDocument(file_path)
            return '\n'.join(paragraph.text for paragraph in document.paragraphs)

        raise ServiceException(message=f'当前版本暂不支持 {file_ext} 文件的真实解析，请使用 pdf/docx/txt/md')

    @classmethod
    def _split_text(cls, content: str) -> list[str]:
        chunk_size = KnowledgeConfig.knowledge_chunk_size
        chunk_overlap = KnowledgeConfig.knowledge_chunk_overlap
        if chunk_overlap >= chunk_size:
            chunk_overlap = max(0, chunk_size // 4)

        paragraphs = [item.strip() for item in re.split(r'\n{2,}', content) if item.strip()]
        if not paragraphs:
            paragraphs = [content]

        chunks: list[str] = []
        current = ''
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if len(paragraph) <= chunk_size and len(current) + len(paragraph) + 1 <= chunk_size:
                current = f'{current}\n{paragraph}'.strip()
                continue

            if current:
                chunks.append(current[: cls.MAX_CONTENT_LENGTH])
                overlap = current[-chunk_overlap:] if chunk_overlap else ''
                current = f'{overlap}{paragraph}'.strip()
            else:
                current = paragraph

            while len(current) > chunk_size:
                chunk = current[:chunk_size].strip()
                if chunk:
                    chunks.append(chunk[: cls.MAX_CONTENT_LENGTH])
                start = max(0, chunk_size - chunk_overlap)
                current = current[start:].strip()

        if current:
            chunks.append(current[: cls.MAX_CONTENT_LENGTH])

        return [item for item in chunks if item.strip()]

    @classmethod
    def _build_preview(cls, content: str) -> str:
        return cls._normalize_text(content)[:300]

    @classmethod
    def _embed_texts(cls, texts: Sequence[str]) -> list[list[float]]:
        client = cls._get_embedding_client()
        batch_size = max(1, KnowledgeConfig.knowledge_embedding_batch_size)
        embeddings: list[list[float]] = []
        model = KnowledgeConfig.knowledge_embedding_model

        for index in range(0, len(texts), batch_size):
            batch = [item for item in texts[index : index + batch_size] if item.strip()]
            if not batch:
                continue
            response = client.embeddings.create(input=batch, model=model)
            embeddings.extend(item.embedding for item in response.data)

        return embeddings

    @classmethod
    def _delete_document_vectors(cls, document_id: int) -> None:
        collection = cls._get_collection()
        collection.delete(expr=f'document_id == {document_id}')
        collection.flush()

    @classmethod
    def index_document(cls, document: KnowledgeDocument) -> tuple[str, int]:
        cls._ensure_dependencies()
        cls._ensure_openai_dependency()
        content = cls._load_document_text(document.document_path, document.file_ext)
        normalized = cls._normalize_text(content)
        if not normalized:
            raise ServiceException(message='文档内容为空，无法建立索引')

        chunks = cls._split_text(normalized)
        if not chunks:
            raise ServiceException(message='文档切片结果为空，无法建立索引')

        embeddings = cls._embed_texts(chunks)
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

        return cls._build_preview(normalized), len(chunks)

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

        query_embedding = cls._embed_texts([query.strip()])
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
