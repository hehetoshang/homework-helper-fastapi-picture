from pymilvus import (connections, Collection, CollectionSchema, FieldSchema,
                      DataType, utility, Index, AnnSearchRequest)
from typing import List, Dict, Any, Optional, Tuple
from pymilvus.exceptions import (MilvusException, ConnectionNotExistException,
                                CollectionNotExistException)
import time
import logging
from retry import retry

from .config import settings

logger = logging.getLogger(__name__)


class MilvusClient:
    """Milvus数据库客户端，提供连接管理和向量操作功能"""
    def __init__(self):
        """初始化Milvus客户端"""
        self.host = settings.MILVUS_HOST
        self.port = settings.MILVUS_PORT
        self.collection_name = settings.MILVUS_COLLECTION_NAME
        self.index_type = settings.MILVUS_INDEX_TYPE
        self.metric_type = settings.MILVUS_METRIC_TYPE
        self.nlist = settings.MILVUS_NLIST
        self.vector_dim = 512  # CLIP模型的向量维度
        self.collection = None
        self.connected = False
        
    @retry(MilvusException, tries=3, delay=2, backoff=2)
    def connect(self):
        """连接到Milvus数据库"""
        try:
            # 检查连接是否已存在
            if connections.has_connection("default"):
                try:
                    # 测试连接
                    utility.get_server_version()
                    self.connected = True
                    logger.info("Milvus连接已存在且有效")
                    return
                except Exception:
                    # 连接无效，重新连接
                    connections.disconnect("default")
            
            # 创建新连接
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            
            self.connected = True
            logger.info(f"成功连接到Milvus服务器: {self.host}:{self.port}")
            
            # 确保集合存在
            self._ensure_collection_exists()
        except Exception as e:
            self.connected = False
            logger.error(f"连接Milvus服务器失败: {str(e)}")
            raise
    
    def _ensure_collection_exists(self):
        """确保集合存在，如果不存在则创建"""
        if not utility.has_collection(self.collection_name):
            self._create_collection()
        else:
            # 加载集合
            self.collection = Collection(self.collection_name)
            logger.info(f"已加载集合: {self.collection_name}")
            
            # 检查索引是否存在
            if not self._has_index():
                self._create_index()
    
    def _create_collection(self):
        """创建集合和字段"""
        # 定义字段
        fields = [
            FieldSchema(name="question_id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.vector_dim),
            FieldSchema(name="metadata", dtype=DataType.JSON, optional=True)
        ]
        
        # 创建schema
        schema = CollectionSchema(fields=fields, description="题目向量集合")
        
        # 创建集合
        self.collection = Collection(name=self.collection_name, schema=schema)
        logger.info(f"已创建集合: {self.collection_name}")
        
        # 创建索引
        self._create_index()
    
    def _create_index(self):
        """为向量字段创建索引"""
        if not self.collection:
            raise ConnectionError("集合未加载")
        
        index_params = {
            "index_type": self.index_type,
            "metric_type": self.metric_type,
            "params": {"nlist": self.nlist}
        }
        
        self.collection.create_index(field_name="vector", index_params=index_params)
        logger.info(f"已为集合创建索引: {self.index_type}")
    
    def _has_index(self):
        """检查集合是否已有索引"""
        if not self.collection:
            return False
        
        try:
            indexes = self.collection.indexes
            return len(indexes) > 0
        except Exception:
            return False
    
    @retry(MilvusException, tries=3, delay=1, backoff=2)
    def insert(self, question_id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """插入单个向量数据"""
        try:
            if not self.connected:
                self.connect()
            
            # 准备数据
            data = [
                [question_id],
                [vector],
                [metadata if metadata else {}]
            ]
            
            # 插入数据
            self.collection.insert(data)
            self.collection.flush()
            logger.info(f"已插入题目向量: {question_id}")
            return True
        except Exception as e:
            logger.error(f"插入题目向量失败: {str(e)}")
            raise
    
    @retry(MilvusException, tries=3, delay=1, backoff=2)
    def batch_insert(self, data: List[Tuple[str, List[float], Optional[Dict[str, Any]]]]) -> bool:
        """批量插入向量数据"""
        try:
            if not self.connected:
                self.connect()
            
            # 准备数据
            question_ids = [item[0] for item in data]
            vectors = [item[1] for item in data]
            metadatas = [item[2] if item[2] else {} for item in data]
            
            # 分批次插入
            batch_size = settings.MILVUS_BATCH_SIZE
            for i in range(0, len(data), batch_size):
                batch_end = min(i + batch_size, len(data))
                batch_data = [
                    question_ids[i:batch_end],
                    vectors[i:batch_end],
                    metadatas[i:batch_end]
                ]
                self.collection.insert(batch_data)
                logger.info(f"已插入批次 {i//batch_size + 1}，包含 {batch_end - i} 个题目向量")
            
            self.collection.flush()
            logger.info(f"批量插入完成，共 {len(data)} 个题目向量")
            return True
        except Exception as e:
            logger.error(f"批量插入失败: {str(e)}")
            raise
    
    @retry(MilvusException, tries=3, delay=1, backoff=2)
    def search(self, vector: List[float], top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        try:
            if not self.connected:
                self.connect()
            
            # 确保集合已加载
            if not self.collection.is_loaded:
                self.collection.load()
            
            # 构建搜索参数
            search_params = {
                "metric_type": self.metric_type,
                "params": {"nprobe": 10}
            }
            
            # 构建过滤表达式
            expr = None
            if filters:
                # 简单的过滤表达式构建，实际应用中可能需要更复杂的逻辑
                conditions = []
                for key, value in filters.items():
                    if isinstance(value, str):
                        conditions.append(f"metadata['{key}'] == '{value}'")
                    else:
                        conditions.append(f"metadata['{key}'] == {value}")
                expr = " && ".join(conditions)
            
            # 执行搜索
            start_time = time.time()
            results = self.collection.search(
                data=[vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["question_id", "metadata"]
            )
            search_time = time.time() - start_time
            
            # 处理搜索结果
            search_results = []
            for hits in results:
                for hit in hits:
                    search_results.append({
                        "question_id": hit.entity.get("question_id"),
                        "similarity": hit.distance,
                        "metadata": hit.entity.get("metadata", {})
                    })
            
            logger.info(f"搜索完成，耗时: {search_time:.4f}秒，找到 {len(search_results)} 个结果")
            return search_results
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            raise
    
    @retry(MilvusException, tries=3, delay=1, backoff=2)
    def get_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """根据ID查询题目信息"""
        try:
            if not self.connected:
                self.connect()
            
            # 构建查询表达式
            expr = f"question_id == '{question_id}'"
            
            # 执行查询
            results = self.collection.query(expr=expr, output_fields=["question_id", "metadata"])
            
            if results and len(results) > 0:
                return results[0]
            else:
                logger.info(f"未找到题目: {question_id}")
                return None
        except Exception as e:
            logger.error(f"查询题目失败: {str(e)}")
            raise
    
    @retry(MilvusException, tries=3, delay=1, backoff=2)
    def delete_by_id(self, question_id: str) -> bool:
        """根据ID删除题目"""
        try:
            if not self.connected:
                self.connect()
            
            # 构建删除表达式
            expr = f"question_id == '{question_id}'"
            
            # 执行删除
            result = self.collection.delete(expr=expr)
            
            if result.delete_count > 0:
                logger.info(f"已删除题目: {question_id}")
                return True
            else:
                logger.info(f"未找到要删除的题目: {question_id}")
                return False
        except Exception as e:
            logger.error(f"删除题目失败: {str(e)}")
            raise
    
    @retry(MilvusException, tries=3, delay=1, backoff=2)
    def get_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            if not self.connected:
                self.connect()
            
            # 获取集合统计信息
            stats = utility.get_collection_stats(self.collection_name)
            
            # 计算题目总数
            row_count = stats["row_count"]
            
            # 计算集合大小
            collection_size = 0
            for field in stats["fields"]:
                if "size" in field:
                    collection_size += field["size"]
            
            # 计算平均向量大小
            avg_vector_size = collection_size / row_count if row_count > 0 else 0
            
            return {
                "question_count": row_count,
                "collection_size": collection_size,
                "avg_vector_size": avg_vector_size
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            raise
    
    def disconnect(self):
        """断开与Milvus的连接"""
        try:
            if connections.has_connection("default"):
                connections.disconnect("default")
                self.connected = False
                logger.info("已断开与Milvus的连接")
        except Exception as e:
            logger.error(f"断开连接失败: {str(e)}")


# 创建全局Milvus客户端实例
milvus_client = MilvusClient()