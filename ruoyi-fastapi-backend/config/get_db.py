from collections.abc import AsyncGenerator

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import AsyncSessionLocal, Base, async_engine
from config.env import DataBaseConfig
from utils.log_util import logger


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    每一个请求处理完毕后会关闭当前连接，不同的请求使用不同的连接

    :return:
    """
    async with AsyncSessionLocal() as current_db:
        yield current_db


async def init_create_table() -> None:
    """
    应用启动时初始化数据库连接

    :return:
    """
    logger.info('🔎 初始化数据库连接...')
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_knowledge_document_schema)
    logger.info('✅️ 数据库连接成功')


def _ensure_knowledge_document_schema(sync_conn) -> None:
    """
    为历史数据库补齐知识库表缺失字段

    :param sync_conn: 同步连接
    :return: None
    """
    inspector = inspect(sync_conn)
    if not inspector.has_table('knowledge_document'):
        return

    column_names = {column['name'] for column in inspector.get_columns('knowledge_document')}
    if 'provider_name' in column_names:
        return

    logger.info('🧩 检测到 knowledge_document 缺少 provider_name 字段，开始自动补齐')
    if DataBaseConfig.db_type == 'postgresql':
        sync_conn.exec_driver_sql('ALTER TABLE knowledge_document ADD COLUMN provider_name VARCHAR(32)')
        sync_conn.exec_driver_sql("COMMENT ON COLUMN knowledge_document.provider_name IS '索引Provider'")
    else:
        sync_conn.exec_driver_sql(
            "ALTER TABLE knowledge_document ADD COLUMN provider_name VARCHAR(32) NULL COMMENT '索引Provider'"
        )


async def close_async_engine() -> None:
    """
    应用关闭时释放数据库连接池

    :return:
    """
    await async_engine.dispose()
