from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class KnowledgeDocumentModel(BaseModel):
    """
    知识库文档模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    document_id: int | None = Field(default=None, description='文档主键')
    document_name: str | None = Field(default=None, description='存储文件名')
    origin_name: str | None = Field(default=None, description='原始文件名')
    document_url: str | None = Field(default=None, description='文档访问地址')
    document_path: str | None = Field(default=None, description='文档物理路径')
    file_ext: str | None = Field(default=None, description='文件后缀')
    file_size: int | None = Field(default=None, description='文件大小')
    scope: Literal['enterprise', 'department', 'personal'] | None = Field(default=None, description='知识库范围')
    status: Literal['indexing', 'ready', 'error'] | None = Field(default=None, description='索引状态')
    chunk_count: int | None = Field(default=None, description='切片数量')
    content_preview: str | None = Field(default=None, description='内容预览')
    error_message: str | None = Field(default=None, description='错误信息')
    indexed_time: datetime | None = Field(default=None, description='索引完成时间')
    user_id: int | None = Field(default=None, description='上传用户ID')
    dept_id: int | None = Field(default=None, description='上传用户部门ID')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: datetime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: datetime | None = Field(default=None, description='更新时间')
    remark: str | None = Field(default=None, description='备注')


class KnowledgeDocumentPageQueryModel(KnowledgeDocumentModel):
    """
    知识库文档分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class KnowledgeDocumentUploadModel(BaseModel):
    """
    知识库文档上传模型
    """

    model_config = ConfigDict(alias_generator=to_camel)

    scope: Literal['enterprise', 'department', 'personal'] = Field(default='personal', description='知识库范围')
