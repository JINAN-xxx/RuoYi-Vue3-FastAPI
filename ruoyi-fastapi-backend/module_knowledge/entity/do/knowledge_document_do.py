from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text

from config.database import Base
from config.env import DataBaseConfig
from utils.common_util import SqlalchemyUtil


class KnowledgeDocument(Base):
    """
    知识库文档表
    """

    __tablename__ = 'knowledge_document'
    __table_args__ = {'comment': '知识库文档表'}

    document_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='文档主键')
    document_name = Column(String(255), nullable=False, comment='存储文件名')
    origin_name = Column(String(255), nullable=False, comment='原始文件名')
    document_url = Column(String(500), nullable=False, comment='文档访问地址')
    document_path = Column(String(500), nullable=False, comment='文档物理路径')
    file_ext = Column(String(20), nullable=False, comment='文件后缀')
    file_size = Column(Integer, nullable=False, default=0, comment='文件大小')
    scope = Column(String(20), nullable=False, default='personal', comment='知识库范围')
    status = Column(String(20), nullable=False, default='indexing', comment='索引状态')
    chunk_count = Column(Integer, nullable=True, comment='切片数量')
    content_preview = Column(
        Text,
        nullable=True,
        server_default=SqlalchemyUtil.get_server_default_null(DataBaseConfig.db_type),
        comment='内容预览',
    )
    error_message = Column(
        String(500),
        nullable=True,
        server_default=SqlalchemyUtil.get_server_default_null(DataBaseConfig.db_type),
        comment='错误信息',
    )
    indexed_time = Column(DateTime, nullable=True, comment='索引完成时间')
    user_id = Column(BigInteger, nullable=False, comment='上传用户ID')
    dept_id = Column(BigInteger, nullable=True, comment='上传用户部门ID')
    create_by = Column(String(64), nullable=True, server_default="''", comment='创建者')
    create_time = Column(DateTime, nullable=True, default=datetime.now, comment='创建时间')
    update_by = Column(String(64), nullable=True, server_default="''", comment='更新者')
    update_time = Column(DateTime, nullable=True, default=datetime.now, comment='更新时间')
    remark = Column(
        String(500),
        nullable=True,
        server_default=SqlalchemyUtil.get_server_default_null(DataBaseConfig.db_type),
        comment='备注',
    )
