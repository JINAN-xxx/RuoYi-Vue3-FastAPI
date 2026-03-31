import asyncio
import math
import os
import json
from functools import partial
from datetime import datetime

import aiofiles
from fastapi import Request, UploadFile
from sqlalchemy import ColumnElement, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import CrudResponseModel, PageModel
from config.database import AsyncSessionLocal
from config.env import KnowledgeConfig, UploadConfig
from exceptions.exception import ServiceException
from module_admin.dao.dept_dao import DeptDao
from module_admin.entity.do.dept_do import SysDept
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_knowledge.dao.knowledge_document_dao import KnowledgeDocumentDao
from module_knowledge.entity.do.knowledge_document_do import KnowledgeDocument
from module_knowledge.entity.vo.knowledge_document_vo import (
    KnowledgeDocumentModel,
    KnowledgeDocumentPageQueryModel,
    KnowledgeDocumentReindexModel,
    KnowledgeDocumentUploadModel,
)
from module_knowledge.service.providers.manager import KnowledgeProviderManager
from module_knowledge.service.knowledge_task_service import KnowledgeTaskQueueService
from utils.common_util import CamelCaseUtil
from utils.log_util import logger
from utils.upload_util import UploadUtil


class KnowledgeDocumentService:
    """
    知识库文档服务层
    """

    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md'}
    MAX_FILE_SIZE = 20 * 1024 * 1024
    REINDEX_CONFIG_REMARK_KEY = 'reindex_config'
    PROVIDER_REMARK_KEY = 'provider_name'
    LEGACY_REMARK_KEY = 'legacy_remark'
    LEGACY_PROVIDER_NAME = 'milvus'

    @classmethod
    def _check_scope_permission(cls, scope: str, current_user: CurrentUserModel) -> None:
        if scope not in {'enterprise', 'department', 'personal'}:
            raise ServiceException(message='知识库范围参数无效')
        if scope == 'enterprise' and not current_user.user.admin:
            raise ServiceException(message='只有管理员可以上传企业知识')
        if scope == 'department' and not current_user.user.dept_id:
            raise ServiceException(message='当前用户未绑定部门，无法上传部门知识')

    @classmethod
    def _get_storage_paths(cls, scope: str, user_id: int) -> tuple[str, str]:
        relative_dir = os.path.join('knowledge', scope)
        if scope == 'personal':
            relative_dir = os.path.join(relative_dir, f'user_{user_id}')
        dir_path = os.path.join(UploadConfig.UPLOAD_PATH, relative_dir)
        os.makedirs(dir_path, exist_ok=True)

        return relative_dir, dir_path

    @classmethod
    def _build_filename(cls, file: UploadFile) -> tuple[str, str]:
        if '.' not in file.filename:
            raise ServiceException(message='文件名称不合法')
        file_ext = f".{file.filename.rsplit('.', 1)[-1].lower()}"
        if file_ext not in cls.ALLOWED_EXTENSIONS:
            raise ServiceException(message=f'暂不支持的文件类型：{file_ext}')
        filename = (
            f'{file.filename.rsplit(".", 1)[0]}_{datetime.now().strftime("%Y%m%d%H%M%S")}'
            f'{UploadConfig.UPLOAD_MACHINE}{UploadUtil.generate_random_number()}{file_ext}'
        )

        return filename, file_ext

    @classmethod
    def _load_remark_data(cls, remark: str | None) -> dict:
        if not remark:
            return {}
        try:
            remark_data = json.loads(remark)
            return remark_data if isinstance(remark_data, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            return {cls.LEGACY_REMARK_KEY: str(remark)}

    @classmethod
    def _dump_remark_data(cls, remark_data: dict | None) -> str | None:
        cleaned = {k: v for k, v in (remark_data or {}).items() if v not in (None, '', {}, [])}
        if not cleaned:
            return None
        if set(cleaned.keys()) == {cls.LEGACY_REMARK_KEY}:
            return str(cleaned[cls.LEGACY_REMARK_KEY])
        return json.dumps(cleaned, ensure_ascii=False)

    @classmethod
    def _resolve_document_chunk_config(
        cls, document: KnowledgeDocument, requested_config: KnowledgeDocumentReindexModel | None = None
    ) -> tuple[int, int, dict]:
        remark_data = cls._load_remark_data(document.remark)
        stored_config = remark_data.get(cls.REINDEX_CONFIG_REMARK_KEY, {})
        if not isinstance(stored_config, dict):
            stored_config = {}

        chunk_size = requested_config.chunk_size if requested_config and requested_config.chunk_size is not None else None
        if chunk_size is None:
            chunk_size = stored_config.get('chunk_size')
        if chunk_size is None:
            chunk_size = KnowledgeConfig.knowledge_chunk_size

        chunk_overlap = (
            requested_config.chunk_overlap if requested_config and requested_config.chunk_overlap is not None else None
        )
        if chunk_overlap is None:
            chunk_overlap = stored_config.get('chunk_overlap')
        if chunk_overlap is None:
            chunk_overlap = KnowledgeConfig.knowledge_chunk_overlap

        chunk_size = int(chunk_size)
        chunk_overlap = int(chunk_overlap)
        if chunk_overlap >= chunk_size:
            raise ServiceException(message='切片重叠长度必须小于切片长度')

        remark_data[cls.REINDEX_CONFIG_REMARK_KEY] = {
            'chunk_size': chunk_size,
            'chunk_overlap': chunk_overlap,
        }
        return chunk_size, chunk_overlap, remark_data

    @classmethod
    def _resolve_document_provider_name(
        cls, document: KnowledgeDocument, use_default_for_untracked: bool = False
    ) -> str:
        provider_name = getattr(document, 'provider_name', None)
        if isinstance(provider_name, str) and provider_name.strip():
            return provider_name.strip()
        remark_data = cls._load_remark_data(document.remark)
        provider_name = remark_data.get(cls.PROVIDER_REMARK_KEY)
        if isinstance(provider_name, str) and provider_name.strip():
            return provider_name.strip()
        if use_default_for_untracked:
            return KnowledgeProviderManager.get_default_provider_name()
        return cls.LEGACY_PROVIDER_NAME

    @classmethod
    def _build_delete_provider_names(
        cls, document: KnowledgeDocument, preferred_provider_name: str | None = None
    ) -> list[str]:
        provider_names = [
            preferred_provider_name,
            cls._resolve_document_provider_name(document, use_default_for_untracked=True),
            KnowledgeProviderManager.get_default_provider_name(),
            cls.LEGACY_PROVIDER_NAME,
        ]

        return [name for index, name in enumerate(provider_names) if name and name not in provider_names[:index]]

    @classmethod
    def _enrich_document_data(cls, document_data: dict) -> dict:
        document_data = dict(document_data)
        remark_data = cls._load_remark_data(document_data.get('remark'))
        reindex_config = remark_data.get(cls.REINDEX_CONFIG_REMARK_KEY, {})
        if not isinstance(reindex_config, dict):
            reindex_config = {}
        provider_name = document_data.get('provider_name')
        if not provider_name:
            provider_name = remark_data.get(cls.PROVIDER_REMARK_KEY) or cls.LEGACY_PROVIDER_NAME
        document_data['provider_name'] = provider_name
        document_data['chunkSize'] = int(reindex_config.get('chunk_size') or KnowledgeConfig.knowledge_chunk_size)
        chunk_overlap = (
            reindex_config.get('chunk_overlap')
            if reindex_config.get('chunk_overlap') is not None
            else KnowledgeConfig.knowledge_chunk_overlap
        )
        document_data['chunkOverlap'] = int(chunk_overlap)
        return document_data

    @classmethod
    async def get_document_list_services(
        cls,
        query_db: AsyncSession,
        query_object: KnowledgeDocumentPageQueryModel,
        current_user: CurrentUserModel,
        is_page: bool = False,
    ) -> PageModel | list[dict]:
        visible_sql = await cls._build_visibility_sql(query_db, current_user)
        result = await KnowledgeDocumentDao.get_document_list(query_db, query_object, visible_sql, is_page)
        if is_page:
            result.rows = [cls._enrich_document_data(item) for item in result.rows]
            return result
        return [cls._enrich_document_data(item) for item in result]

    @classmethod
    async def document_detail_services(
        cls, query_db: AsyncSession, document_id: int, current_user: CurrentUserModel
    ) -> KnowledgeDocumentModel:
        document = await KnowledgeDocumentDao.get_document_detail_by_id(query_db, document_id)
        if document is None:
            raise ServiceException(message='知识库文档不存在')
        if not await cls._can_access_document(query_db, document, current_user):
            raise ServiceException(message='没有权限查看该知识库文档')

        return KnowledgeDocumentModel(**cls._enrich_document_data(CamelCaseUtil.transform_result(document)))

    @classmethod
    async def upload_document_services(
        cls,
        request: Request,
        query_db: AsyncSession,
        current_user: CurrentUserModel,
        upload_data: KnowledgeDocumentUploadModel,
        file: UploadFile,
    ) -> CrudResponseModel:
        cls._check_scope_permission(upload_data.scope, current_user)
        filename, file_ext = cls._build_filename(file)
        relative_dir, dir_path = cls._get_storage_paths(upload_data.scope, current_user.user.user_id)
        file_path = os.path.join(dir_path, filename)
        total_size = 0

        async with aiofiles.open(file_path, 'wb') as stream:
            while True:
                chunk = await file.read(1024 * 1024 * 2)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > cls.MAX_FILE_SIZE:
                    await stream.close()
                    UploadUtil.delete_file(file_path)
                    raise ServiceException(message='文件大小超过限制，最大支持20MB')
                await stream.write(chunk)

        document_url = f'{UploadConfig.UPLOAD_PREFIX}/{relative_dir}/{filename}'.replace('\\', '/')
        document = KnowledgeDocumentModel(
            documentName=filename,
            originName=file.filename,
            documentUrl=document_url,
            documentPath=file_path,
            fileExt=file_ext,
            fileSize=total_size,
            scope=upload_data.scope,
            status='indexing',
            providerName=KnowledgeProviderManager.get_default_provider_name(),
            userId=current_user.user.user_id,
            deptId=current_user.user.dept_id,
            createBy=current_user.user.user_name,
            createTime=datetime.now(),
            updateBy=current_user.user.user_name,
            updateTime=datetime.now(),
        )
        db_document = await KnowledgeDocumentDao.add_document_dao(query_db, document)
        await query_db.commit()
        await query_db.refresh(db_document)

        try:
            await KnowledgeTaskQueueService.enqueue_document_index(
                request.app.state.redis,
                db_document.document_id,
                provider_name=KnowledgeProviderManager.get_default_provider_name(),
                source='upload',
            )
        except Exception as exc:
            await KnowledgeDocumentDao.edit_document_dao(
                query_db,
                {
                    'document_id': db_document.document_id,
                    'status': 'error',
                    'error_message': f'索引任务入队失败：{exc}'[:500],
                    'update_time': datetime.now(),
                },
            )
            await query_db.commit()
            raise ServiceException(message='知识库文档上传成功，但索引任务入队失败') from exc

        return CrudResponseModel(
            is_success=True,
            message='知识库文档已上传，正在建立索引',
            result=KnowledgeDocumentModel(**CamelCaseUtil.transform_result(db_document)),
        )

    @classmethod
    async def delete_document_services(
        cls, query_db: AsyncSession, document_id: int, current_user: CurrentUserModel
    ) -> CrudResponseModel:
        document = await KnowledgeDocumentDao.get_document_detail_by_id(query_db, document_id)
        if document is None:
            raise ServiceException(message='知识库文档不存在')
        if not await cls._can_delete_document(query_db, document, current_user):
            raise ServiceException(message='没有权限删除该知识库文档')

        delete_failures: list[str] = []
        for provider_name in cls._build_delete_provider_names(document):
            try:
                KnowledgeProviderManager.delete_document(document_id, provider_name=provider_name)
            except Exception as exc:
                logger.warning(f'删除知识库索引失败 provider={provider_name}, document_id={document_id}, error={exc}')
                delete_failures.append(f'{provider_name}: {exc}')
        if delete_failures:
            provider_name = cls._resolve_document_provider_name(document, use_default_for_untracked=True)
            await KnowledgeDocumentDao.edit_document_dao(
                query_db,
                {
                    'document_id': document_id,
                    'status': 'error',
                    'provider_name': provider_name,
                    'error_message': f'删除未完成，请重试。索引清理失败：{" | ".join(delete_failures)}'[:500],
                    'update_time': datetime.now(),
                },
            )
            await query_db.commit()
            raise ServiceException(message='删除失败，索引未完全清理，已保留文档记录以便重试')
        await KnowledgeDocumentDao.delete_document_dao(query_db, document_id)
        await query_db.commit()
        if document.document_path and os.path.exists(document.document_path):
            try:
                UploadUtil.delete_file(document.document_path)
            except Exception as exc:
                logger.warning(f'删除知识库源文件失败 document_id={document_id}, path={document.document_path}, error={exc}')

        return CrudResponseModel(is_success=True, message='删除成功')

    @classmethod
    async def reindex_document_services(
        cls,
        request: Request,
        query_db: AsyncSession,
        document_id: int,
        current_user: CurrentUserModel,
        reindex_config: KnowledgeDocumentReindexModel,
    ) -> CrudResponseModel:
        document = await KnowledgeDocumentDao.get_document_detail_by_id(query_db, document_id)
        if document is None:
            raise ServiceException(message='知识库文档不存在')
        if not await cls._can_delete_document(query_db, document, current_user):
            raise ServiceException(message='没有权限重新索引该知识库文档')
        if document.status == 'indexing':
            raise ServiceException(message='该文档正在索引中，请稍后再试')

        if not document.document_path or not os.path.exists(document.document_path):
            raise ServiceException(message='知识库源文件不存在，无法重新索引')

        _, _, remark_data = cls._resolve_document_chunk_config(document, reindex_config)

        await KnowledgeDocumentDao.edit_document_dao(
            query_db,
            {
                'document_id': document_id,
                'status': 'indexing',
                'error_message': None,
                'indexed_time': None,
                'remark': cls._dump_remark_data(remark_data),
                'update_time': datetime.now(),
            },
        )
        await query_db.commit()

        try:
            await KnowledgeTaskQueueService.enqueue_document_index(
                request.app.state.redis,
                document_id,
                provider_name=KnowledgeProviderManager.get_default_provider_name(),
                source='reindex',
            )
        except Exception as exc:
            await KnowledgeDocumentDao.edit_document_dao(
                query_db,
                {
                    'document_id': document_id,
                    'status': 'error',
                    'error_message': f'索引任务入队失败：{exc}'[:500],
                    'update_time': datetime.now(),
                },
            )
            await query_db.commit()
            raise ServiceException(message='重新索引任务入队失败') from exc

        return CrudResponseModel(is_success=True, message='已提交重新索引任务')

    @classmethod
    async def run_document_indexing(cls, document_id: int) -> None:
        async with AsyncSessionLocal() as query_db:
            document = await KnowledgeDocumentDao.get_document_detail_by_id(query_db, document_id)
            if document is None:
                return
            target_provider_name = KnowledgeProviderManager.get_default_provider_name()
            previous_provider_name = cls._resolve_document_provider_name(document)
            try:
                chunk_size, chunk_overlap, remark_data = cls._resolve_document_chunk_config(document)
                remark_data[cls.PROVIDER_REMARK_KEY] = target_provider_name

                preview, chunk_count = await asyncio.to_thread(
                    partial(
                        KnowledgeProviderManager.index_document,
                        document,
                        provider_name=target_provider_name,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                    )
                )
                if previous_provider_name != target_provider_name:
                    try:
                        await asyncio.to_thread(
                            partial(
                                KnowledgeProviderManager.delete_document,
                                document.document_id,
                                provider_name=previous_provider_name,
                            )
                        )
                    except Exception as exc:
                        logger.warning(
                            f'清理历史知识库索引失败 provider={previous_provider_name}, '
                            f'document_id={document.document_id}, error={exc}'
                        )
                await KnowledgeDocumentDao.edit_document_dao(
                    query_db,
                    {
                        'document_id': document_id,
                        'status': 'ready',
                        'provider_name': target_provider_name,
                        'chunk_count': chunk_count,
                        'content_preview': preview,
                        'indexed_time': datetime.now(),
                        'error_message': None,
                        'remark': cls._dump_remark_data(remark_data),
                        'update_time': datetime.now(),
                    },
                )
                await query_db.commit()
            except Exception as e:
                logger.exception(e)
                try:
                    _, _, remark_data = cls._resolve_document_chunk_config(document)
                except ServiceException:
                    remark_data = cls._load_remark_data(document.remark)
                remark_data[cls.PROVIDER_REMARK_KEY] = target_provider_name
                await KnowledgeDocumentDao.edit_document_dao(
                    query_db,
                    {
                        'document_id': document_id,
                        'status': 'error',
                        'provider_name': target_provider_name,
                        'error_message': str(e)[:500],
                        'remark': cls._dump_remark_data(remark_data),
                        'update_time': datetime.now(),
                    },
                )
                await query_db.commit()

    @classmethod
    async def _build_document_preview(cls, document_path: str, file_ext: str | None) -> tuple[str, int]:
        if not os.path.exists(document_path):
            raise ServiceException(message='知识库源文件不存在')
        file_size = os.path.getsize(document_path)
        chunk_count = max(1, math.ceil(file_size / 1500))

        if file_ext in {'.txt', '.md'}:
            async with aiofiles.open(document_path, 'r', encoding='utf-8', errors='ignore') as stream:
                content = await stream.read(4000)
            normalized = ' '.join(content.split())
            preview = normalized[:300]
            if preview:
                chunk_count = max(1, math.ceil(len(normalized) / 500))
            return preview, chunk_count

        filename = os.path.basename(document_path)
        preview = f'{filename} 已进入知识库索引队列，当前版本完成了文档接收、状态流转与基础切片统计。'

        return preview, chunk_count

    @classmethod
    async def _get_related_dept_ids(cls, query_db: AsyncSession, dept_id: int | None) -> set[int]:
        if not dept_id:
            return set()

        dept_ids = {int(dept_id)}
        dept_detail = await DeptDao.get_dept_detail_by_id(query_db, int(dept_id))
        if dept_detail and dept_detail.ancestors:
            dept_ids.update(int(item) for item in dept_detail.ancestors.split(',') if item and item != '0')

        children = await DeptDao.get_children_dept_dao(query_db, int(dept_id))
        dept_ids.update(int(item.dept_id) for item in children if item.dept_id)

        return dept_ids

    @classmethod
    async def _build_visibility_sql(cls, query_db: AsyncSession, current_user: CurrentUserModel) -> ColumnElement:
        if current_user.user.admin:
            return True

        dept_ids = await cls._get_related_dept_ids(query_db, current_user.user.dept_id)
        conditions = [
            KnowledgeDocument.scope == 'enterprise',
            and_(KnowledgeDocument.scope == 'personal', KnowledgeDocument.user_id == current_user.user.user_id),
        ]
        if dept_ids:
            conditions.append(
                and_(KnowledgeDocument.scope == 'department', KnowledgeDocument.dept_id.in_(dept_ids))
            )

        return or_(*conditions)

    @classmethod
    async def _can_access_document(
        cls, query_db: AsyncSession, document: KnowledgeDocument, current_user: CurrentUserModel
    ) -> bool:
        if current_user.user.admin:
            return True
        if document.scope == 'enterprise':
            return True
        if document.scope == 'personal':
            return document.user_id == current_user.user.user_id
        if document.scope == 'department':
            dept_ids = await cls._get_related_dept_ids(query_db, current_user.user.dept_id)
            return bool(document.dept_id and document.dept_id in dept_ids)

        return False

    @classmethod
    async def _can_delete_document(
        cls, query_db: AsyncSession, document: KnowledgeDocument, current_user: CurrentUserModel
    ) -> bool:
        if current_user.user.admin:
            return True
        if document.scope == 'enterprise':
            return False
        if document.scope == 'personal':
            return document.user_id == current_user.user.user_id
        if document.scope == 'department':
            if document.user_id == current_user.user.user_id:
                return True
            dept_ids = await cls._get_related_dept_ids(query_db, current_user.user.dept_id)
            return bool(document.dept_id and document.dept_id in dept_ids and current_user.user.dept_id == document.dept_id)

        return False

    @classmethod
    async def get_accessible_ready_document_ids(
        cls,
        query_db: AsyncSession,
        current_user: CurrentUserModel,
        selected_document_ids: list[int] | None = None,
    ) -> list[int]:
        visible_sql = await cls._build_visibility_sql(query_db, current_user)

        return await KnowledgeDocumentDao.get_document_id_list(
            query_db,
            visible_sql=visible_sql,
            status='ready',
            document_ids=selected_document_ids,
        )

    @classmethod
    async def get_accessible_ready_documents(
        cls,
        query_db: AsyncSession,
        current_user: CurrentUserModel,
        selected_document_ids: list[int] | None = None,
    ) -> list[KnowledgeDocument]:
        visible_sql = await cls._build_visibility_sql(query_db, current_user)

        return await KnowledgeDocumentDao.get_document_list_by_ids(
            query_db,
            visible_sql=visible_sql,
            status='ready',
            document_ids=selected_document_ids,
        )

    @classmethod
    async def search_knowledge_chunks(
        cls,
        query_db: AsyncSession,
        current_user: CurrentUserModel,
        query: str,
        selected_document_ids: list[int] | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        documents = await cls.get_accessible_ready_documents(query_db, current_user, selected_document_ids)
        if not documents:
            return []

        provider_document_ids: dict[str, list[int]] = {}
        for document in documents:
            provider_name = cls._resolve_document_provider_name(document)
            provider_document_ids.setdefault(provider_name, []).append(int(document.document_id))

        results = []
        for provider_name, document_ids in provider_document_ids.items():
            results.extend(
                KnowledgeProviderManager.search(
                    query=query,
                    document_ids=document_ids,
                    limit=limit,
                    provider_name=provider_name,
                )
            )
        results.sort(key=lambda item: item.score if item.score is not None else float('-inf'), reverse=True)
        if limit:
            results = results[:limit]

        return [
            {
                'document_id': item.document_id,
                'scope': item.scope,
                'user_id': item.user_id,
                'dept_id': item.dept_id,
                'content': item.content,
                'score': item.score,
            }
            for item in results
        ]
