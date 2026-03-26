import json
import os
import uuid
from collections.abc import AsyncGenerator, AsyncIterator
from datetime import datetime
from typing import TYPE_CHECKING, Any

from agno.agent import Agent
from agno.db.base import SessionType
from agno.media import Image
from agno.run.agent import RunEvent, RunOutput, RunOutputEvent
from agno.run.cancel import acancel_run
from agno.utils.message import get_text_from_message
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import CrudResponseModel
from config.env import DataBaseConfig, UploadConfig
from exceptions.exception import ServiceException
from module_ai.dao.ai_chat_dao import AiChatConfigDao
from module_ai.dao.ai_model_dao import AiModelDao
from module_ai.entity.do.ai_chat_do import AiChatConfig
from module_ai.entity.vo.ai_chat_vo import (
    AgentDataModel,
    AiChatConfigModel,
    AiChatRequestModel,
    AiChatSessionBaseModel,
    AiChatSessionModel,
    ChatMessageModel,
    MessageMetrics,
    SessionDataModel,
    SessionMetricsModel,
)
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_ai.entity.vo.ai_model_vo import AiModelModel
from module_knowledge.service.knowledge_document_service import KnowledgeDocumentService
from utils.ai_util import AiUtil
from utils.common_util import CamelCaseUtil
from utils.crypto_util import CryptoUtil
from utils.log_util import logger

if TYPE_CHECKING:
    from agno.models.message import Message
    from agno.run.team import TeamRunOutput
    from agno.run.workflow import WorkflowRunOutput
    from agno.session import Session


