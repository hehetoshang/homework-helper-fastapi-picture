from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from typing import List, Dict, Any, Optional

from .config import settings
from .models import (
    QuestionRequest, BatchQuestionRequest, SearchRequest, 
    SearchResponse, SearchResult, HealthResponse, StatsResponse
)
from .milvus_client import milvus_client
from .pipelines import vector_pipeline
from .utils import (
    setup_logging, log_request_middleware, get_uptime,
    global_stats, RateLimiter, generate_error_response
)

# 导入Prometheus指标集成模块
from prometheus_fastapi_instrumentator import Instrumentator

# 配置日志
logger = setup_logging("INFO" if not settings.DEBUG else "DEBUG")

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="基于FastAPI + Towhee + Milvus的向量搜索微服务",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=settings.DEBUG
)

# 配置Prometheus指标收集器
instrumentator = Instrumentator()

# 启用基本指标收集
instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=True)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加请求日志中间件
app.middleware("http")(log_request_middleware)

# 创建速率限制器
rate_limiter = RateLimiter(settings.RATE_LIMIT)


# 依赖项：获取请求ID
def get_request_id(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)


# 依赖项：速率限制
def check_rate_limit(request: Request):
    """检查请求是否超过速率限制"""
    # 使用IP地址作为速率限制的键
    client_ip = request.client.host
    if rate_limiter.is_rate_limited(client_ip):
        request_id = get_request_id(request)
        error_response = generate_error_response(
            429,
            "Rate Limit Exceeded",
            f"超过请求限制: {settings.RATE_LIMIT}",
            request_id
        )
        raise HTTPException(
            status_code=429,
            detail=error_response
        )


# API端点
@app.get("/health", response_model=HealthResponse, tags=["基础服务"])
async def health_check(request: Request):
    """服务健康检查端点"""
    try:
        # 检查Milvus连接
        milvus_status = "connected"
        try:
            milvus_client.connect()
        except Exception:
            milvus_status = "disconnected"
            logger.error("Milvus连接失败")
        
        return HealthResponse(
            status="healthy",
            version=settings.PROJECT_VERSION,
            database=milvus_status,
            uptime=get_uptime()
        )
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "error": str(e)}
        )


@app.get("/stats", response_model=StatsResponse, tags=["基础服务"])
async def get_stats(request: Request):
    """获取服务统计信息"""
    try:
        # 获取Milvus统计信息
        milvus_stats = milvus_client.get_stats()
        
        return StatsResponse(
            question_count=milvus_stats["question_count"],
            collection_size=milvus_stats["collection_size"],
            avg_vector_size=milvus_stats["avg_vector_size"],
            api_calls=global_stats["api_calls"],
            error_count=global_stats["error_count"]
        )
    except Exception as e:
        request_id = get_request_id(request)
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=generate_error_response(
                500,
                "Internal Server Error",
                str(e),
                request_id
            )
        )


@app.post("/questions", status_code=201, tags=["题目管理"])
async def add_question(
    question: QuestionRequest,
    request: Request,
    _: None = Depends(check_rate_limit)
):
    """添加单个题目向量"""
    try:
        # 检查题目是否已存在
        existing_question = milvus_client.get_by_id(question.question_id)
        if existing_question:
            raise HTTPException(
                status_code=409,
                detail={"error": "Conflict", "message": f"题目ID '{question.question_id}' 已存在"}
            )
        
        # 生成图片向量
        vector = vector_pipeline.vectorize_image(question.image_base64)
        
        # 插入Milvus
        milvus_client.insert(question.question_id, vector, question.metadata)
        
        return {
            "message": "题目添加成功",
            "question_id": question.question_id
        }
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        request_id = get_request_id(request)
        logger.error(f"添加题目失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=generate_error_response(
                500,
                "Internal Server Error",
                str(e),
                request_id
            )
        )


