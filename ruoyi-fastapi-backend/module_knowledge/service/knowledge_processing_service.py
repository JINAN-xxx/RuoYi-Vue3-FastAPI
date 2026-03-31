import os
import re
from collections.abc import Sequence

from config.env import KnowledgeConfig
from exceptions.exception import ServiceException

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

if WordDocument is not None:
    DOCX_IMPORT_ERROR = None
if OpenAI is not None:
    OPENAI_IMPORT_ERROR = None
if PdfReader is not None:
    PDF_IMPORT_ERROR = None


class KnowledgeProcessingService:
    """
    知识库共享处理能力：解析、切片、Embedding
    """

    MAX_CONTENT_LENGTH = 4096

    @classmethod
    def ensure_openai_dependency(cls) -> None:
        if OPENAI_IMPORT_ERROR is not None:
            raise ServiceException(message=f'Embedding 依赖缺失：{OPENAI_IMPORT_ERROR}')

    @classmethod
    def ensure_parser_dependency(cls, file_ext: str | None) -> None:
        if file_ext == '.docx' and DOCX_IMPORT_ERROR is not None:
            raise ServiceException(message=f'DOCX 解析依赖缺失：{DOCX_IMPORT_ERROR}')
        if file_ext == '.pdf' and PDF_IMPORT_ERROR is not None:
            raise ServiceException(message=f'PDF 解析依赖缺失：{PDF_IMPORT_ERROR}')

    @classmethod
    def ensure_embedding_config(cls) -> None:
        if not KnowledgeConfig.knowledge_embedding_api_key:
            raise ServiceException(message='未配置 KNOWLEDGE_EMBEDDING_API_KEY，无法建立知识库向量索引')

    @classmethod
    def get_embedding_client(cls) -> OpenAI:
        cls.ensure_openai_dependency()
        cls.ensure_embedding_config()

        return OpenAI(
            api_key=KnowledgeConfig.knowledge_embedding_api_key,
            base_url=KnowledgeConfig.knowledge_embedding_base_url,
        )

    @classmethod
    def normalize_text(cls, content: str) -> str:
        normalized = content.replace('\x00', ' ')
        normalized = re.sub(r'\r\n?', '\n', normalized)
        normalized = re.sub(r'\n{3,}', '\n\n', normalized)
        normalized = re.sub(r'[ \t]+', ' ', normalized)

        return normalized.strip()

    @classmethod
    def load_document_text(cls, file_path: str, file_ext: str | None) -> str:
        if not os.path.exists(file_path):
            raise ServiceException(message='知识库源文件不存在')
        cls.ensure_parser_dependency(file_ext)

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
    def split_text(cls, content: str, chunk_size: int | None = None, chunk_overlap: int | None = None) -> list[str]:
        chunk_size = int(chunk_size or KnowledgeConfig.knowledge_chunk_size)
        chunk_overlap = int(chunk_overlap if chunk_overlap is not None else KnowledgeConfig.knowledge_chunk_overlap)
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
    def build_preview(cls, content: str) -> str:
        return cls.normalize_text(content)[:300]

    @classmethod
    def embed_texts(cls, texts: Sequence[str]) -> list[list[float]]:
        client = cls.get_embedding_client()
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
