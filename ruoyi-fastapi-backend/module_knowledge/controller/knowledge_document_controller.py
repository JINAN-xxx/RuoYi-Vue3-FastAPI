from typing import Annotated

from fastapi import BackgroundTasks, File, Form, Path, Query, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from common.annotation.log_annotation import Log
from common.aspect.db_seesion import DBSessionDependency
from common.aspect.interface_auth import UserInterfaceAuthDependency
from common.aspect.pre_auth import CurrentUserDependency, PreAuthDependency
from common.enums import BusinessType
from common.router import APIRouterPro
from common.vo import DataResponseModel, DynamicResponseModel, PageResponseModel, ResponseBaseModel
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_knowledge.entity.vo.knowledge_document_vo import (
    KnowledgeDocumentModel,
    KnowledgeDocumentPageQueryModel,
    KnowledgeDocumentUploadModel,
)
from module_knowledge.service.knowledge_document_service import KnowledgeDocumentService
from utils.log_util import logger
from utils.response_util import ResponseUtil

knowledge_document_controller = APIRouterPro(
    prefix='/ai/knowledge', order_num=20, tags=['AI管理-知识库'], dependencies=[PreAuthDependency()]
)


@knowledge_document_controller.get(
    '/list',
    summary='获取知识库文档分页列表接口',
    description='用于获取当前用户可见的知识库文档列表',
    response_model=PageResponseModel[KnowledgeDocumentModel],
    dependencies=[UserInterfaceAuthDependency('ai:knowledge:list')],
)
async def get_knowledge_document_list(
    request: Request,
    query_object: Annotated[KnowledgeDocumentPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await KnowledgeDocumentService.get_document_list_services(query_db, query_object, current_user, True)
    logger.info('获取成功')

    return ResponseUtil.success(model_content=result)


@knowledge_document_controller.get(
    '/all',
    summary='获取知识库文档列表接口',
    description='用于获取当前用户可见的知识库文档列表（不分页）',
    response_model=DataResponseModel[list[KnowledgeDocumentModel]],
    dependencies=[UserInterfaceAuthDependency('ai:knowledge:list')],
)
async def get_knowledge_document_all(
    request: Request,
    query_object: Annotated[KnowledgeDocumentPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await KnowledgeDocumentService.get_document_list_services(query_db, query_object, current_user, False)
    logger.info('获取成功')

    return ResponseUtil.success(data=result)


@knowledge_document_controller.get(
    '/{document_id}',
    summary='获取知识库文档详情接口',
    description='用于获取指定知识库文档详情',
    response_model=DataResponseModel[KnowledgeDocumentModel],
    dependencies=[UserInterfaceAuthDependency('ai:knowledge:query')],
)
async def get_knowledge_document_detail(
    request: Request,
    document_id: Annotated[int, Path(description='文档ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await KnowledgeDocumentService.document_detail_services(query_db, document_id, current_user)
    logger.info('获取成功')

    return ResponseUtil.success(data=result)


@knowledge_document_controller.post(
    '/upload',
    summary='上传知识库文档接口',
    description='用于上传知识库文档并异步建立索引',
    response_model=DynamicResponseModel[KnowledgeDocumentModel],
    dependencies=[UserInterfaceAuthDependency('ai:knowledge:upload')],
)
@Log(title='知识库管理', business_type=BusinessType.INSERT)
async def upload_knowledge_document(
    request: Request,
    background_tasks: BackgroundTasks,
    scope: Annotated[str, Form()] = 'personal',
    file: Annotated[UploadFile, File(...)] = None,
    query_db: Annotated[AsyncSession, DBSessionDependency()] = None,
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()] = None,
) -> Response:
    result = await KnowledgeDocumentService.upload_document_services(
        request=request,
        background_tasks=background_tasks,
        query_db=query_db,
        current_user=current_user,
        upload_data=KnowledgeDocumentUploadModel(scope=scope),
        file=file,
    )
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message, model_content=result.result)


@knowledge_document_controller.delete(
    '/{document_id}',
    summary='删除知识库文档接口',
    description='用于删除知识库文档',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('ai:knowledge:remove')],
)
@Log(title='知识库管理', business_type=BusinessType.DELETE)
async def delete_knowledge_document(
    request: Request,
    document_id: Annotated[int, Path(description='文档ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await KnowledgeDocumentService.delete_document_services(query_db, document_id, current_user)
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)
