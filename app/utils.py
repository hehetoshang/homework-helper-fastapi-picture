import logging
import os
import time
import uuid
from typing import Dict, Any, Optional
import traceback
from fastapi import Request, Response
from fastapi.responses import JSONResponse

# 全局API调用统计
global_stats = {
    "api_calls": {
        "health": 0,
        "stats": 0,
        "add_question": 0,
        "batch_add_question": 0,
        "get_question": 0,
        "delete_question": 0,
        "search": 0
    },
    "error_count": 0,
    "start_time": time.time()
}


def setup_logging(log_level: str = "INFO"):
    """配置日志系统"""
    # 设置根日志级别
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 设置第三方库的日志级别
    logging.getLogger("pymilvus").setLevel(logging.WARNING)
    logging.getLogger("towhee").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    
    return logging.getLogger("vector_search_service")


async def log_request_middleware(request: Request, call_next):
    """请求日志中间件"""
    # 生成请求ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # 记录请求开始
    logger = logging.getLogger("vector_search_service")
    logger.info(f"[REQ:{request_id}] {request.method} {request.url}")
    
    # 记录请求体（如果是JSON）
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            if body:
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    # 对于JSON请求，记录部分内容（避免太大）
                    body_str = body.decode("utf-8")
                    if len(body_str) > 500:
                        body_str = body_str[:500] + "... [truncated]"
                    logger.debug(f"[REQ:{request_id}] Request body: {body_str}")
        except Exception:
            pass
    
    # 执行请求
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 更新API调用统计
        path = request.url.path
        if path == "/health":
            global_stats["api_calls"]["health"] += 1
        elif path == "/stats":
            global_stats["api_calls"]["stats"] += 1
        elif path == "/questions" and request.method == "POST":
            global_stats["api_calls"]["add_question"] += 1
        elif path == "/questions/batch" and request.method == "POST":
            global_stats["api_calls"]["batch_add_question"] += 1
        elif path.startswith("/questions/") and request.method == "GET":
            global_stats["api_calls"]["get_question"] += 1
        elif path.startswith("/questions/") and request.method == "DELETE":
            global_stats["api_calls"]["delete_question"] += 1
        elif path == "/search" and request.method == "POST":
            global_stats["api_calls"]["search"] += 1
        
        # 记录响应
        logger.info(f"[REQ:{request_id}] {response.status_code} {process_time:.4f}s")
        
        return response
    except Exception as e:
        # 记录错误
        process_time = time.time() - start_time
        global_stats["error_count"] += 1
        
        error_message = str(e)
        error_stack = traceback.format_exc()
        
        logger.error(f"[REQ:{request_id}] Error: {error_message}")
        logger.debug(f"[REQ:{request_id}] Stack trace: {error_stack}")
        
        # 返回通用错误响应
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "details": error_message,
                "request_id": request_id
            }
        )


def get_uptime() -> float:
    """获取服务运行时间（秒）"""
    return time.time() - global_stats["start_time"]


class RateLimiter:
    """简单的速率限制器"""
    def __init__(self, rate_limit: str = "100/minute"):
        """初始化速率限制器
        
        Args:
            rate_limit: 速率限制字符串，如 "100/minute" 或 "10/second"
        """
        self.rate_limit = rate_limit
        self.requests = {}
        
        # 解析速率限制
        parts = rate_limit.split("/")
        if len(parts) != 2:
            raise ValueError("无效的速率限制格式")
        
        self.limit = int(parts[0])
        self.interval = parts[1]
        
        # 转换为秒
        if self.interval == "second":
            self.interval_seconds = 1
        elif self.interval == "minute":
            self.interval_seconds = 60
        elif self.interval == "hour":
            self.interval_seconds = 3600
        else:
            raise ValueError(f"不支持的时间间隔: {self.interval}")
    
    def is_rate_limited(self, key: str) -> bool:
        """检查是否超过速率限制"""
        current_time = time.time()
        
        # 清理过期的请求记录
        if key in self.requests:
            # 只保留时间窗口内的请求
            self.requests[key] = [t for t in self.requests[key] if current_time - t < self.interval_seconds]
            
            # 检查是否超过限制
            if len(self.requests[key]) >= self.limit:
                return True
        else:
            self.requests[key] = []
        
        # 记录新请求
        self.requests[key].append(current_time)
        return False


def generate_error_response(status_code: int, error_type: str, message: str, request_id: Optional[str] = None) -> Dict[str, Any]:
    """生成标准化的错误响应"""
    response = {
        "error": error_type,
        "message": message,
    }
    
    if request_id:
        response["request_id"] = request_id
    
    return response