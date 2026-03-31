from sqlalchemy import ColumnElement, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_knowledge.entity.do.knowledge_document_do import KnowledgeDocument
from module_knowledge.entity.vo.knowledge_document_vo import KnowledgeDocumentModel, KnowledgeDocumentPageQueryModel
from utils.page_util import PageUtil


class KnowledgeDocumentDao:
    """
    知识库文档数据库操作层
    """

    @classmethod
    async def get_document_detail_by_id(cls, db: AsyncSession, document_id: int) -> KnowledgeDocument | None:
        return (
            (await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.document_id == document_id)))
            .scalars()
            .first()
        )

    @classmethod
    async def get_document_list(
        cls,
        db: AsyncSession,
        query_object: KnowledgeDocumentPageQueryModel,
        visible_sql: ColumnElement,
        is_page: bool = False,
    ) -> PageModel | list[dict]:
        query = (
            select(KnowledgeDocument)
            .where(
                visible_sql,
                KnowledgeDocument.origin_name.like(f'%{query_object.origin_name}%') if query_object.origin_name else True,
                KnowledgeDocument.scope == query_object.scope if query_object.scope else True,
                KnowledgeDocument.status == query_object.status if query_object.status else True,
            )
            .order_by(KnowledgeDocument.create_time.desc(), KnowledgeDocument.document_id.desc())
        )

        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_document_id_list(
        cls,
        db: AsyncSession,
        visible_sql: ColumnElement,
        status: str | None = 'ready',
        document_ids: list[int] | None = None,
    ) -> list[int]:
        query = select(KnowledgeDocument.document_id).where(
            visible_sql,
            KnowledgeDocument.status == status if status else True,
            KnowledgeDocument.document_id.in_(document_ids) if document_ids else True,
        )

        return list((await db.execute(query)).scalars().all())

    @classmethod
    async def get_document_list_by_ids(
        cls,
        db: AsyncSession,
        visible_sql: ColumnElement,
        status: str | None = 'ready',
        document_ids: list[int] | None = None,
    ) -> list[KnowledgeDocument]:
        query = (
            select(KnowledgeDocument)
            .where(
                visible_sql,
                KnowledgeDocument.status == status if status else True,
                KnowledgeDocument.document_id.in_(document_ids) if document_ids else True,
            )
            .order_by(KnowledgeDocument.document_id.desc())
        )

        return list((await db.execute(query)).scalars().all())

    @classmethod
    async def add_document_dao(cls, db: AsyncSession, document: KnowledgeDocumentModel) -> KnowledgeDocument:
        db_document = KnowledgeDocument(**document.model_dump(exclude_unset=True))
        db.add(db_document)
        await db.flush()

        return db_document

    @classmethod
    async def edit_document_dao(cls, db: AsyncSession, document: dict) -> None:
        await db.execute(update(KnowledgeDocument), [document])

    @classmethod
    async def delete_document_dao(cls, db: AsyncSession, document_id: int) -> None:
        await db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.document_id == document_id))
