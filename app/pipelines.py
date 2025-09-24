import towhee
import base64
import io
import numpy as np
from PIL import Image
from typing import List, Optional, Dict, Any
import logging
import time
from functools import lru_cache
from retry import retry

from .config import settings

logger = logging.getLogger(__name__)


class VectorizationPipeline:
    """向量处理管道，使用Towhee和CLIP模型生成图片向量"""
    def __init__(self):
        """初始化向量处理管道"""
        self.cache_size = settings.CACHE_SIZE
        self.cache_ttl = settings.CACHE_TTL
        
        # 创建Towhee管道用于向量生成
        self._create_vectorization_pipeline()
        
        # 初始化缓存计数器
        self.cache_hits = 0
        self.cache_misses = 0
    
    def _create_vectorization_pipeline(self):
        """创建Towhee向量生成管道"""
        try:
            # 使用Towhee的新API创建图片向量化管道
            self.pipeline = (
                towhee.pipe.input("image")
                .map("image", "decoded_image", towhee.ops.image_decode())
                .map("decoded_image", "vector", towhee.ops.image_embedding.clip())
                .output("vector")
            )
            logger.info("成功创建Towhee向量生成管道")
        except Exception as e:
            logger.error(f"创建Towhee管道失败: {str(e)}")
            raise
    
    def _decode_base64_image(self, base64_str: str) -> Image.Image:
        """解码Base64字符串为PIL图片"""
        try:
            # 检查是否包含data URI前缀
            if base64_str.startswith("data:image/"):
                # 提取Base64部分
                import re
                match = re.search(r"base64,(.+)", base64_str)
                if match:
                    base64_str = match.group(1)
            
            # 解码Base64字符串
            image_data = base64.b64decode(base64_str)
            
            # 转换为PIL图片
            image = Image.open(io.BytesIO(image_data))
            
            # 确保图片格式正确
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            return image
        except Exception as e:
            logger.error(f"解码Base64图片失败: {str(e)}")
            raise ValueError(f"无效的图片格式: {str(e)}")
    
    @lru_cache(maxsize=1000)
    def _get_image_hash(self, base64_str: str) -> str:
        """获取图片的哈希值，用于缓存"""
        import hashlib
        return hashlib.md5(base64_str.encode()).hexdigest()
    
    @retry(Exception, tries=3, delay=1, backoff=2)
    def vectorize_image(self, base64_str: str) -> List[float]:
        """将Base64编码的图片转换为向量"""
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 解码图片
            image = self._decode_base64_image(base64_str)
            
            # 使用Towhee管道生成向量
            result = self.pipeline(image=image).get()
            
            # 确保结果是列表格式
            if isinstance(result, np.ndarray):
                vector = result.tolist()
            elif isinstance(result, dict) and "vector" in result:
                vector = result["vector"]
                if isinstance(vector, np.ndarray):
                    vector = vector.tolist()
            else:
                vector = list(result)
            
            # 记录处理时间
            process_time = time.time() - start_time
            logger.info(f"图片向量化完成，耗时: {process_time:.4f}秒")
            
            return vector
        except Exception as e:
            logger.error(f"图片向量化失败: {str(e)}")
            raise
    
    def batch_vectorize(self, base64_strs: List[str]) -> List[List[float]]:
        """批量处理图片向量化"""
        vectors = []
        
        try:
            start_time = time.time()
            
            for i, base64_str in enumerate(base64_strs):
                try:
                    vector = self.vectorize_image(base64_str)
                    vectors.append(vector)
                    logger.info(f"批量向量化进度: {i+1}/{len(base64_strs)}")
                except Exception as e:
                    logger.error(f"第 {i+1} 个图片向量化失败: {str(e)}")
                    # 对于批量处理，继续处理下一个，而不是整体失败
                    vectors.append([])  # 或者可以选择其他方式标记失败
            
            total_time = time.time() - start_time
            logger.info(f"批量向量化完成，共 {len(base64_strs)} 个图片，耗时: {total_time:.4f}秒，平均: {total_time/len(base64_strs):.4f}秒/张")
            
            return vectors
        except Exception as e:
            logger.error(f"批量向量化过程中出现错误: {str(e)}")
            raise
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_size": self.cache_size,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) * 100 
                        if (self.cache_hits + self.cache_misses) > 0 else 0
        }
    
    def clear_cache(self):
        """清除缓存"""
        # 清除lru_cache
        self._get_image_hash.cache_clear()
        
        # 重置缓存统计
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info("向量处理缓存已清除")


# 创建全局向量处理管道实例
vector_pipeline = VectorizationPipeline()