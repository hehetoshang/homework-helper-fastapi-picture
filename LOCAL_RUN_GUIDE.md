# 本地运行指南

本指南将帮助您在本地开发环境中运行向量搜索微服务。

## 前置条件

在开始之前，请确保您的系统已安装以下软件：

- **Python 3.8+**: https://www.python.org/downloads/
- **Docker**: https://www.docker.com/get-started (用于运行Milvus数据库)
- **Git**: https://git-scm.com/downloads (可选，用于克隆代码)

## 步骤1: 获取代码

如果您还没有项目代码，请先获取：

```bash
# 克隆代码仓库
git clone <repository-url>
# 进入项目目录
cd homework-helper-fastapi-picture
```

## 步骤2: 创建虚拟环境

为了隔离项目依赖，建议创建一个Python虚拟环境：

### Windows系统

```bash
# 创建虚拟环境
python -m venv venv
# 激活虚拟环境
env\Scripts\activate
```

### Linux/Mac系统

```bash
# 创建虚拟环境
python3 -m venv venv
# 激活虚拟环境
source venv/bin/activate
```

激活后，您会看到命令提示符前面显示`(venv)`，表示虚拟环境已激活。

## 步骤3: 安装依赖

在虚拟环境中，安装项目所需的所有依赖：

```bash
# 安装基本依赖
pip install -r requirements.txt
```

## 步骤4: 配置环境变量

复制环境变量示例文件，并根据您的本地环境进行配置：

```bash
# 复制示例文件
cp .env.example .env
```

使用文本编辑器打开`.env`文件，修改以下关键配置：

```
# Milvus配置
MILVUS_HOST=localhost  # 本地运行时使用localhost
MILVUS_PORT=19530      # Milvus默认端口

# 服务配置
APP_HOST=0.0.0.0       # 允许从任何IP访问
APP_PORT=8000          # 服务端口
DEBUG=true             # 开发环境开启调试模式
```

## 步骤5: 启动Milvus数据库

向量搜索服务依赖Milvus数据库来存储和搜索向量数据。您可以使用Docker快速启动Milvus：

```bash
# 启动Milvus独立实例
docker run -d --name milvus-standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:v2.2.8 milvus run standalone
```

验证Milvus是否成功启动：

```bash
# 查看容器状态
docker ps -a | grep milvus-standalone
```

您应该看到Milvus容器的状态为`Up`。

## 步骤6: 启动FastAPI服务

在虚拟环境中，使用Uvicorn启动FastAPI服务：

```bash
# 开发模式启动（带自动重载）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 或者使用环境变量配置
uvicorn app.main:app --host ${APP_HOST} --port ${APP_PORT} --reload
```

启动成功后，您会看到类似以下输出：

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345]
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## 步骤7: 访问服务

服务启动后，您可以通过以下URL访问：

- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **统计信息**: http://localhost:8000/stats

## 运行测试

项目包含完整的测试用例，您可以通过以下命令运行测试：

```bash
# 安装测试依赖
pip install pytest httpx

# 运行测试
pytest tests/
```

## 常见问题和解决方案

### 1. 无法连接到Milvus数据库

- 确认Milvus容器正在运行：`docker ps -a | grep milvus-standalone`
- 检查Milvus容器日志：`docker logs milvus-standalone`
- 确认`.env`文件中的`MILVUS_HOST`和`MILVUS_PORT`配置正确

### 2. 端口被占用

如果8000端口被其他程序占用，可以修改`.env`文件中的`APP_PORT`配置，然后使用新端口启动服务。

### 3. 依赖安装失败

- 确保您使用的是最新版本的pip：`pip install --upgrade pip`
- 如果是特定包安装失败，可以尝试单独安装：`pip install <package-name>`
- 检查Python版本是否满足要求（3.8+）

### 4. 内存使用过高

- 调整`.env`文件中的`WORKERS`参数，减少工作进程数量
- 降低Milvus的配置参数，如`MILVUS_NLIST`

## 开发建议

1. **代码风格**: 遵循PEP8规范，使用类型提示
2. **提交前检查**: 运行测试确保代码质量
3. **日志查看**: 注意查看控制台输出的日志信息，有助于排查问题
4. **热重载**: 开发模式下使用`--reload`参数可以在修改代码后自动重启服务

## 停止服务

当您完成开发或测试后，可以按以下步骤停止服务：

1. 按`CTRL+C`停止FastAPI服务
2. 停止Milvus容器：`docker stop milvus-standalone`
3. 退出虚拟环境：`deactivate`

## 后续步骤

如果您想进一步部署到生产环境，请参考项目中的Docker和docker-compose配置，或查看README.md中的部署文档部分。

祝您开发愉快！