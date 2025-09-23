import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """项目配置类，管理环境变量和配置参数"""
    # 基础配置
    PROJECT_NAME: str = "FastAPI 向量搜索微服务"
    PROJECT_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Milvus 配置
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    MILVUS_COLLECTION_NAME: str = os.getenv("MILVUS_COLLECTION_NAME", "questions")
    MILVUS_INDEX_TYPE: str = os.getenv("MILVUS_INDEX_TYPE", "IVF_FLAT")
    MILVUS_METRIC_TYPE: str = os.getenv("MILVUS_METRIC_TYPE", "COSINE")
    MILVUS_NLIST: int = int(os.getenv("MILVUS_NLIST", "1024"))
    MILVUS_BATCH_SIZE: int = int(os.getenv("MILVUS_BATCH_SIZE", "100"))
    
    # 服务配置
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    WORKERS: int = int(os.getenv("WORKERS", "4"))
    
    # 缓存配置
    CACHE_SIZE: int = int(os.getenv("CACHE_SIZE", "1000"))
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 秒
    
    # 限流配置
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "100/minute")
    
    # 监控配置
    PROMETHEUS_ENABLED: bool = os.getenv("PROMETHEUS_ENABLED", "false").lower() == "true"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()