class AiChatService:
    """
    AI对话服务层
    """

    SESSION_TITLE_KEY = 'session_title'
    SESSION_TITLE_MAX_LENGTH = 50

    @classmethod
    def _normalize_session_title(cls, raw_text: str | None) -> str:
        """
        标准化会话标题

        :param raw_text: 原始标题
        :return: 处理后的标题
        """
        if not raw_text:
            return ''
        normalized = ' '.join(str(raw_text).split())
        if len(normalized) <= cls.SESSION_TITLE_MAX_LENGTH:
            return normalized
        return normalized[: cls.SESSION_TITLE_MAX_LENGTH - 3].rstrip() + '...'

    @classmethod
    def _resolve_session_title(cls, session_data: dict[str, Any] | None, runs: list[Any] | None = None) -> str:
        """
        解析会话标题，优先使用自定义标题，其次回退到首条用户提问

        :param session_data: 会话数据
        :param runs: 会话运行记录
        :return: 会话标题
        """
        session_data = session_data or {}
        custom_title = cls._normalize_session_title(session_data.get(cls.SESSION_TITLE_KEY))
        if custom_title:
            return custom_title

        for run in runs or []:
            input_content = getattr(getattr(run, 'input', None), 'input_content', None)
            derived_title = cls._normalize_session_title(input_content)
            if derived_title:
                return derived_title

        return '新对话'

    @classmethod
    def _resolve_temperature(cls, user_config: AiChatConfigModel, model_config: AiModelModel) -> float:
        """
        解析温度配置，优先级为 用户配置 > 模型配置

        :param user_config: 用户配置对象
        :param model_config: 模型配置对象
        :return: 解析后的温度值
        """
        temperature = user_config.temperature or model_config.temperature
        return temperature

    @classmethod
    def _resolve_request_temperature(
        cls, chat_req: AiChatRequestModel, user_config: AiChatConfigModel, model_config: AiModelModel
    ) -> float | None:
        """
        解析本次请求的温度配置，优先级为 本次请求 > 用户配置 > 模型配置

        :param chat_req: 对话请求对象
        :param user_config: 用户配置对象
        :param model_config: 模型配置对象
        :return: 解析后的温度值
        """
        if chat_req.temperature is not None:
            return chat_req.temperature
        return cls._resolve_temperature(user_config, model_config)

    @classmethod
    def _resolve_is_reasoning(cls, chat_req: AiChatRequestModel, model_config: AiModelModel) -> bool:
        """
        解析深度思考开关，结合请求参数与模型配置确定最终是否开启

        :param chat_req: 对话请求对象
        :param model_config: 模型配置对象
        :return: 是否开启深度思考
        """
        if model_config.support_reasoning != 'Y':
            return False
        return bool(chat_req.is_reasoning)

    @classmethod
    def _resolve_history_config(cls, user_config: AiChatConfigModel) -> tuple[bool, int]:
        """
        解析历史消息配置，确定是否附带历史以及轮数

        :param user_config: 用户配置对象
        :return: (是否附带历史, 历史轮数)
        """
        add_history = user_config.add_history_to_context == '0'
        num_history = user_config.num_history_runs or 3

        return bool(add_history), int(num_history)

    @classmethod
    def _build_agent(
        cls,
        model_config: AiModelModel,
        temperature: float,
        system_prompt: str | None,
        user_id: int,
        session_id: str,
        add_history: bool,
        num_history: int,
    ) -> Agent:
        """
        构建对话Agent对象

        :param model_config: 模型配置对象
        :param temperature: 对话温度
        :param system_prompt: 系统提示词
        :param user_id: 用户ID
        :param session_id: 会话ID
        :param add_history: 是否附带历史消息
        :param num_history: 历史消息轮数
        :return: Agent对象
        """
        real_api_key = CryptoUtil.decrypt(model_config.api_key)

        model = AiUtil.get_model_from_factory(
            provider=model_config.provider,
            model_code=model_config.model_code,
            model_name=model_config.model_name,
            api_key=real_api_key,
            base_url=model_config.base_url,
            temperature=temperature,
            max_tokens=model_config.max_tokens,
        )
        storage = AiUtil.get_storage_engine()
        return Agent(
            model=model,
            id='chat-agent',
            description=system_prompt or 'You are a helpful AI assistant.',
            db=storage,
            user_id=str(user_id),
            session_id=session_id,
            add_history_to_context=add_history,
            num_history_runs=num_history,
            markdown=True,
        )

    @classmethod
    def _build_knowledge_prompt(cls, knowledge_chunks: list[dict]) -> str:
        if not knowledge_chunks:
            return ''

        prompt_parts = [
            '以下是从知识库检索到的参考资料，请优先基于这些资料回答；如果资料不足，请明确说明，并可结合通用知识补充。',
        ]
        for index, item in enumerate(knowledge_chunks, start=1):
            scope_label = {
                'enterprise': '企业知识',
                'department': '部门知识',
                'personal': '个人知识',
            }.get(item.get('scope'), '知识库')
            score = item.get('score')
            score_text = f'，相关度 {score:.4f}' if isinstance(score, (int, float)) else ''
            prompt_parts.append(
                f'[{index}] 文档ID={item.get("document_id")}，范围={scope_label}{score_text}\n{item.get("content", "")}'
            )

        return '\n\n'.join(prompt_parts)

    @classmethod
    def _build_run_kwargs(
        cls,
        chat_req: AiChatRequestModel,
        user_config: AiChatConfigModel,
    ) -> dict[str, Any]:
        """
        构造Agent运行参数

        :param chat_req: 对话请求对象
        :param user_config: 用户配置对象
        :return: 运行参数字典
        """
        run_kwargs: dict[str, Any] = {'stream': True, 'stream_events': True}
        if not chat_req.images or not user_config.vision_enabled:
            return run_kwargs

        processed_images: list[Image] = []
        for img in chat_req.images:
            if img and img.startswith(UploadConfig.UPLOAD_PREFIX):
                relative_path = img[len(UploadConfig.UPLOAD_PREFIX) :]
                if relative_path.startswith('/'):
                    relative_path = relative_path[1:]
                file_path = os.path.join(UploadConfig.UPLOAD_PATH, relative_path)
                abs_path = os.path.abspath(file_path)
                if os.path.exists(abs_path):
                    processed_images.append(Image(filepath=abs_path))
        run_kwargs['images'] = processed_images
        return run_kwargs

    @classmethod
    def _convert_images_to_upload_paths(cls, images: list[Image] | None) -> list[str] | None:
        """
        将Agno Image对象列表转换为前端可访问的上传路径列表

        :param images: Image对象列表
        :return: 上传路径列表
        """
        if not images:
            return None

        result = []
        for img in images:
            # 如果是本地文件路径
            if hasattr(img, 'filepath') and img.filepath:
                try:
                    # 使用 abspath 确保路径标准化
                    abs_filepath = os.path.abspath(img.filepath)
                    abs_upload_path = os.path.abspath(UploadConfig.UPLOAD_PATH)

                    if abs_filepath.startswith(abs_upload_path):
                        relative_path = os.path.relpath(abs_filepath, abs_upload_path)
                        # 转换路径分隔符为URL格式
                        url_path = relative_path.replace(os.sep, '/')
                        # 拼接前缀
                        full_url = f'{UploadConfig.UPLOAD_PREFIX}/{url_path}'.replace('//', '/')
                        result.append(full_url)
                    else:
                        result.append(img.filepath)
                except Exception:
                    result.append(img.filepath)
            # 如果是URL
            elif hasattr(img, 'url') and img.url:
                result.append(img.url)

        return result if result else None

    @classmethod
    async def _stream_agent(
        cls,
        agent: Agent,
        chat_req: AiChatRequestModel,
        run_kwargs: dict[str, Any],
        is_reasoning: bool,
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        将Agent输出流式转换为前端SSE消息

        :param agent: Agent实例
        :param chat_req: 对话请求对象
        :param run_kwargs: 运行参数字典
        :param is_reasoning: 是否输出推理内容
        :param session_id: 会话ID
        :return: SSE消息生成器
        """
        full_response = ''
        full_reasoning = ''
        try:
            yield json.dumps({'session_id': session_id, 'type': 'meta'}) + '\n'

            response_stream: AsyncIterator[RunOutputEvent] = agent.arun(chat_req.message, **run_kwargs)

            async for chunk in response_stream:
                content = None
                reasoning = None

                if chunk.event == RunEvent.run_started and chunk.run_id:
                    yield json.dumps({'run_id': chunk.run_id, 'type': 'run_info'}) + '\n'

                if chunk.event == RunEvent.run_content:
                    content = get_text_from_message(chunk.content) if chunk.content is not None else ''
                    if hasattr(chunk, 'reasoning_content') and chunk.reasoning_content:
                        reasoning = chunk.reasoning_content

                if chunk.event == RunEvent.reasoning_content_delta and getattr(chunk, 'reasoning_content', None):
                    reasoning = chunk.reasoning_content

                if chunk.event == RunEvent.run_completed:
                    if not full_response and getattr(chunk, 'content', None) is not None:
                        completed_content = get_text_from_message(chunk.content)
                        if completed_content:
                            content = completed_content
                    if not full_reasoning and getattr(chunk, 'reasoning_content', None):
                        reasoning = chunk.reasoning_content

                if chunk.event == RunEvent.run_error:
                    error_msg = getattr(chunk, 'content', None) or '模型调用失败'
                    yield json.dumps({'error': str(error_msg), 'type': 'error'}) + '\n'
                    continue

                if reasoning and is_reasoning:
                    full_reasoning += reasoning
                    yield json.dumps({'content': reasoning, 'type': 'reasoning'}) + '\n'

                if chunk.event == RunEvent.run_completed and chunk.metrics:
                    yield (
                        json.dumps(
                            {'metrics': CamelCaseUtil.transform_result(chunk.metrics.to_dict()), 'type': 'metrics'}
                        )
                        + '\n'
                    )

                if content:
                    full_response += content
                    yield json.dumps({'content': content, 'type': 'content'}) + '\n'
        except Exception as e:
            yield json.dumps({'error': str(e), 'type': 'error'}) + '\n'

    @classmethod
    async def chat_services(
        cls, query_db: AsyncSession, chat_req: AiChatRequestModel, current_user: CurrentUserModel
    ) -> AsyncGenerator[str, None]:
        """
        流式对话

        :param query_db: orm对象
        :param chat_req: 对话请求对象
        :param user_id: 用户ID
        :return: 对话响应流
        """
        try:
            user_id = current_user.user.user_id
            ai_model = await AiModelDao.get_ai_model_detail_by_id(query_db, chat_req.model_id)
            if ai_model is None:
                raise ServiceException(message='模型不存在')
            model_config = AiModelModel(**CamelCaseUtil.transform_result(ai_model))

            user_config = await cls.ai_chat_config_detail_services(query_db, user_id)

            session_id = chat_req.session_id
            if not session_id:
                session_id = str(uuid.uuid4())

            temperature = cls._resolve_request_temperature(chat_req, user_config, model_config)
            is_reasoning = cls._resolve_is_reasoning(chat_req, model_config)
            add_history, num_history = cls._resolve_history_config(user_config)
            system_prompt = user_config.system_prompt
            if chat_req.use_knowledge:
                knowledge_chunks = await KnowledgeDocumentService.search_knowledge_chunks(
                    query_db=query_db,
                    current_user=current_user,
                    query=chat_req.message,
                    selected_document_ids=chat_req.knowledge_document_ids,
                    limit=6,
                )
                knowledge_prompt = cls._build_knowledge_prompt(knowledge_chunks)
                if knowledge_prompt:
                    system_prompt = '\n\n'.join(filter(None, [system_prompt, knowledge_prompt]))

            agent = cls._build_agent(
                model_config=model_config,
                temperature=temperature,
                system_prompt=system_prompt,
                user_id=user_id,
                session_id=session_id,
                add_history=add_history,
                num_history=num_history,
            )
            run_kwargs = cls._build_run_kwargs(chat_req, user_config)
            async for chunk in cls._stream_agent(
                agent=agent,
                chat_req=chat_req,
                run_kwargs=run_kwargs,
                is_reasoning=is_reasoning,
                session_id=session_id,
            ):
                yield chunk
        except Exception as e:
            logger.exception(e)
            yield json.dumps({'error': str(e), 'type': 'error'}) + '\n'

    @classmethod
    async def ai_chat_config_detail_services(cls, query_db: AsyncSession, user_id: int) -> AiChatConfigModel:
        """
        获取用户配置

        :param query_db: orm对象
        :param user_id: 用户ID
        :return: 配置模型
        """
        chat_config = await AiChatConfigDao.get_chat_config_detail_by_user_id(query_db, user_id)
        result = AiChatConfigModel(**CamelCaseUtil.transform_result(chat_config)) if chat_config else AiChatConfig()

        return result

    @classmethod
    async def save_ai_chat_config_services(
        cls, query_db: AsyncSession, user_id: int, page_object: AiChatConfigModel
    ) -> CrudResponseModel:
        """
        保存用户配置

        :param query_db: orm对象
        :param user_id: 用户ID
        :param page_object: AI对话配置对象
        :return: 更新后的配置模型
        """
        chat_config = await AiChatConfigDao.get_chat_config_detail_by_user_id(query_db, user_id)
        if page_object.user_id is None:
            page_object.user_id = user_id

        try:
            if chat_config:
                if chat_config.chat_config_id != page_object.chat_config_id:
                    raise ServiceException(message='只允许修改当前用户的配置')
                page_object.update_time = datetime.now()
                edit_ai_chat_config = page_object.model_dump(exclude_unset=True)
                await AiChatConfigDao.edit_chat_config_dao(query_db, edit_ai_chat_config)
            else:
                page_object.create_time = datetime.now()
                await AiChatConfigDao.add_chat_config_dao(query_db, page_object)

            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='保存成功')

    @classmethod
    async def get_chat_session_list_services(cls, user_id: int) -> list[AiChatSessionBaseModel]:
        """
        获取用户会话列表

        :param user_id: 用户ID
        :return: 用户会话列表
        """
        # 获取Agno会话列表
        storage = AiUtil.get_storage_engine()
        sessions: list[Session] = await storage.get_sessions(
            user_id=str(user_id),
            component_id='chat-agent',
            session_type=SessionType.AGENT,
        )

        result = []
        for s in sessions:
            created_at = datetime.fromtimestamp(s.created_at) if s.created_at else None
            updated_at = datetime.fromtimestamp(s.updated_at) if s.updated_at else None
            session_title = cls._resolve_session_title(getattr(s, 'session_data', None), getattr(s, 'runs', None))

            result.append(
                AiChatSessionBaseModel(
                    sessionId=s.session_id,
                    sessionTitle=session_title,
                    userId=s.user_id,
                    createdAt=created_at,
                    updatedAt=updated_at,
                )
            )
        return result

    @classmethod
    async def delete_chat_session_services(cls, session_id: str) -> CrudResponseModel:
        """
        删除会话

        :param session_id: 会话ID
        :return: 删除结果
        """
        storage = AiUtil.get_storage_engine()
        delete_result = await storage.delete_session(session_id=session_id)
        if not delete_result:
            raise ServiceException(message='删除会话失败')
        return CrudResponseModel(is_success=True, message='删除成功')

    @classmethod
    async def get_chat_session_detail_services(cls, session_id: str) -> AiChatSessionModel:
        """
        获取会话消息详情

        :param session_id: 会话ID
        :return: 会话消息详情
        """
        storage = AiUtil.get_storage_engine()
        session: Session | None = await storage.get_session(session_id=session_id, session_type=SessionType.AGENT)

        if not session:
            raise ServiceException(message='会话不存在')

        session_data: dict[str, Any] = session.session_data or {}
        agent_data: dict[str, Any] = session.agent_data or {}
        runs: list[RunOutput | TeamRunOutput | WorkflowRunOutput] = session.runs
        messages: list[Message] = session.get_messages(skip_roles=['system'])

        run_metrics_map = {}
        if runs:
            for run in runs:
                if run.model_provider_data and (provider_id := run.model_provider_data.get('id')):
                    run_metrics_map[provider_id] = run.metrics

        chat_messages = []
        for m in messages:
            if hasattr(m, 'provider_data') and m.provider_data:
                provider_id = m.provider_data.get('id')
                if provider_id and provider_id in run_metrics_map:
                    m.metrics = run_metrics_map[provider_id]

            metrics_model = None
            if getattr(m, 'metrics', None) and hasattr(m.metrics, 'to_dict'):
                metrics_dict = m.metrics.to_dict()
                if metrics_dict:
                    metrics_model = MessageMetrics(**CamelCaseUtil.transform_result(metrics_dict))

            chat_messages.append(
                ChatMessageModel(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    images=cls._convert_images_to_upload_paths(m.images),
                    metrics=metrics_model,
                    createdAt=datetime.fromtimestamp(m.created_at) if m.created_at else None,
                    reasoningContent=m.reasoning_content,
                    fromHistory=m.from_history,
                    stopAfterToolCall=m.stop_after_tool_call,
                )
            )

        session_detail = AiChatSessionModel(
            sessionId=session.session_id,
            sessionTitle=cls._resolve_session_title(session_data, runs),
            userId=session.user_id,
            createdAt=datetime.fromtimestamp(session.created_at) if session.created_at else None,
            updatedAt=datetime.fromtimestamp(session.updated_at) if session.updated_at else None,
            agentId=session.agent_id,
            sessionData=SessionDataModel(
                sessionState=session_data.get('session_state'),
                sessionMetrics=SessionMetricsModel(
                    **CamelCaseUtil.transform_result(session_data.get('session_metrics'))
                ),
            ),
            agentData=AgentDataModel(**CamelCaseUtil.transform_result(agent_data)),
            messages=chat_messages,
        )

        return session_detail

    @classmethod
    async def update_chat_session_title_services(
        cls, query_db: AsyncSession, user_id: int, session_id: str, session_title: str
    ) -> CrudResponseModel:
        """
        更新会话标题

        :param query_db: 数据库会话
        :param user_id: 用户ID
        :param session_id: 会话ID
        :param session_title: 会话标题
        :return: 更新结果
        """
        storage = AiUtil.get_storage_engine()
        session: Session | None = await storage.get_session(session_id=session_id, session_type=SessionType.AGENT)
        if not session:
            raise ServiceException(message='会话不存在')
        if str(session.user_id) != str(user_id):
            raise ServiceException(message='无权修改该会话')

        normalized_title = cls._normalize_session_title(session_title)
        if not normalized_title:
            raise ServiceException(message='会话标题不能为空')

        next_session_data = dict(session.session_data or {})
        next_session_data[cls.SESSION_TITLE_KEY] = normalized_title
        session_data_json = json.dumps(next_session_data, ensure_ascii=False)

        if DataBaseConfig.db_type == 'postgresql':
            update_stmt = sql_text(
                """
                UPDATE ai_sessions
                SET session_data = CAST(:session_data AS jsonb),
                    updated_at = CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT)
                WHERE session_id = :session_id AND user_id = :user_id
                """
            )
        else:
            update_stmt = sql_text(
                """
                UPDATE ai_sessions
                SET session_data = CAST(:session_data AS JSON),
                    updated_at = UNIX_TIMESTAMP()
                WHERE session_id = :session_id AND user_id = :user_id
                """
            )

        try:
            result = await query_db.execute(
                update_stmt,
                {
                    'session_data': session_data_json,
                    'session_id': session_id,
                    'user_id': str(user_id),
                },
            )
            if result.rowcount == 0:
                raise ServiceException(message='更新会话标题失败')
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='重命名成功')

    @classmethod
    async def cancel_run_services(cls, run_id: str) -> CrudResponseModel:
        """
        取消运行

        :param run_id: 运行ID
        :return: 取消结果
        """
        cancel_result = await acancel_run(run_id)
        if not cancel_result:
            raise ServiceException(message='取消运行失败')
        return CrudResponseModel(is_success=True, message='取消成功')
