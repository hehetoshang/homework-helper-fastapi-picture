from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
import base64
import re


class QuestionRequest(BaseModel):
    """添加单个题目的请求模型"""
    question_id: str = Field(..., description="题目的唯一标识符")
    image_base64: str = Field(..., description="题目图片的Base64编码")
    metadata: Optional[Dict[str, Any]] = Field(None, description="题目相关的元数据")
    
    @validator("question_id")
    def validate_question_id(cls, v):
        """验证题目ID格式"""
        if not v or len(v) > 100:
            raise ValueError("题目ID不能为空且长度不能超过100个字符")
        return v
    
    @validator("image_base64")
    def validate_image_base64(cls, v):
        """验证Base64图片格式"""
        # 检查是否包含data URI前缀
        if v.startswith("data:image/"):
            # 提取Base64部分
            match = re.search(r"base64,(.+)", v)
            if match:
                v = match.group(1)
        
        # 验证Base64格式
        try:
            base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("无效的Base64编码")
        return v


class BatchQuestionRequest(BaseModel):
    """批量添加题目的请求模型"""
    questions: List[QuestionRequest] = Field(..., description="题目列表")
    
    @validator("questions")
    def validate_questions_length(cls, v):
        """验证批量添加的题目数量"""
        if len(v) == 0:
            raise ValueError("题目列表不能为空")
        if len(v) > 1000:
            raise ValueError("批量添加的题目数量不能超过1000个")
        return v


class SearchRequest(BaseModel):
    """搜索相似题目的请求模型"""
    image_base64: str = Field(..., description="搜索图片的Base64编码")
    top_k: int = Field(5, ge=1, le=100, description="返回的最大结果数量")
    search_method: str = Field("vector", regex="^(vector|hybrid)$", description="搜索方法: vector(纯向量) 或 hybrid(混合)")
    filters: Optional[Dict[str, Any]] = Field(None, description="搜索过滤条件")
    
    @validator("image_base64")
    def validate_search_image_base64(cls, v):
        """验证搜索图片的Base64格式"""
        return QuestionRequest.validate_image_base64(cls, v)


class SearchResult(BaseModel):
    """单个搜索结果模型"""
    question_id: str = Field(..., description="题目的唯一标识符")
    similarity: float = Field(..., description="相似度得分")
    metadata: Optional[Dict[str, Any]] = Field(None, description="题目相关的元数据")


class SearchResponse(BaseModel):
    """搜索响应模型"""
    results: List[SearchResult] = Field(..., description="搜索结果列表")
    total: int = Field(..., description="总结果数量")
    search_time: float = Field(..., description="搜索耗时(秒)")


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="服务版本")
    database: str = Field(..., description="数据库连接状态")
    uptime: float = Field(..., description="服务运行时间(秒)")


class StatsResponse(BaseModel):
    """统计信息响应模型"""
    question_count: int = Field(..., description="题目总数")
    collection_size: int = Field(..., description="集合大小(bytes)")
    avg_vector_size: float = Field(..., description="平均向量大小")
    api_calls: Dict[str, int] = Field(..., description="各API调用次数")
    error_count: int = Field(..., description="错误总数")