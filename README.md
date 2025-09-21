# FastAPI 向量搜索微服务

基于 FastAPI + Towhee + Milvus 的高性能向量搜索微服务，专门处理图片向量化和相似度搜索。

## 🎯 核心功能

- **题目管理**：添加、查询、删除题目向量
- **智能搜索**：基于图片相似度的题目搜索
- **批量操作**：支持批量添加题目
- **监控统计**：服务状态监控和统计信息
- **高性能**：异步处理、连接池管理、缓存优化
- **生产就绪**：Docker容器化、环境变量配置、健康检查

## 📦 技术栈

- **框架**: FastAPI + Uvicorn + Pydantic
- **向量处理**: Towhee (CLIP模型)
- **向量数据库**: Milvus + PyMilvus
- **其他**: Python 3.9+, 异步处理, 缓存优化

## 🚀 快速开始

### 本地开发环境

```bash
# 克隆仓库
git clone <repository-url>
cd vector-search-service

# 创建虚拟环境
python -m venv venv
# 激活虚拟环境
# Windows
env\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件，配置Milvus连接信息

# 启动Milvus（如果本地没有）
docker run -d --name milvus-standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:v2.2.8 milvus run standalone

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📚 API文档

服务提供了完整的OpenAPI文档，可以通过`/docs`端点访问交互式API文档，或通过`/redoc`端点访问更详细的文档。

### 主要API端点

#### 基础服务
- **GET /health**: 服务健康检查
- **GET /stats**: 获取统计信息

#### 题目管理
- **POST /questions**: 添加单个题目
- **POST /questions/batch**: 批量添加题目
- **GET /questions/{id}**: 查询题目信息
- **DELETE /questions/{id}**: 删除题目

#### 搜索功能
- **POST /search**: 搜索相似题目

## 📝 使用示例

### Python客户端示例

```python
import requests
import base64
import json

# 服务URL
base_url = "http://localhost:8000"

# 1. 读取图片并转换为Base64
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# 2. 添加题目
image_base64 = image_to_base64("example_question.png")
add_response = requests.post(
    f"{base_url}/questions",
    json={
        "question_id": "q123",
        "image_base64": image_base64,
        "metadata": {"subject": "math", "grade": "3"}
    }
)
print(f"添加题目响应: {add_response.json()}")

# 3. 搜索相似题目
search_image_base64 = image_to_base64("search_image.png")
search_response = requests.post(
    f"{base_url}/search",
    json={
        "image_base64": search_image_base64,
        "top_k": 5,
        "search_method": "vector",
        "filters": {"subject": "math"}
    }
)
print(f"搜索结果: {json.dumps(search_response.json(), indent=2)}")

# 4. 查询题目
question_response = requests.get(f"{base_url}/questions/q123")
print(f"题目信息: {question_response.json()}")

# 5. 删除题目
delete_response = requests.delete(f"{base_url}/questions/q123")
print(f"删除状态码: {delete_response.status_code}")
```

### cURL命令示例

```bash
# 健康检查
curl -X GET http://localhost:8000/health

# 获取统计信息
curl -X GET http://localhost:8000/stats

# 添加题目（注意：这里需要替换为实际的base64编码图片数据）
curl -X POST http://localhost:8000/questions \
  -H "Content-Type: application/json" \
  -d '{"question_id": "q123", "image_base64": "BASE64_ENCODED_IMAGE_HERE", "metadata": {"subject": "math"}}'

# 搜索相似题目
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "SEARCH_IMAGE_BASE64_HERE", "top_k": 5, "search_method": "vector"}'
```

## ⚙️ 配置说明

服务通过环境变量进行配置，可以在`.env`文件中设置以下配置项：

- **MILVUS_HOST**: Milvus服务器主机名
- **MILVUS_PORT**: Milvus服务器端口
- **MILVUS_COLLECTION_NAME**: Milvus集合名称
- **APP_HOST**: 应用主机名
- **APP_PORT**: 应用端口
- **WORKERS**: Uvicorn工作进程数
- **DEBUG**: 调试模式开关
- **RATE_LIMIT**: API速率限制

详细配置请参考`.env.example`文件。

## 📊 监控与维护

### 健康检查

服务提供了`/health`端点用于健康检查，可以集成到Kubernetes等容器编排系统中。

### 统计信息

通过`/stats`端点可以获取服务的运行统计信息，包括：
- 题目总数
- 集合大小
- API调用次数
- 错误统计

### 可选的Prometheus + Grafana监控

项目的`docker-compose.yml`文件中包含了Prometheus和Grafana服务配置，可以用于更详细的监控。

## 🧪 测试

项目支持使用pytest进行测试：

```bash
# 安装测试依赖
pip install pytest httpx

# 运行测试
pytest tests/
```

## 🔍 性能优化

1. **异步处理**：使用FastAPI的异步特性提高并发处理能力
2. **连接池**：Milvus客户端使用连接池管理数据库连接
3. **批量操作**：支持批量添加题目，减少网络往返
4. **缓存机制**：图片向量化结果缓存，提高重复图片的处理速度
5. **速率限制**：防止恶意请求和资源滥用

## 📈 扩展建议

1. **API认证**：添加JWT或API密钥认证机制
2. **分布式部署**：支持多实例部署和负载均衡
3. **更多模型**：集成更多的向量模型，支持不同类型的图片和文本
4. **数据备份**：实现Milvus数据的定期备份和恢复机制
5. **自动扩展**：基于负载自动调整服务实例数量

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用MIT许可证 - 详见[LICENSE](LICENSE)文件

## 📧 联系我们

如有问题或建议，请联系项目维护者。