import asyncio
import json
import os
import uuid

from redis import asyncio as aioredis

from config.database import AsyncSessionLocal
from config.env import KnowledgeConfig
from module_knowledge.dao.knowledge_document_dao import KnowledgeDocumentDao
from utils.log_util import logger


class KnowledgeTaskQueueService:
    """
    知识库任务入队服务
    """

    @classmethod
    async def enqueue_document_index(
        cls,
        redis: aioredis.Redis,
        document_id: int,
        provider_name: str,
        source: str,
    ) -> None:
        await redis.xadd(
            KnowledgeConfig.knowledge_task_stream_key,
            {
                'task_type': 'document_index',
                'document_id': str(document_id),
                'provider_name': provider_name,
                'source': source,
                'payload': json.dumps(
                    {
                        'documentId': document_id,
                        'providerName': provider_name,
                        'source': source,
                    },
                    ensure_ascii=False,
                ),
            },
        )


class KnowledgeTaskWorkerService:
    """
    知识库任务消费服务
    """

    @classmethod
    async def _ensure_group(cls, redis: aioredis.Redis) -> None:
        try:
            await redis.xgroup_create(
                name=KnowledgeConfig.knowledge_task_stream_key,
                groupname=KnowledgeConfig.knowledge_task_stream_group,
                id='0-0',
                mkstream=True,
            )
        except Exception as exc:
            if 'BUSYGROUP' not in str(exc):
                raise

    @classmethod
    async def _claim_pending(cls, redis: aioredis.Redis, consumer_name: str) -> None:
        if KnowledgeConfig.knowledge_task_stream_claim_idle_ms <= 0:
            return
        start_id = '0-0'
        while True:
            result = await redis.xautoclaim(
                name=KnowledgeConfig.knowledge_task_stream_key,
                groupname=KnowledgeConfig.knowledge_task_stream_group,
                consumername=consumer_name,
                min_idle_time=KnowledgeConfig.knowledge_task_stream_claim_idle_ms,
                start_id=start_id,
                count=KnowledgeConfig.knowledge_task_stream_claim_batch_size,
            )
            if not result:
                return
            next_start_id, messages = result[0], result[1]
            if messages:
                await cls._process_messages(redis, KnowledgeConfig.knowledge_task_stream_key, messages)
            if not messages or next_start_id == start_id:
                return
            start_id = next_start_id

    @classmethod
    async def consume_stream(cls, redis: aioredis.Redis) -> None:
        await cls._ensure_group(redis)
        consumer_name = (
            f'{KnowledgeConfig.knowledge_task_stream_consumer_prefix}-{os.getpid()}-{uuid.uuid4().hex[:6]}'
        )
        last_claim_time = 0.0
        while True:
            try:
                now = asyncio.get_running_loop().time()
                if now - last_claim_time >= KnowledgeConfig.knowledge_task_stream_claim_interval_ms / 1000:
                    await cls._claim_pending(redis, consumer_name)
                    last_claim_time = now
                result = await redis.xreadgroup(
                    groupname=KnowledgeConfig.knowledge_task_stream_group,
                    consumername=consumer_name,
                    streams={KnowledgeConfig.knowledge_task_stream_key: '>'},
                    count=KnowledgeConfig.knowledge_task_stream_batch_size,
                    block=KnowledgeConfig.knowledge_task_stream_block_ms,
                )
                if not result:
                    continue
                for stream_name, messages in result:
                    await cls._process_messages(redis, stream_name, messages)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(f'知识库任务消费异常: {exc}')
                await asyncio.sleep(1)

    @classmethod
    async def _mark_document_error(cls, document_id: int, message: str) -> None:
        async with AsyncSessionLocal() as session:
            document = await KnowledgeDocumentDao.get_document_detail_by_id(session, document_id)
            if document is None:
                return
            await KnowledgeDocumentDao.edit_document_dao(
                session,
                {
                    'document_id': document_id,
                    'status': 'error',
                    'error_message': message[:500],
                },
            )
            await session.commit()

    @classmethod
    async def _process_messages(cls, redis: aioredis.Redis, stream_name: str, messages: list[tuple[str, dict]]) -> None:
        if not messages:
            return

        from module_knowledge.service.knowledge_document_service import KnowledgeDocumentService

        ack_ids: list[str] = []
        for message_id, data in messages:
            task_type = data.get('task_type')
            document_id_raw = data.get('document_id')
            if task_type != 'document_index' or not document_id_raw:
                ack_ids.append(message_id)
                continue

            try:
                await KnowledgeDocumentService.run_document_indexing(int(document_id_raw))
                ack_ids.append(message_id)
            except Exception as exc:
                logger.exception(exc)
                await cls._mark_document_error(int(document_id_raw), f'知识库任务执行失败：{exc}')
                ack_ids.append(message_id)

        if ack_ids:
            await redis.xack(stream_name, KnowledgeConfig.knowledge_task_stream_group, *ack_ids)