@app.post("/questions/batch", status_code=201, tags=["题目管理"])
async def batch_add_questions(
    batch_request: BatchQuestionRequest,
    request: Request,
    _: None = Depends(check_rate_limit)
):
    """批量添加题目向量"""
    try:
        # 准备批量插入数据
        batch_data = []
        for question in batch_request.questions:
            # 检查题目是否已存在
            existing_question = milvus_client.get_by_id(question.question_id)
            if existing_question:
                raise HTTPException(
                    status_code=409,
                    detail={"error": "Conflict", "message": f"题目ID '{question.question_id}' 已存在"}
                )
            
            # 生成图片向量
            vector = vector_pipeline.vectorize_image(question.image_base64)
            
            # 添加到批量数据
            batch_data.append((question.question_id, vector, question.metadata))
        
        # 批量插入Milvus
        milvus_client.batch_insert(batch_data)
        
        return {
            "message": "批量题目添加成功",
            "count": len(batch_request.questions)
        }
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        request_id = get_request_id(request)
        logger.error(f"批量添加题目失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=generate_error_response(
                500,
                "Internal Server Error",
                str(e),
                request_id
            )
        )


@app.get("/questions/{question_id}", tags=["题目管理"])
async def get_question(
    question_id: str,
    request: Request
):
    """根据ID查询题目信息"""
    try:
        # 查询题目
        question = milvus_client.get_by_id(question_id)
        
        if not question:
            raise HTTPException(
                status_code=404,
                detail={"error": "Not Found", "message": f"题目ID '{question_id}' 不存在"}
            )
        
        return question
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        request_id = get_request_id(request)
        logger.error(f"查询题目失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=generate_error_response(
                500,
                "Internal Server Error",
                str(e),
                request_id
            )
        )


@app.delete("/questions/{question_id}", status_code=204, tags=["题目管理"])
async def delete_question(
    question_id: str,
    request: Request
):
    """根据ID删除题目"""
    try:
        # 删除题目
        success = milvus_client.delete_by_id(question_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail={"error": "Not Found", "message": f"题目ID '{question_id}' 不存在"}
            )
        
        return None  # 204 响应不包含内容
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        request_id = get_request_id(request)
        logger.error(f"删除题目失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=generate_error_response(
                500,
                "Internal Server Error",
                str(e),
                request_id
            )
        )


@app.post("/search", response_model=SearchResponse, tags=["搜索功能"])
async def search_similar_questions(
    search_request: SearchRequest,
    request: Request,
    _: None = Depends(check_rate_limit)
):
    """搜索相似题目"""
    try:
        # 记录搜索开始时间
        start_time = time.time()
        
        # 生成搜索图片的向量
        search_vector = vector_pipeline.vectorize_image(search_request.image_base64)
        
        # 执行搜索
        search_results = milvus_client.search(
            search_vector,
            top_k=search_request.top_k,
            filters=search_request.filters
        )
        
        # 计算搜索耗时
        search_time = time.time() - start_time
        
        # 格式化搜索结果
        results = [
            SearchResult(
                question_id=result["question_id"],
                similarity=result["similarity"],
                metadata=result["metadata"]
            )
            for result in search_results
        ]
        
        return SearchResponse(
            results=results,
            total=len(results),
            search_time=search_time
        )
    except Exception as e:
        request_id = get_request_id(request)
        logger.error(f"搜索失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=generate_error_response(
                500,
                "Internal Server Error",
                str(e),
                request_id
            )
        )


# 全局异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理HTTP异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail if isinstance(exc.detail, dict) else {"error": str(exc.detail)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理所有其他异常"""
    request_id = get_request_id(request)
    logger.error(f"未捕获的异常: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content=generate_error_response(
            500,
            "Internal Server Error",
            "服务器内部错误，请联系管理员",
            request_id
        )
    )


# 应用启动和关闭事件
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"{settings.PROJECT_NAME} v{settings.PROJECT_VERSION} 启动中...")
    
    # 初始化Milvus连接
    try:
        milvus_client.connect()
        logger.info("Milvus连接初始化成功")
    except Exception as e:
        logger.error(f"Milvus连接初始化失败: {str(e)}")
        # 在启动时不抛出异常，允许服务继续运行
    
    logger.info(f"服务已成功启动，监听在 http://{settings.APP_HOST}:{settings.APP_PORT}")
    logger.info(f"API文档: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("服务正在关闭...")
    
    # 断开Milvus连接
    try:
        milvus_client.disconnect()
        logger.info("Milvus连接已断开")
    except Exception as e:
        logger.error(f"断开Milvus连接失败: {str(e)}")
    
    logger.info("服务已成功关闭")